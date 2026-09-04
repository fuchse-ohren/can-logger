import time

import can


def get_vin_mode09(bus):
    # OBD-II Mode 09 PID 02
    req = can.Message(
        arbitration_id=0x7DF,
        data=[0x02, 0x09, 0x02, 0, 0, 0, 0, 0],
        is_extended_id=False,
    )

    print(f"TX 7DF  {req.data.hex(' ').upper()}")
    bus.send(req)

    first_frame = None

    # First Frameを待つ
    deadline = time.monotonic() + 2.0

    while time.monotonic() < deadline:
        msg = bus.recv(timeout=0.1)

        if msg is None:
            continue

        print(f"RX {msg.arbitration_id:03X}  {msg.data.hex(' ').upper()}")

        if msg.arbitration_id != 0x7E8:
            continue

        # ISO-TP First Frame
        if len(msg.data) >= 2 and (msg.data[0] >> 4) == 0x1:
            first_frame = msg
            break

        # Single Frame
        if len(msg.data) >= 1 and (msg.data[0] >> 4) == 0x0:
            length = msg.data[0] & 0x0F
            payload = bytes(msg.data[1 : 1 + length])

            if payload.startswith(b"\x49\x02"):
                return parse_vin_payload(payload)

    if first_frame is None:
        return None

    # --------------------------------------------------------
    # First Frame
    # --------------------------------------------------------

    total_length = ((first_frame.data[0] & 0x0F) << 8) | first_frame.data[1]

    payload = bytearray(first_frame.data[2:])

    print(f"ISO-TP total length = {total_length}")

    # --------------------------------------------------------
    # Flow Control
    # --------------------------------------------------------

    fc = can.Message(
        arbitration_id=0x7E0,
        data=[0x30, 0x00, 0x00, 0, 0, 0, 0, 0],
        is_extended_id=False,
    )

    print(f"TX 7E0  {fc.data.hex(' ').upper()}")
    bus.send(fc)

    # --------------------------------------------------------
    # Consecutive Frames
    # --------------------------------------------------------

    expected_sn = 1

    deadline = time.monotonic() + 2.0

    while len(payload) < total_length:
        if time.monotonic() >= deadline:
            print("Timeout waiting for Consecutive Frame")
            return None

        msg = bus.recv(timeout=0.1)

        if msg is None:
            continue

        print(f"RX {msg.arbitration_id:03X}  {msg.data.hex(' ').upper()}")

        if msg.arbitration_id != 0x7E8:
            continue

        pci_type = msg.data[0] >> 4

        if pci_type != 0x2:
            continue

        sn = msg.data[0] & 0x0F

        if sn != expected_sn:
            print(f"Unexpected sequence number: {sn}, expected {expected_sn}")
            return None

        payload.extend(msg.data[1:])

        expected_sn = (expected_sn + 1) & 0x0F

    payload = bytes(payload[:total_length])

    print("ISO-TP payload:", payload.hex(" ").upper())

    return parse_vin_payload(payload)


def parse_vin_payload(payload):
    """
    49 02 01 + 17-byte VIN
    """

    if not payload.startswith(b"\x49\x02"):
        return None

    # Mode 09 PID 02:
    #
    # 49 02 01 [VIN 17 bytes]
    #
    vin = payload[3:20].decode("ascii", errors="replace")

    if len(vin) == 17:
        return vin

    return None


bus = can.Bus(
    interface="slcan",
    channel="COM6",
    bitrate=500000,
)

vin = get_vin_mode09(bus)

print()
print("VIN:", vin)

bus.shutdown()
