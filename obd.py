"""
CANable 2.0 (slcan firmware) + Windows 用 OBD-II クライアントサンプル
- Mode 09 / PID 02 による VIN 取得
- 任意のサービス / PID を指定したクエリ
- PIDs supported ビットマップの取得とキャッシュ

依存: pip install python-can python-isotp pyserial

実行例:
  python obd_vin.py --port COM5                        # VIN 取得
  python obd_vin.py --port COM5 --supported            # 対応 PID 一覧
  python obd_vin.py --port COM5 --service 0x01 --pid 0x0C
  python obd_vin.py --port COM5 --pid 0x0D
"""
from __future__ import annotations

import argparse
import sys
import time
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Set

import can
import isotp


# ============================================================ 例外・定数

NRC_NAMES = {
    0x10: "generalReject",
    0x11: "serviceNotSupported",
    0x12: "subFunctionNotSupported",
    0x13: "incorrectMessageLength",
    0x31: "requestOutOfRange",
    0x33: "securityAccessDenied",
    0x78: "responsePending",
}


class ObdError(Exception):
    """OBD 通信に関する基底例外"""


class ObdTimeoutError(ObdError):
    """ECU から応答がない"""


class ObdNegativeResponse(ObdError):
    """ECU から NEGATIVE RESPONSE (0x7F) が返された"""

    def __init__(self, service: int, code: int) -> None:
        self.service = service
        self.error_code = code
        super().__init__(
            f"Negative Response: service=0x{service:02X}, "
            f"NRC=0x{code:02X} ({NRC_NAMES.get(code, 'unknown')})"
        )


class PidNotSupportedError(ObdError):
    """車両が対応していない PID が指定された"""

    def __init__(self, service: int, pid: int) -> None:
        self.service = service
        self.pid = pid
        super().__init__(
            f"PID 0x{pid:02X} is not supported by this vehicle "
            f"(service 0x{service:02X})"
        )


# ============================================================ 層1: アドレス設定

@dataclass(frozen=True)
class ObdAddress:
    """物理アドレッシングの CAN ID 組 (ISO 15765-4 / SAE J1979)"""
    tx_id: int = 0x7E0   # 送信 (要求)
    rx_id: int = 0x7E8   # 受信 (応答)


# ============================================================ 層2: CAN バス接続

class SlcanBus:
    """CANable 2.0 (slcan) を python-can 経由で開くコンテキストマネージャ"""

    def __init__(self, port: str, bitrate: int = 500_000) -> None:
        self.bus = can.Bus(interface="slcan", channel=port, bitrate=bitrate)

    def __enter__(self) -> "SlcanBus":
        return self

    def __exit__(self, *exc) -> None:
        self.bus.shutdown()


# ============================================================ 層3: ISO-TP 送受信

class IsoTpTransport:
    """ISO 15765-2 (CAN-TP) を透過的に扱う。マルチフレーム応答 (VIN 等) にも対応"""

    def __init__(self, bus: can.BusABC, addr: ObdAddress) -> None:
        params = isotp.Params(
            address=isotp.Address(
                isotp.AddressingMode.Normal_11bits,
                txid=addr.tx_id,
                rxid=addr.rx_id,
            ),
            blocksize=0,
            stmin=0,
        )
        self._stack = isotp.NotifierBasedCanStack(bus, params)
        self._stack.start()

    def request(self, payload: bytes, timeout: float = 2.0) -> bytes:
        """1 リクエスト → 1 完全応答 (マルチフレームは復元済み)"""
        if hasattr(self._stack, "flush_rx_queue"):
            self._stack.flush_rx_queue()
        self._stack.send(payload, block=True, timeout=timeout)
        data = self._stack.recv(timeout=timeout)
        if data is None:
            raise ObdTimeoutError(
                f"{timeout}s 以内に応答なし (req={payload.hex(' ').upper()})"
            )
        return bytes(data)

    def __enter__(self) -> "IsoTpTransport":
        return self

    def __exit__(self, *exc) -> None:
        self._stack.stop()


# ============================================================ 層4: OBD-II プロトコル

