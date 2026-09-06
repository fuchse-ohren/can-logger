from __future__ import annotations

from dataclasses import dataclass
from poplib import POP3_SSL_PORT
from typing import Optional

import can
import isotp
import time


# ============================================================
# CAN Layer
# ============================================================

@dataclass
class CanConfig:
    """
    Slcanポートとの接続設定

    Parameters
    ----------
     - port (str) = "COM6" - COMポートの名称
     - bitrate (int) = 500000 - シリアル通信のビットレート
    """
    port: str = "COM6"
    bitrate: int = 500000


class CanTransport:
    """
    CANable 2.0 + SLCAN を利用したCANトランスポート。
    """

    def __init__(self, config: CanConfig):
        self.config = config
        self.bus: Optional[can.Bus] = None

    def open(self) -> None:
        self.bus = can.Bus(
            interface="slcan",
            channel=self.config.port,
            bitrate=self.config.bitrate,
        )

    def close(self) -> None:
        if self.bus is not None:
            self.bus.shutdown()
            self.bus = None

    def send(
        self,
        arbitration_id: int,
        data: bytes,
        *,
        is_extended_id: bool = False,
    ) -> None:
        if self.bus is None:
            raise RuntimeError("CAN bus is not open")

        msg = can.Message(
            arbitration_id=arbitration_id,
            data=data,
            is_extended_id=is_extended_id,
        )

        self.bus.send(msg)

    def recv(self, timeout: float = 1.0) -> Optional[can.Message]:
        if self.bus is None:
            raise RuntimeError("CAN bus is not open")

        return self.bus.recv(timeout)


# ============================================================
# ISO-TP Layer
# ============================================================

class IsotpError(Exception):
    pass

@dataclass
class IsoTpConfig:
    """
    ISO-TP関連のパラメタを保持するクラス

    Parameters
    -----------
     - tx_id (int) = 0x7DF - 送信用CAN ID
     - rx_id (int) = 0x7E8 - 受信用CAN ID
     - stmin (int) = 0 - フロー制御メッセージで送信される最小間隔時間。
        連続する2つのフレーム間の待機時間を示す。この値はCANプロトコル上でそのまま送信される。
        値が1から127の場合はミリ秒単位、0xF1から0xF9の場合は100マイクロ秒から900マイクロ秒の範囲を意味する。
        値が0の場合はタイミング要件がないことを示す。
     - blocksize (int) = 8 - フロー制御メッセージを送信する際にレイヤーが含める単一バイトのブロックサイズ。
        送信者がフロー制御メッセージを要求する前に送信すべき連続フレーム数を表す。
        値が 0 の場合、ブロックサイズは無限大（つまりフロー制御メッセージは送信されない）を意味する。
     - wtfmax (int) = 0 - フロー制御メッセージに含める単一バイトの「待機フレーム最大値」を設定する。
        この値が上限に達すると、受信処理は停止し、MaximumWaitFrameReachedError が発生する。
        値が 0 の場合、待機フレームはサポートされておらず、送信も行われない。
     - tx_data_length (int) = 8 - リンク層(CANレイヤー)が転送できる最大バイト数。
        つまり、単一のCANメッセージで可能な限り最大のデータバイト数。
        有効な値は : 8、12、16、20、24、32、48、64です。
        大きなIsoTPフレームは、パディングを使用しない限り、可能な限り小さくなる最後のCANメッセージを除き、
        このサイズの小型CANメッセージで送信されます。
    """

    tx_id: int = 0x7DF
    rx_id: int = 0x7E8

    # ISO-TP parameters
    stmin: int = 0
    blocksize: int = 8
    wftmax: int = 0
    tx_data_length: int = 8


class IsoTpTransport:
    """
    ISO 15765-2 transport 層。
    """

    def __init__(
        self,
        can_transport: CanTransport,
        config: IsoTpConfig,
    ):
        self.can_transport = can_transport
        self.config = config

        self.stack: Optional[isotp.CanStack] = None

    def open(self) -> None:
        if self.can_transport.bus is None:
            raise RuntimeError("CAN bus is not open")

        address = isotp.Address(
            isotp.AddressingMode.Normal_11bits,
            txid=self.config.tx_id,
            rxid=self.config.rx_id,
        )

        params = {
            "stmin": self.config.stmin,
            "blocksize": self.config.blocksize,
            "wftmax": self.config.wftmax,
            "tx_data_length": self.config.tx_data_length,
            "rx_flowcontrol_timeout": 100,
            "rx_consecutive_frame_timeout": 100,
            "tx_padding": 0x00
        }

        self.stack = isotp.CanStack(
            bus=self.can_transport.bus,
            address=address,
            params=params,
        )

    def send_and_receive(
        self,
        payload: bytes,
        timeout: float = 0.5,
    ) -> bytes:

        if self.stack is None:
            raise RuntimeError("ISO-TPスタックの開設に失敗しました")

        self.stack.send(payload)
        #print("ISOTP ↑\t",payload.hex(" "))

        deadline = __import__("time").monotonic() + timeout

        while __import__("time").monotonic() < deadline:
            self.stack.process()

            if self.stack.available():
                res = self.stack.recv()
                if res == None:
                    raise IsotpError("ISO-TPで正常な応答を受信できませんでした")
                #print("ISOTP ↓\t",bytes(res).hex(" "))
                return bytes(res)

            __import__("time").sleep(0.001)

        raise TimeoutError("ISO-TP応答がタイムアウトしました")


