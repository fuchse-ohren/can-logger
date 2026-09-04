from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import can
import isotp
import time


# ============================================================
# CAN Layer
# ============================================================

@dataclass
class CanConfig:
    port: str = "COM5"
    bitrate: int = 500000


class CanTransport:
    """
    CANable 2.0 + SLCAN を利用したCANトランスポート。
    OBD/ISO-TPの知識を持たない。
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

@dataclass
class IsoTpConfig:
    tx_id: int
    rx_id: int

    # ISO-TP parameters
    stmin: int = 0
    blocksize: int = 0
    wftmax: int = 0
    tx_data_length: int = 8


class IsoTpTransport:
    """
    ISO 15765-2 transport layer。
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
            "rx_flowcontrol_timeout": 1000,
            "rx_consecutive_frame_timeout": 1000,
            "tx_padding": 0x00,
            #"rx_padding": 0x00,
        }

        self.stack = isotp.CanStack(
            bus=self.can_transport.bus,
            address=address,
            params=params,
        )

    def send_and_receive(
        self,
        payload: bytes,
        timeout: float = 5.0,
    ) -> bytes:

        if self.stack is None:
            raise RuntimeError("ISO-TP stack is not open")

        self.stack.send(payload)

        deadline = __import__("time").monotonic() + timeout

        while __import__("time").monotonic() < deadline:
            self.stack.process()

            if self.stack.available():
                return self.stack.recv()

            __import__("time").sleep(0.001)

        raise TimeoutError("ISO-TP response timed out")


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

    現在:
        Mode 09 PID 02 -> VIN

    将来:
        Mode 01 PID
        Mode 03
        Mode 04
        Mode 09 その他PID
        等を追加可能。
    """

    def __init__(
        self,
        transport: IsoTpTransport,
    ):
        self.transport = transport

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

    def get_supported(self):
        pid = 0x80
        data = self.request(
            service=0x01,
            pid=pid,
        )
        print(pid,"\t",data.hex(" "))


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

        vin = obd.get_vin()

        print(f"VIN = {vin}")

        obd.get_supported()

    finally:
        can_transport.close()


if __name__ == "__main__":
    main()