class ObdClient:
    """OBD-II サービス要求/応答の送受信。負応答・responsePending を処理"""

    MAX_PENDING = 5  # 0x78 (responsePending) の再待ち受け上限

    def __init__(self, transport: IsoTpTransport, timeout: float = 2.0) -> None:
        self._tp = transport
        self._timeout = timeout

    def query(self, service: int, pid: Optional[int] = None,
              timeout: Optional[float] = None) -> bytes:
        """サービス (モード) と PID を指定して応答の生バイト列を受け取る"""
        req = bytes([service]) + (b"" if pid is None else bytes([pid]))
        t = timeout if timeout is not None else self._timeout
        for _ in range(1 + self.MAX_PENDING):
            resp = self._tp.request(req, timeout=t)
            if resp and resp[0] == 0x7F:  # Negative Response
                code = resp[2] if len(resp) >= 3 else 0
                if code == 0x78:          # responsePending: もう一度待ち受ける
                    continue
                raise ObdNegativeResponse(
                    resp[1] if len(resp) >= 2 else service, code)
            if not resp or resp[0] != service + 0x40:
                raise ObdError(f"予期しない応答: {resp.hex(' ').upper()}")
            return resp
        raise ObdTimeoutError("responsePending が継続して応答を取得できず")

    def read_vin(self, timeout: Optional[float] = None) -> str:
        """Mode 09 / PID 02 による VIN 取得 (17 文字 ASCII)"""
        resp = self.query(0x09, 0x02, timeout=timeout)  # 49 04 CC + VIN 17B
        if len(resp) < 4:
            raise ObdError(f"VIN 応答が不正に短い: {resp.hex(' ').upper()}")
        return bytes(b for b in resp[3:] if 0x20 <= b <= 0x7E).decode("ascii")


# ============================================================ 層5: PID 定義

@dataclass(frozen=True)
class PidDefinition:
    name: str
    unit: str
    decode: Optional[Callable[[bytes], float]]  # Bitmap は None
    nbytes: int = 1                             # 期待データ長 (A,B,...)
    kind: str = "value"                         # "value" | "bitmap"


# PIDs supported ビットマップベース (0x00 基準でカスケード参照)
SUPPORTED_PID_BASES: List[int] = [0x00, 0x20, 0x40, 0x60, 0x80, 0xA0]

MODE01_PIDS: Dict[int, PidDefinition] = {
    # --- PIDs supported (Bitmap) ---
    0x00: PidDefinition("PIDs supported [01-20]", "Bitmap", None, 4, "bitmap"),
    0x20: PidDefinition("PIDs supported [21-40]", "Bitmap", None, 4, "bitmap"),
    0x40: PidDefinition("PIDs supported [41-60]", "Bitmap", None, 4, "bitmap"),
    0x60: PidDefinition("PIDs supported [61-80]", "Bitmap", None, 4, "bitmap"),
    0x80: PidDefinition("PIDs supported [81-A0]", "Bitmap", None, 4, "bitmap"),
    0xA0: PidDefinition("PIDs supported [A1-C0]", "Bitmap", None, 4, "bitmap"),
    # --- ライブデータ ---
    0x04: PidDefinition("計算負荷値", "%", lambda d: d[0] * 100 / 255),
    0x05: PidDefinition("冷却水温度", "℃", lambda d: d[0] - 40),
    0x0C: PidDefinition("エンジン回転数", "rpm",
                        lambda d: (d[0] * 256 + d[1]) / 4, nbytes=2),
    0x0D: PidDefinition("車速", "km/h", lambda d: float(d[0])),
    0x0F: PidDefinition("吸気温度", "℃", lambda d: d[0] - 40),
    0x10: PidDefinition("MAF", "g/s",
                        lambda d: (d[0] * 256 + d[1]) / 100, nbytes=2),
    0x11: PidDefinition("スロットル位置", "%", lambda d: d[0] * 100 / 255),
    0x2F: PidDefinition("燃料残量", "%", lambda d: d[0] * 100 / 255),
}


def bitmap_to_pids(base: int, data: bytes) -> List[int]:
    """4 バイトビットマップを対応 PID 番号リストに変換

    先頭バイトの MSB が base+1 を表す (SAE J1979)。
    """
    pids: List[int] = []
    for i, byte in enumerate(data[:4]):
        for j in range(8):
            if (byte >> (7 - j)) & 1:
                pids.append(base + i * 8 + j + 1)
    return pids


# ============================================================ 層6: 車両 API (高レベル)