# ============================================================
# OBD-II Layer
# ============================================================

class ObdError(Exception):
    pass


class ObdNegativeResponse(ObdError):
    def __init__(
        self,
        service: int,
        error_code: int,
    ):
        self.service = service
        self.error_code = error_code

        super().__init__(
            f"OBD negative response: "
            f"service=0x{service:02X}, "
            f"error=0x{error_code:02X}"
        )


class ObdClient:
    """
    OBD-IIサービス層。
    """

    def __init__(
        self,
        transport: IsoTpTransport,
    ):
        self.transport = transport
        self.dec_fomula = {
            0x04: lambda d: int(d[0]) / 2.55, # 発動機負荷(%)
            0x05: lambda d: int(d[0]) - 40, # 冷却水温(C)
            0x0C: lambda d: (256 * int(d[0]) + int(d[1])) / 4, # 発動機回転数(rpm)
            0x0D: lambda d: int(d[0]), # 車速(km/h)
            0x0F: lambda d: int(d[0]) - 40, # 吸気温度(C)
            0x10: lambda d: (256 * int(d[0]) + int(d[1])) / 100, # 空気流量(g)
            #0x2F: lambda d: int(d[0]) / 2.55, # 燃料残量(%)
            0x43: lambda d: ( 256 * int(d[0]) + int(d[1]) ) / 2.55, # 絶対負荷(%)
            0x44: lambda d: (256 * int(d[0]) + int(d[0])) / 32768, # 空燃比等量比指令(λ)
            #0x46: lambda d: int(d[0]) - 40, # 外気温(C)
            #0x48: lambda d: int(d[0]) / 2.55, # スロットル位置C(%)
            0x49: lambda d: int(d[0]) / 2.55, # スロットル位置D(%)
            #0x4B: lambda d: int(d[0]) / 2.55, # スロットル位置F(%)
            0x4C: lambda d: int(d[0]) / 2.55, # スロットルアクチュエーター指令(%)
        }
        self.supported_pids = self.dec_fomula.keys()


    def decoder(self, pid: int, data: bytes):
        """
        PID応答をデコードする

        Parameters
        ----------
         - pid (int) - OBD-IIのパラメタID
         - data (bytes) - 受信したバイナリデータ

        Exceptions
        -----------
         - ObdError - パラメタIDが不正だった場合の例外
        """

        try:
            return self.dec_fomula[pid](data)
        except KeyError as e :
            raise ObdError("デコードできないパラメタIDが指定されました")


    def request(self, service: int, pid: int) -> bytes:

        request = bytes([
            service,
            pid,
        ])

        response = self.transport.send_and_receive(request)

        if len(response) < 2:
            raise ObdError(
                f"Invalid response: {response.hex(' ')}"
            )

        # Negative Response
        #
        # 7F <service> <error>
        #
        if response[0] == 0x7F:
            if len(response) < 3:
                raise ObdError("Invalid negative response")

            raise ObdNegativeResponse(
                service=response[1],
                error_code=response[2],
            )

        # Positive response service = request service + 0x40
        expected_service = service + 0x40

        if response[0] != expected_service:
            raise ObdError(
                f"Unexpected service: "
                f"expected=0x{expected_service:02X}, "
                f"received=0x{response[0]:02X}"
            )

        if response[1] != pid:
            raise ObdError(
                f"Unexpected PID: "
                f"expected=0x{pid:02X}, "
                f"received=0x{response[1]:02X}"
            )

        return response[2:]

    def get_vin(self) -> str:
        """
        OBD-II Mode 09 / PID 02

        09 02 -> VIN
        """

        data = self.request(
            service=0x09,
            pid=0x02,
        )

        # Mode 09 PID 02 の返却データは
        # ISO-TP上で複数フレームになることがある。
        #
        # ECUによって先頭に余分なデータが入る場合もあるため、
        # ASCII printableなVINを抽出する。

        ascii_data = "".join(
            chr(b)
            for b in data
            if 0x20 <= b <= 0x7E
        )

        return ascii_data

        raise ObdError(
            f"VIN not found in response: {data.hex(' ')}"
        )


# ============================================================
# Application
# ============================================================

def main() -> None:

    # ---------------------------------------------
    # CANable
    # ---------------------------------------------

    can_transport = CanTransport(
        CanConfig(
            port="COM6",
            bitrate=500000,
        )
    )

    # ---------------------------------------------
    # OBD-II standard addressing
    #
    # Request  : 0x7DF
    # Response : 0x7E8
    # ---------------------------------------------

    iso_tp = IsoTpTransport(
        can_transport,
        IsoTpConfig(
            tx_id=0x7DF,
            rx_id=0x7E8,
        )
    )

    obd = ObdClient(iso_tp)

    try:
        can_transport.open()
        iso_tp.open()
    except:
        can_transport.close()
        raise Exception("ポート初期化に失敗")

    while True:
        time.sleep(0.1)
        try:
            for pid in obd.supported_pids:
                res_bin = obd.request(0x01,pid)
                res = obd.decoder(pid,res_bin)
                print("pid:",pid,"\tres:",res)
        except KeyboardInterrupt as e:
            can_transport.close()
            return
        except Exception as e:
            print(e)
            pass


if __name__ == "__main__":
    main()