class Vehicle:
    """アプリから使う高レベル API。対応 PID を初期化時にキャッシュする"""

    def __init__(self, obd: ObdClient, probe_supported: bool = True) -> None:
        self._obd = obd
        self._supported: Set[int] = set()
        if probe_supported:
            self._probe_supported_pids()

    # ---------- 対応 PID のキャッシュ ----------

    def _probe_supported_pids(self) -> None:
        """0x00 からカスケード状に PIDs supported を取得し self._supported に記録

        上位ブロック (0x20 以降) は下位ビットマップで対応が示された場合のみ照会する。
        ECU が Mode 01 自体に非対応/無応答の場合は空セットのままとなる。
        """
        for base in SUPPORTED_PID_BASES:
            if base != 0x00 and base not in self._supported:
                break  # 親ビットマップが未対応なら以降は存在しない
            try:
                resp = self._obd.query(0x01, base)  # 41 00 A B C D
            except ObdError:
                break
            self._supported.add(base)
            self._supported.update(bitmap_to_pids(base, resp[2:]))

    def supported_pids(self) -> List[int]:
        """車両が対応する Mode 01 PID のリスト (キャッシュ読み出しのみ・通信なし)"""
        return sorted(self._supported)

    # ---------- 計測 ----------

    def read_pid(self, service: int, pid: int) -> bytes:
        """サービス/PID を指定した生クエリ。Mode 01 は対応チェック付き"""
        if service == 0x01 and self._supported and pid not in self._supported:
            raise PidNotSupportedError(service, pid)
        return self._obd.query(service, pid)

    def read_mode01(self, pid: int) -> str:
        """Mode 01 を読み、既知 PID はデコードして整形表示用文字列で返す"""
        resp = self.read_pid(0x01, pid)  # 41 PID A B ...
        data = resp[2:]
        defn = MODE01_PIDS.get(pid)
        if defn is None or len(data) < defn.nbytes:
            return f"01 {pid:02X} raw: {data.hex(' ').upper()}"
        if defn.kind == "bitmap":
            pids = bitmap_to_pids(pid, data)
            return f"{defn.name}: " + " ".join(f"{p:02X}" for p in pids)
        assert defn.decode is not None
        return f"{defn.name}: {defn.decode(data):.1f} {defn.unit}"

    def read_vin(self) -> str:
        return self._obd.read_vin()


# ============================================================ CLI

def list_com_ports() -> List[str]:
    from serial.tools import list_ports
    return [p.device for p in list_ports.comports()]


def auto_select_port() -> str:
    ports = list_com_ports()
    if len(ports) == 1:
        return ports[0]
    sys.exit(
        "COM ポートを自動決定できません。--port で指定してください。\n"
        f"  検出されたポート: {ports or 'なし (接続/ドライバを確認)'}"
    )


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="CANable(slcan) OBD-II クライアント")
    p.add_argument("--port", help="COM ポート (例: COM5)。省略時は 1 個のみ検出時に自動選択")
    p.add_argument("--bitrate", type=int, default=500_000, help="CAN ビットレート (既定 500000)")
    p.add_argument("--txid", type=lambda x: int(x, 0), default=0x7E0, help="要求 CAN ID (既定 0x7E0)")
    p.add_argument("--rxid", type=lambda x: int(x, 0), default=0x7E8, help="応答 CAN ID (既定 0x7E8)")
    p.add_argument("--timeout", type=float, default=2.0, help="応答待ちタイムアウト秒")
    p.add_argument("--service", type=lambda x: int(x, 0), default=None, help="サービス (モード) 番号")
    p.add_argument("--pid", type=lambda x: int(x, 0), default=None, help="PID 番号")
    p.add_argument("--supported", action="store_true", help="車両の対応 PID 一覧を表示")
    p.add_argument("--list-pids", action="store_true", help="定義済み PID 一覧を表示")
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)

    if args.list_pids:
        for pid, d in sorted(MODE01_PIDS.items()):
            print(f"0x{pid:02X}  {d.name} [{d.unit}]")
        return 0

    port = args.port or auto_select_port()
    addr = ObdAddress(tx_id=args.txid, rx_id=args.rxid)

    try:
        with SlcanBus(port, args.bitrate) as s, IsoTpTransport(s.bus, addr) as tp:
            vehicle = Vehicle(ObdClient(tp, timeout=args.timeout))  # ここで PID 照会
            if args.supported:
                pids = vehicle.supported_pids()
                print("対応 PID:", " ".join(f"{p:02X}" for p in pids) or "(応答なし)")
            elif args.service is not None:
                resp = vehicle.read_pid(args.service, args.pid or 0x00)
                print(f">> {args.service:02X} {args.pid or 0:02X} "
                      f"<< {resp.hex(' ').upper()}")
            elif args.pid is not None:
                print(vehicle.read_mode01(args.pid))
            else:
                t0 = time.monotonic()
                print(f"VIN: {vehicle.read_vin()} ({time.monotonic() - t0:.2f}s)")
    except (ObdError, can.CanError) as e:
        print(f"エラー: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())