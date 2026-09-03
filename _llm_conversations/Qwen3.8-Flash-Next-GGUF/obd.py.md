## User

slcanファームを焼いたCANable 2.0ハードとWindows環境でVINを取得するサンプルを書いて下さい．
サンプルは将来的にOBDのPIDを指定して情報が取得できるように機能を適切にクラスや関数として分離して設計してください．

## Assistant

<details>
<summary>thinking</summary>

The user wants a sample that reads the VIN from a CANable 2.0 (flashed with slcan firmware) on Windows, and is designed by separating it into classes/functions so that OBD PIDs can be specified in the future.

Key points:
- CANable 2.0 on Windows with slcan firmware → recognized as a CDC serial port (COMx).
- Use python-can with the slcan backend: `can.Interface("slcan", channel="COM5", bitrate=500000)`.
- OBD-II: Use functional/request ID 0x7DF (or destination 0x7E0, source 0x7E8 for CAN500_11), Mode 09 PID 02 for VIN. VIN response is multi-frame (0x10 14 ... followed by consecutive frames 0x21.., 0x22..). Need ISO 15765-2 (CAN-TP) multi-frame handling — python-can has isotp implemented (can.isotp is deprecated. Use the `can.interfaces.isotp` IsoTpTransportLayer or the `python-isotp` library).

Actually, python-can has `can.isotp` (deprecated) — the recommended one is the standalone `isotp` package (python-isotp) that integrates with python-can: `import isotp; isotp.NotifierBasedCanStack(bus, params)`.

A simpler, more educational approach: implement a minimal ISO-TP handling yourself (FF/CF handling) in a small class — but for production I recommend python-isotp. Design:

- `SlcanBusFactory` / just create a can bus
- `IsoTpClient` (uses python-isotp)
- `OBDClient` with `read(pid, service=0x01/0x09)` handling multi-frame responses
- `Vehicle` / `VINReader`, or an example main that reads the VIN.

Windows considerations: The CANable 2.0 with slcan firmware shows up as a USB Serial Device (COM port). Might need the Zadig/USB Serial driver? CANable Lite/2.0 use CH340? Actually the CANable 2.0 uses the Canable Lite design with GD32F103? The CANable 2.0 is open hardware (derivative), uses a GD32F103 chip and exposes USB CDC serial. On Windows 10/11 it usually enumerates automatically as CDC. slcan commands: "O" open, "S8" or "S0" bitrate setting (slcan: S0=1M, S1=800k, S2=500k, S3=250k, S4=125k, S5=100k, S6=50k), "A" for auto-rx? python-can's slcan driver handles the initialization including `S` speed setting. Note: with python-can's slcan interface, specify bitrate=500000.

Also flow control: `can.isotp` is deprecated. The `isotp` package (python-isotp) is recommended. Code design:

```python
import can
import isotp

class ObdConfig: request_id=0x7E0, response_id=0x7E8 (or functional 0x7DF)
```

Better design:

- `CanBusConnector` — create a python-can bus from a COM port using the slcan backend.
- `ObdTransport` — ISO-TP stack wrapping the bus with isotp params.
- `ObdClient` — `query(service, pid)`, returns data bytes, handles negative response (0x7F).
- `VehicleDiagnostics` — high-level methods: `read_vin()`, `read_pid(0x01, 0x0D)` (speed), decoding of common PIDs.

VIN: Mode 09 PID 02, response `49 04 31 <17 bytes ASCII>` — multi-frame.

python-isotp usage:

```python
params = isotp.Params(
    address=isotp.Address(isotp.AddressingMode.Normal_11bits),
    txid=0x7E0, rxid=0x7E8,
    block_tx_send=False, block_tx_complete=True, stmin=0,
)
stack = isotp.NotifierBasedCanStack(bus, params)
stack.start()
stack.send(request)
response = stack.recv(timeout=5)  # Actually is it recv() with timeout? Does NotifierBasedCanStack.recv(timeout=...) exist?
```

python-isotp API: `stack.send(data)`, `stack.recv(timeout=None)` — I think recv accepts a timeout parameter. Yes: in newer versions (v3.0+), `recv(timeout=None)` returns None on timeout. Check: python-isotp's IsoTPStack.recv(timeout: float = None). Yes, v3 added the timeout parameter.

As an alternative, use `stack.isotp_layer`... To keep it simple: use send/recv with timeout.

Note: VIN is often answered with functional addressing too, but use physical addressing with a fallback. Keep it simple: physical 0x7E0/0x7E8 (default for CAN vehicles) and mention the 0x7DF broadcast option.

Also mention: CANable 2.0 needs bitrate 500k, termination, and connection to the DLC's OBD port (pins 6, 14, 4/5, 16).

Windows: check the COM port in Device Manager. Install driver if needed. python-can slcan needs pyserial.

I'll write a single-file sample using dataclass. Maybe include CLI arguments (port, service, pid). Keep the code concise and structured.

Should I verify via web search? Design is standard knowledge. I can quickly double-check the isotp recv timeout signature. Do a quick search to confirm the API of python-isotp's NotifierBasedCanStack recv timeout. Also confirm support for the CANable 2.0 slcan interface in python-can. Do one search.

Per instructions: keep it concise, use tables, "da/deru" style, 🦊 on the first line if following instructions. Since this is a code request, provide code. Keep the explanation minimal.

Let me quickly verify the python-isotp API.


</details>

**tool call:** `web_search`

**query:** `python-isotp NotifierBasedCanStack recv timeout API example`

**result:**

```
Title: Pure Python Implementation — isotp 2.0.7 documentation
URL: https://can-isotp.readthedocs.io/en/latest/isotp/implementation.html
Snippet: For example, if you want to rely on python-can for the support of your CAN interface, you will need to run the IsoTP layer in Python.An IsoTP transport layer implementation that runs in a separate thread. The main public interface are start, stop, send, recv.

---

Title: python-can-isotp/doc/source/isotp/examples.rst at...
URL: https://github.com/pylessard/python-can-isotp/blob/v2.x/doc/source/isotp/examples.rst
Snippet: Examples. Blocking transmission with python-can. # In this example, we transmit a payload using a blocking send() import isotp import logging. from can.interfaces.socketcan import SocketcanBus.

---

Title: socket — Low-level networking interface — Python...
URL: https://docs.python.org/3/library/socket.html
Snippet: Notes on socket timeouts. Timeouts and the connect method.CAN_ISOTP protocol requires a tuple (interface, rx_addr, tx_addr) where both additional parameters are unsigned long integer that represent a CAN identifier (standard or extended).

---

Title: How to set timeout on python's socket recv method? - Stack Overflow
URL: https://stackoverflow.com/questions/2719017/how-to-set-timeout-on-pythons-socket-recv-method
Snippet: The socket.recv() seems to time out for me just fine after setting socket.settimeout(), exactly as intended.You can use socket.settimeout() which accepts a integer argument representing number of seconds. For example, socket.settimeout(1) will set the timeout to 1 second.

---

Title: Python Playground - Online Python Programming IDE
URL: https://programiz.pro/ide/python
Snippet: Python Playground: An online IDE to practice Python programming. Write, edit & run code online. Suitable for all skill levels. Try now.

---

IMPORTANT: These are only short snippets. To get the full page content, call web_search with the url parameter (e.g. {"url": "<URL>"}).

---

Images from this search. To show one, write its token exactly as given, e.g. [[img:5767ba86600c]], on its own line after the text it illustrates. Use only these tokens, and only where the image clearly matches. For a picture of a specific thing you name, call web_search with image_queries instead.
- [[img:5767ba86600c]] Facing issues in Custom Transport "CAN-ISOTP" · Issue #608 · micro-ROS ... — github.com
- [[img:b4c4e8b6f48e]] Isotp Transport layer can't recieve can in time · Issue #51 · pylessard ... — github.com
- [[img:0d4de50a0a29]] Isotp Transport layer can't recieve can in time · Issue #51 · pylessard ... — github.com
- [[img:63b6fde256be]] Pure Python Implementation — isotp 2.0.6 documentation — can-isotp.readthedocs.io
- [[img:f18f35ec0f04]] 【python-can】ISO-TP通信でFunctional Addressで送信する | かきエレ — kakitamablog.com
- [[img:de1c2be7ce69]] การส่งข้อมูลบนเครือข่าย CAN ด้วย ISO transport protocol (ISOTP ... — techsquare.co.th
```

**tool call:** `web_search`

**query:** `python-can slcan interface CANable COM port Windows bitrate setup`

**result:**

```
Title: CAN over Serial / SLCAN - python-can 4.6.1 documentation
URL: https://python-can.readthedocs.io/en/stable/interfaces/slcan.html
Snippet: CAN over Serial / SLCAN ¶ A text based interface: compatible to slcan-interfaces (slcan ASCII protocol) should also support LAWICEL direct. These interfaces can also be used with socketcan and slcand with Linux. This driver directly uses either the local or remote serial port, it makes slcan-compatible interfaces usable with Windows also.

---

Title: can.interfaces.slcan - python-can 4.6.1 documentation
URL: https://python-can.readthedocs.io/en/stable/_modules/can/interfaces/slcan.html
Snippet: can.interfaces.slcan - python-can 4.6.1 documentation Source code for can.interfaces.slcan

---

Title: python-can/can/interfaces/slcan.py at main - GitHub
URL: https://github.com/hardbyte/python-can/blob/main/can/interfaces/slcan.py
Snippet: The can package provides controller area network support for Python developers - hardbyte/python-can

---

Title: python-can/doc/interfaces/slcan.rst at main - GitHub
URL: https://github.com/hardbyte/python-can/blob/develop/doc/interfaces/slcan.rst
Snippet: CAN over Serial / SLCAN A text based interface: compatible to slcan-interfaces (slcan ASCII protocol) should also support LAWICEL direct. These interfaces can also be used with socketcan and slcand with Linux. This driver directly uses either the local or remote serial port, it makes slcan-compatible interfaces usable with Windows also.

---

Title: Python CAN / SLCAN send and receive example - TechOverflow
URL: https://techoverflow.net/2024/07/30/python-can-slcan-send-and-receive-example/
Snippet: SLCAN is a CAN interface protocol operating via serial communication. It's often used to connect to CAN interfaces via USB. The following example uses the python-can library to send and receive CAN messages via SLCAN. The basic intention is to have two separate CAN adapters (such as the really cheap FYSETC UCAN with the slcan firmware) First, install the python-can library:

---

IMPORTANT: These are only short snippets. To get the full page content, call web_search with the url parameter (e.g. {"url": "<URL>"}).

---

Images from this search. To show one, write its token exactly as given, e.g. [[img:e1714a6e5e34]], on its own line after the text it illustrates. Use only these tokens, and only where the image clearly matches. For a picture of a specific thing you name, call web_search with image_queries instead.
- [[img:e1714a6e5e34]] Makerbase CANable 2.0 SHELL USB to CAN adapter analyzer CANFD slcan ... — shopee.com.my
- [[img:7d1e7294f250]] Bafang CAN Bus Programming (Electronics) — Kaspars Dambis — kaspars.net
- [[img:648fd5b57ede]] USB To CAN CANable v1 USBCAN Analyzer Adapter python-CAN Communication ... — aliexpress.com
- [[img:6b9e7ce1343f]] 1 PCS TYPE-C USB to CAN Module CANable SLCAN Debugger CAN Bus ... — daraz.lk
- [[img:81ee072c4195]] Amazon.com: CANable Pro USB to CAN CANable USBCAN Analyzer Adapter ... — amazon.com
- [[img:a903fdf48404]] CANable 2.0 USB To CAN Cangaroo Candlelight CAN-FD SLCAN Firmware ... — aliexpress.com
```

<details>
<summary>thinking</summary>

I have enough knowledge. Just to be safe, let me quickly check the signature of `recv` with timeout from the isotp documentation (v3.x has `recv(timeout=None)`). To be certain, I'll fetch the implementation page of the isotp docs.


</details>

**tool call:** `web_search`

**query:** `isotp stack.recv(timeout) NotifierBasedCanStack send recv timeout None python-isotp 3.0`

**result:**

```
Title: Python support for IsoTP Transport protocol (ISO-15765) — isotp 2.0.7 documentation
URL: https://can-isotp.readthedocs.io/en/latest/
Snippet: The NotifierBasedCanStack object has been introduced and uses a notifier instead of calling bus.recv(), solving the popular issue of a CanStack depleting the receive queue and starving other modules from their incoming messages

---

Title: Pure Python Implementation — isotp 2.0.7 documentation
URL: https://can-isotp.readthedocs.io/en/latest/isotp/implementation.html
Snippet: The IsoTP transport layer pre configured to use python-can as CAN layer. python-can must be installed in order to use this class. All parameters except the bus parameter will be given to the TransportLayer constructor · This class directly calls bus.recv, consuming the message from the receive queue, potentially starving other application. Consider using the NotifierBasedCanStack to avoid starvation issues

---

Title: Releases · pylessard/python-can-isotp
URL: https://github.com/pylessard/python-can-isotp/releases
Snippet: The isotp.socket.recv does not return None on Timeout anymore ... isotp.socket.bind now requires an isotp.Address object and is no more backward compatible with old interface ... Timing behaviors has been globally improved.

---

Title: isotp.protocol — isotp 2.0.7 documentation
URL: https://can-isotp.readthedocs.io/en/latest/_modules/isotp/protocol.html
Snippet: All parameters except the ``bus`` parameter will be given to the :class:`TransportLayer` constructor This class directly calls ``bus.recv``, consuming the message from the receive queue, potentially starving other application. Consider using the :class:`NotifierBasedCanStack` to avoid starvation issues :param bus: A python-can bus object implementing ``recv`` and ``send`` :type bus: can.BusABC :param args: Passed down to :class:`TransportLayer`. ``rxfn`` and ``txfn`` are predefined :type args: N/A :param kwargs: Passed do

---

Title: isotp.socket() behavior deviates from python sockets on timeouts · Issue #46 · pylessard/python-can-isotp
URL: https://github.com/pylessard/python-can-isotp/issues/46
Snippet: June 21, 2021 - A standard python socket would encounter a socket.timeout Exception on recv() if no data came in. The can-isotp package, on the other hand, catches the exception and converts it into a return None. I think this is wrong for several reaso...

---

IMPORTANT: These are only short snippets. To get the full page content, call web_search with the url parameter (e.g. {"url": "<URL>"}).

---

Images from this search. To show one, write its token exactly as given, e.g. [[img:1f2b87330168]], on its own line after the text it illustrates. Use only these tokens, and only where the image clearly matches. For a picture of a specific thing you name, call web_search with image_queries instead.
- [[img:1f2b87330168]] Facing issues in Custom Transport "CAN-ISOTP" · Issue #608 · micro-ROS ... — github.com
- [[img:5488c384e067]] ISO15765 ISO-TP DoCAN Stack for UDS communication protocol — rapidseasuite.com
- [[img:bd2610f84251]] Isotp Transport layer can't recieve can in time · Issue #51 · pylessard ... — github.com
- [[img:c9758bd731b5]] Consecutive frame timeout not raised after a Flow Control triggered by ... — github.com
- [[img:fc0b89e92c91]] การส่งข้อมูลบนเครือข่าย CAN ด้วย ISO transport protocol (ISOTP ... — techsquare.co.th
- [[img:f8a3add0e63f]] STM32Cube Expansion Pack CAN Stack: IsoTp Class Reference — tmaniacdev.github.io
```

<details>
<summary>thinking</summary>

I'll write the code using the pattern I know well:

```python
import isotp
params = isotp.Params(
    address=isotp.Address(isotp.AddressingMode.Normal_11bits, txid=tx, rxid=rx),
    stmin=0, block_size=0, ...
)
stack = isotp.NotifierBasedCanStack(bus, params)
stack.start()
stack.send(payload, block=True)
data = stack.recv(timeout=2.0)
stack.stop()
```

Note: v3.x's `stack.send(data, block=True)` supports block and timeout parameters. `recv(timeout=None)` returns None on timeout (v3 behavior; in v2 it always returned None on timeout anyway... actually in v2 recv blocks; the 2.0.7 docs say "recv(timeout=None)"? Not sure. Safe bet: install the latest `pip install python-can python-isotp pyserial`. In recent versions recv(timeout=...) works. Pin it with `pip install "python-can>=4" "python-isotp>=3"`. In v3.0.0, `recv` does indeed take a timeout and returns None on timeout (release notes: "isotp.socket.recv does not return None on Timeout anymore" — that's about isotp.socket, and does the stack's recv throw IsoTPTimeoutError? Hmm.

Let me check carefully. In python-isotp v3.x, the protocol layer has `data_available()` and a blocking `recv()`; the IsoTPStack's recv signature: `def recv(self, timeout: float = None) -> bytes | None`? In 3.x, does TransportLayer.recv with timeout throw `IsoTPTimeoutError`? Actually, does isotp have an exception class `isotp.IsoTPTimeoutError`? Is there an `isotp.exceptions`? From memory, the v3 changelog: "Timeout passed to TransportLayer.recv() now raises IsoTPTimeoutError instead of returning None" — not 100% sure.

To avoid API uncertainty, we could implement recv with a loop: check `stack.data_available()`? Hmm, that's also API-dependent.

Alternative solid approach: avoid python-isotp and implement minimal ISO-TP multi-frame handling directly on top of python-can. For OBD use with a single ECU it's simple and reliable (send FF, receive CF; FF.CI=0 requires no flow control; FC frame from the ECU comes before the CF). Actually, ISO-TP receiver: ECU sends FF, receiver must respond with FC (CTS) before the ECU sends CF. So manual implementation: send request, wait for FF (0x1X LL..), send FC (0x30 0x00 0x00), receive CF group. Single frame case: 0x0L data. That's about 40 lines, with zero additional dependencies. And it's educational — the user wants a learning-quality design.

But python-isotp is more robust. I could also use python-isotp and handle both behaviors: wrap recv in try/except and check the result. The simplest thing is to write our own small ISO-TP client — that removes dependency uncertainty and works on Windows too. But robustness (STmin, timeouts, BS) — as an OBD client BS=0, STmin from the FC, standard behavior. Manual implementation is sufficient and common in OBD samples.

Design decision: use python-can + python-isotp (recommended) — but the API risk... let me quickly fetch the v3 protocol module source and confirm the recv signature.


</details>

**tool call:** `web_search`

**url:** `https://raw.githubusercontent.com/pylessard/python-can-isotp/v3.x/isotp/protocol.py`

**result:** `Failed to fetch URL: HTTP 404 Not Found`

<details>
<summary>thinking</summary>

Let's fetch the isotp v3 source from GitHub master: https://raw.githubusercontent.com/pylessard/python-can-isotp/master/isotp/protocol.py — it might be large. Or maybe just the readthedocs for 3.x would do: https://can-isotp.readthedocs.io/en/latest/isotp/implementation.html. But that's 2.0.7. I'll try the raw on GitHub master.


</details>

**tool call:** `web_search`

**query:** `"isotp" "stack.recv(timeout" example NotifierBasedCanStack returns None timeout`

**result:**

```
Title: Pure Python Implementation — isotp 2.0.7 documentation
URL: https://can-isotp.readthedocs.io/en/latest/isotp/implementation.html
Snippet: A value between 20ms-500ms should generally be good. Meaningless if the provided rxfn ignores its timeout parameter · If python-can must be used as CAN layer, one can use the isotp.CanStack and isotp.NotifierBasedCanStack which extends the TransportLayer object with predefined functions that calls python-can.

---

Title: Python support for IsoTP Transport protocol (ISO-15765) — isotp 2.0.7 documentation
URL: https://can-isotp.readthedocs.io/en/latest/index.html
Snippet: The API now comply with the Python socket API and will raise the proper exception in case of timeout. isotp.socket.bind now requires an isotp.Address object and is no more backward compatible with old interface · The error handler is called from a different thread · The TransportLayer object is now an extension of the legacy v1.x TransportLayer, which has been renamed to TransportLayerLogic. See Backward Compatibility and Legacy Methods · On top of that, some improvement makes v2.x preferable over v1.x · The NotifierBasedCanStack object has been introduced and uses a notifier instead of calling bus.recv(), solving the popular issue of a CanStack depleting the receive queue and starving other modules from their incoming messages

---

Title: Examples — isotp 2.0.7 documentation
URL: https://can-isotp.readthedocs.io/en/latest/isotp/examples.html
Snippet: import isotp from typing import Optional def my_rxfn(timeout:float) -> Optional[isotp.CanMesage]: # All my_hardware_something and get_something() function are fictive of course. msg = my_hardware_api_recv(timeout) # Blocking read are encouraged for better timing. if msg is None: return None # Return None if no message available return isotp.CanMesage(arbitration_id=msg.get_id(), data=msg.get_data(), dlc=msg.get_dlc(), extended_id=msg.is_extended_id()) def my_txfn(isotp_msg:isotp.CanMesage): # all set_something functions and my_hardware_something are fictive.

---

Title: Releases · pylessard/python-can-isotp
URL: https://github.com/pylessard/python-can-isotp/releases
Snippet: The isotp.socket.recv does not return None on Timeout anymore ... isotp.socket.bind now requires an isotp.Address object and is no more backward compatible with old interface ... Timing behaviors has been globally improved.

---

Title: isotp.protocol — isotp 2.0.7 documentation
URL: https://can-isotp.readthedocs.io/en/latest/_modules/isotp/protocol.html
Snippet: All parameters except the ``bus`` parameter will be given to the :class:`TransportLayer` constructor This class directly calls ``bus.recv``, consuming the message from the receive queue, potentially starving other application. Consider using the :class:`NotifierBasedCanStack<...

---

IMPORTANT: These are only short snippets. To get the full page content, call web_search with the url parameter (e.g. {"url": "<URL>"}).

---

Images from this search. To show one, write its token exactly as given, e.g. [[img:f1bf33db8701]], on its own line after the text it illustrates. Use only these tokens, and only where the image clearly matches. For a picture of a specific thing you name, call web_search with image_queries instead.
- [[img:f1bf33db8701]] การส่งข้อมูลบนเครือข่าย CAN ด้วย ISO transport protocol (ISOTP ... — techsquare.co.th
- [[img:a8c23b82e61b]] ISO15765 ISO-TP DoCAN Stack for UDS communication protocol — rapidseasuite.com
- [[img:611622eccf35]] Isotp Transport layer can't recieve can in time · Issue #51 · pylessard ... — github.com
- [[img:e4bf8bad29e6]] Solved: Notifier timeout behavior - NI Community — forums.ni.com
- [[img:85636463f21a]] Pure Python Implementation — isotp 2.0.6 documentation — can-isotp.readthedocs.io
- [[img:d9468b96f8fb]] Solved: Notifier timeout behavior - NI Community — forums.ni.com
```

<details>
<summary>thinking</summary>

Regarding isotp's recv timeout semantics: in v2/v3, does `TransportLayer.recv(timeout=None)` return None on timeout? Actually, the v2 release notes say that isotp.socket.recv raises an exception on timeout (socket API), but does TransportLayer.recv return None on timeout? In v2.x's protocol.py: `def recv(self, timeout=None)` — "If a timeout is specified and elapsed, returns None" — I think TransportLayer.recv returns None on timeout. And IsoTPStack inherits recv. Many examples online use `data = stack.recv(timeout=...)` with a None check... hmm, but the older v2 docs said recv blocks without a timeout, and returns None if there's nothing on the queue? In v2: recv() without a timeout blocks indefinitely until data arrives? The docstring says: ":param timeout: ... If None, waits forever... Returns bytes or None". I'm fairly confident that if you pass a timeout parameter to TransportLayer.recv in v2.x/v3.x, it returns None on timeout.

To be robust across versions, code defensively: wrap in try/except, treat None as timeout. Pin to python-isotp>=3,<4? No, avoid over-engineering; pin to `python-isotp>=2.0.6`, and use `stack.recv(timeout=...)` with a None check plus a generic exception guard.

Okay, let me write a sample. Structure (single file for the sample):

```
obd/
  __init__.py
  bus.py        # SlcanConnector
  isotp_client.py# IsoTpClient (send/receive)
  obd.py        # ObdClient (service/pid queries, negative response handling)
  vehicle.py    # VehicleInfo (VIN, PIDs)
main.py
```

Or, a single file with classes for the sake of the sample's conciseness. The user's request is "properly separate into classes and functions (適切にクラスや関数として分離)" — a modular single file with clear classes is acceptable, but small package splits would show the design better. Single file might be easier to run. Let me do a single-file `obd_tool.py` with the following classes:

- `SlcanCanBus` (context manager): opens a python-can slcan bus on a COM port at 500k.
- `IsoTpClient`: wraps NotifierBasedCanStack, `request(payload, timeout)`.
- `ObdClient`: `query(service:int, pid:int, timeout)` → bytes (payload with SID/PID stripped); handles 0x7F negative responses → raises `ObdNegativeResponse`.
- `VehicleInfo`: `read_vin()`, `read_pid(service,pid)` via data decode, a `PIDS` registry for decoding (e.g., engine RPM (pid 0x0C), vehicle speed 0x0D, coolant temperature 0x05, fuel level 0x2F).
- CLI with argparse in `main()`: `--port COM5 --vin`, `--svc 01 --pid 0D`.

VIN details: request `09 02`; response `49 04 01 <17 ASCII bytes>` → strip `0x49 0x04 0x01`, decode ASCII, strip padding (0x00, spaces, 0xAA? — trailing nulls and spaces stripped).

Addressing: default is physical 0x7E0→0x7E8; optional --txid/--rxid; note on functional 0x7DF (send-only; can use for multi-ECU VIN but need to pick one response — keep it simple, physical + mention in comments).

Windows procedure table: install driver (CANable 2.0 is USB CDC, auto-recognized on Win10+), check COM in Device Manager, wiring table (pin 6 H, 14 L, 4/5 GND, 16 +12V), 120Ω termination (does CANable 2.0 have a switch? CANable 2.0 — does it have a termination jumper? Does CANable Lite have a 120Ω jumper? Does CANable 2.0 have solder jumpers / a switch? I think CANable 2.0 includes an on-board 120Ω termination jumper. Mention termination in general terms).

pip install: `pip install python-can python-isotp pyserial`.

slcan-specific notes: python-can's slcan auto-initializes (sets "S" bitrate code, opens with "O"). bitrate must be one of the slcan-supported rates (500000). Also a `can_fd=False` parameter? Not needed.

Another note: does python-can's slcan interface expect `timing`? No, the bitrate parameter works.

Write the code:

```python
"""..."""
from __future__ import annotations
import argparse
import dataclasses
from dataclasses import dataclass
from typing import Optional

import can
import isotp


# ---------- Exceptions ----------
class ObdError(Exception): ...
class ObdTimeoutError(ObdError): ...
class ObdNegativeResponse(ObdError):
    def __init__(self, service, error_code):
        self.service = service
        self.error_code = error_code
        super().__init__(f"Negative Response: service=0x{service:02X}, error=0x{error_code:02X} ({NRC.get(error_code,'?')})")

NRC = {0x10:"notSupported", ...}  # small subset

@dataclass(frozen=True)
class ObdAddress:
    tx_id: int = 0x7E0
    rx_id: int = 0x7E8

class CanBus:  # SlcanConnector
    def __init__(self, port, bitrate=500_000):
        self._bus = can.Bus(interface="slcan", channel=port, bitrate=bitrate)
    ...context manager, property bus

class IsoTpClient:
    def __init__(self, bus: can.BusABC, addr: ObdAddress):
        params = isotp.Params(
            address=isotp.Address(isotp.AddressingMode.Normal_11bits, txid=addr.tx_id, rxid=addr.rx_id),
            stmin=0, blocksize=8, stmin_separation_threshold?  # keep minimal
        )
        self._stack = isotp.NotifierBasedCanStack(bus, params)
        self._stack.start()
    def request(self, payload: bytes, timeout=2.0) -> bytes:
        self._stack.flush_rx_queue()?  # exists in v3 (does the stack have flush_tx_queue/flush_rx_queue methods? Does IsoTPStack have flush_tx_queue? Does TransportLayer have flush_tx_queue() and flush_rx_queue()? v2.0+: `flush_tx_queue()`, `flush_rx_queue()` — not sure about rx.)
```

Hmm, flush_rx_queue exists in v2+ (TransportLayer.flush_rx_queue? not sure). Let me try/except or skip flush and defensively ignore the stale issue... Better: drain the bus queue? Keep it simple: if isotp >=2.0.6 has flush_rx_queue, try calling it. In v2.0.7 protocol.py: I recall the `TransportLayer` has `flush_tx_queue()` and `flush_rx_queue()`. Yes, added in 2.0. Guard with hasattr.

Also `stack.send(payload, block=True, timeout=timeout)`? v2's send signature: `send(self, msg, block=True, timeout=None)` — throws exception on block timeout. v3: send is async; use `await`? No, in v3 the stack's send is also `send(msg, block=True, timeout=None)`? I think it's still valid in v3.x too.

Response for multi-frame reception is handled by the stack.

class ObdClient:
    def __init__(self, isotp_client, timeout=2.0, functional=None)
    def query(self, service:int, pid:int|None=None, *extra) -> bytes:
        req = bytes([service]) + (bytes([pid]) if pid is not None else b"")
        resp = self._tp.request(req, timeout)
        if resp[0] == service + 0x40: neg = resp[0]==0x7F → raise
        return resp[1:]  # strip SID (+PID? for 09 02, response is 49 04 01...; keep raw, let the high-level side parse)

For Mode 01 PID responses, keep the payload after SID? For simplicity, return the full response and let each method parse it.

class Vehicle:
    def __init__(self, obd: ObdClient)
    def read_vin(self)->str
    def read_pid01(self, pid:int)->bytes
    Decoders: a dict of pid → (name, decode function, unit).

main(): argparse; a list COM ports function `list_ports` using serial.tools.list_ports.

Also VIN via functional addressing (0x7DF) to probe which ECUs respond with VIN? Skip — leave optional: `--probe` scans? Keep the sample focused, but the user wants "in the future you can specify OBD PIDs to retrieve information (将来的にOBDのPIDを指定して情報が取得できる)" — a CLI `--svc/--pid` covers that.

Add CAN ID probing too: many cars use RX at 0x7E8; mention alternative ID pairs in a comment (0x7E0/0x7E8, 0x7DF functional, 0x726/0x72D for Mazda, etc.). Keep it short.

Also mention safety: don't drive while fiddling; ignition ON, engine can be off.

Response structure (da/de-aru style, concise, tables, emoji headers):
- 🦊 first line
- Setup (pip table, wiring table, COM check)
- Code (1 file)
- How to run
- Short notes (addressing, NRC, extension points)

Keep prose minimal. Now carefully write the code.

CANable 2.0 details: uses CANable 2.0 open hardware (a CANable fork by oscii-bot?), normally has USB-C with candleLight/canable firmware pre-flashed; the user already flashed slcan. On Windows, with slcan firmware it enumerates as USB Serial Device (CDC) — no driver needed on Win10+. python-can slcan maps bitrate to slcan S command (500k → S4? actually the slcan codes are: 0=1M? in the LAWICEL spec: S0=1000k? LAWICEL speed codes: 1=1M? The spec table says: S0=1M? Actually LAWICEL: 0=10k? Hmm — python-can handles it so no need to state explicitly.)

CANable 2.0 termination: I think CANable 2.0 has a "term" jumper/switch? CANable 1.0 has solder pads J1 for 120Ω. CANable 2.0 (makerbase?) — I think CANable 2.0 has a termination jumper. Say "enable on-board 120Ω termination if available (車載OBD端口は通常既に120Ω終端済み — in-vehicle OBD ports usually already have 120Ω termination)".

Actually note: since the car side has termination, only add termination on the adapter side if the bus is unterminated. Keep it to a one-liner.

Write the code:

```python
"""
OBD-II Client sample for CANable 2.0 (slcan firmware) + Windows
- VIN read (Mode 09, PID 02)
- Supports arbitrary service/PID queries
Dependencies: pip install python-can python-isotp pyserial
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Callable, Optional

import can
import isotp


# ---------------------------------------------------------------- 例外定義

class ObdError(Exception): ...
class ObdTimeoutError(ObdError): ...

class ObdNegativeResponse(ObdError):
    def __init__(self, service: int, code: int) -> None:
        self.service, self.error_code = service, code
        super().__init__(
            f"Negative Response (service=0x{service:02X}, NRC=0x{code:02X} {NRC.get(code, '')})"
        )

NRC = {
    0x00: "positiveResponse",
    0x10: "generalReject",
    0x11: "serviceNotSupported",
    0x12: "subFunctionNotSupported",
    0x13: "incorrectMessageLength",
    0x31: "requestOutOfRange",
    0x33: "securityAccessDenied",
    0x78: "responsePending",
}
```

Note: is responsePending (0x78) handled by isotp? No — 0x78 is an application-layer thing; does python-isotp auto-handle 0x7F 78? Does python-isotp have an option to treat 0x78 as pending? isotp.Params... no, does python-isotp handle "wftda"? No, that's J1939. isotp.Params does... no. UDS 0x78 handling is app-layer; can be looped: while negative response code==0x78, keep recv-ing. Nice touch — implement in ObdClient.query loop.

Address configuration:

```python
@dataclass(frozen=True)
class ObdAddress:
    tx_id: int = 0x7E0      # request (physical addressing)
    rx_id: int = 0x7E8      # response
    extended: bool = False

    @staticmethod
    def j1898_default(): return ObdAddress()
```

Bus connector:

```python
class SlcanBus:
    """CANable 2.0 (slcan) connection. Windows COM port name (e.g. "COM5") is the identifier."""
    def __init__(self, port: str, bitrate: int = 500_000) -> None:
        self.bus = can.Bus(interface="slcan", channel=port, bitrate=bitrate)

    def close(self) -> None: self.bus.shutdown()
    __enter__/__exit__
```

Transport layer:

```python
class IsoTpTransport:
    """ISO 15765-2 (CAN-TP) communication. Absorbs multi-frame responses like VIN."""
    def __init__(self, bus, addr, stmin=0, block_size=0):
        params = isotp.Params(
            address=isotp.Address(
                isotp.AddressingMode.Normal_11bits,
                txid=addr.tx_id, rxid=addr.rx_id,
            ),
            blocksize=block_size, stmin=stmin,
            wftmax=0,
        )
        self._stack = isotp.NotifierBasedCanStack(bus, params)
        self._stack.start()

    def request(self, payload: bytes, timeout: float = 2.0) -> bytes:
        if hasattr(self._stack, "flush_rx_queue"):
            self._stack.flush_rx_queue()
        self._stack.send(payload, block=True, timeout=timeout)
        data = self._stack.recv(timeout=timeout)
        if data is None:
            raise ObdTimeoutError(f"No response within {timeout}s for {payload.hex(' ').upper()}")
        return bytes(data)

    close(): self._stack.stop()
```

isotp.Address with AddressingMode as first positional arg — in v2: `isotp.Address(isotp.AddressingMode.Normal_11bits, txid=..., rxid=...)`? Address signature: `Address(mode_or_isotpparams, txid=None, rxid=None...)`. Common examples show `isotp.Address(isotp.AddressingMode.Normal_11bits)` and... actually the examples show `address=isotp.Address(0x123, 0x124)`? In v2 examples:

```python
params = isotp.Params(
    address = isotp.Address(isotp.AddressingMode.Normal_11bits),
    ...
)
```
For 11-bit normal mode, txid/rxid are also accepted as kwargs to Params (legacy Params has txid/rxid fields). Safer: `isotp.Address(txid=0x7E0, rxid=0x7E8)` — mode is inferred from txid being <=0x7FF → Normal_11bits. Yes, if txid/rxid are given and the values fit, Address infers the mode. To be explicit, pass mode and txid/rxid as kwargs: Address(mode, txid=..., rxid=...) — signature is `def __init__(self, mode=None, txid=None, rxid=None, ...)` I think. In v2 source: `Address(self, mode = None, txid = None, rxid = None, ...)`? From memory the Address constructor is: `Address(mode_or_addr, txid, rxid)`. Going with `isotp.Address(isotp.AddressingMode.Normal_11bits, txid=..., rxid=...)` — matches the docs example for 11-bit normal (kakitamablog's example uses Address(isotp.AddressingMode.Normal_11bits)? but they set txid/rxid in Params...). Hmm. To minimize risk: pass both mode and txid/rxid as kwargs. If Address's signature is (mode=None, txid=None, rxid=None) it works. I'm fairly sure it's `Address(self, mode=None, txid=None, rxid=None, ...)`? Actually v2 docstring: "Address(mode, txid, rxid...)". OK.

OBD client:

```python
class ObdClient:
    """Sends/receives OBD-II (ISO 15765-4) service requests."""
    def __init__(self, transport, timeout=2.0): ...

    def query(self, service: int, pid: Optional[int] = None, *, timeout=None) -> bytes:
        t = timeout or self._timeout
        req = bytes([service]) + (bytes([pid]) if pid is not None else b"")
        while True:
            resp = self._tp.request(req, timeout=t)
            if resp and resp[0] == 0x7F:
                if len(resp) >= 3 and resp[2] == 0x78:   # responsePending: keep waiting
                    continue
                raise ObdNegativeResponse(resp[1] if len(resp)>1 else service, resp[2] if len(resp)>2 else 0)
            if not resp or resp[0] != service + 0x40:
                raise ObdError(f"Unexpected response: {resp.hex(' ').upper()}")
            return resp  # response with SID stripped, full form
    
    def read_vin(self)->str:
        data = self.query(0x09, 0x02)  # 49 04 01 + 17 bytes
        if len(data) < 5 or data[0] != 0x49 or data[1] != 0x04: raise ...
        vin = data[3:].decode("ascii", "ignore")  # wait: 49 04 01 → counter byte 01 is at index 2
        return vin.strip("\x00 \xAA")?  # strip whitespace and control chars
```

VIN byte cleanup: filter to printable characters. `''.join(ch for ch in raw if ch.isprintable())`... plus strip nulls. Also count should be 0x04 meaning 4 frames of data; payload after 49 04 04? Wait, response is `49 04 01 <17 bytes>`: 0x49 = 0x09+0x40, 0x04 = number of data frames, 0x01 = VIN message counter. Payload = bytes after 3 bytes = 17 bytes of VIN. OK: `data[3:20]`.

VIN decoding: `bytes(b for b in data[3:] if 0x20 <= b <= 0x7E)` decoded.

PID decode registry:

```python
@dataclass(frozen=True)
class PidDefinition:
    name: str
    unit: str
    decode: Callable[[bytes, bytes], float | str]

MODE01_PIDS: dict[int, PidDefinition] = {
    0x00: ... skip
    0x04: engine load: A*100/255 %
    0x05: coolant temp A-40 ℃
    0x0C: RPM (256A+B)/4
    0x0D: speed A km/h
    0x0F: intake temp A-40
    0x11: TPS A*100/255
    0x2F: fuel level A*100/255
}
```

Vehicle layer:

```python
class Vehicle:
    """High-level API. More methods can be added here as needed."""
    def __init__(self, obd): self._obd = obd
    def read_vin(self)->str: return self._obd.read_vin()
    def read_mode01(self, pid:int):
        resp = self._obd.query(0x01, pid)  # 41 PID A B...
        a = resp[2] if len(resp)>2 else None ...
        defn = MODE01_PIDS.get(pid)
        return formatted if defn else raw
```

CLI:

```python
def scan_com_ports():
    from serial.tools import list_ports
    return list(list_ports.comports())

def build_parser()...
main():
    args: --port COM5 (default scan), --bitrate 500000, --txid 0x7E0 --rxid 0x7E8, subcommand-like: --vin flag, or --service/--pid query, list-pids action.
```

Keep the CLI simple: default action = print VIN; `--pid N` with `--service` for raw queries.

Full main:

```python
def main(argv=None):
    args = build_parser().parse_args(argv)
    port = args.port or auto_select_port()
    addr = ObdAddress(tx_id=..., rx_id=...)
    try:
        with SlcanBus(port, args.bitrate) as bus:
            with IsoTpTransport(bus, addr) as tp:  # or without context
                vehicle = Vehicle(ObdClient(tp, timeout=args.timeout))
                ...
    except KeyboardInterrupt...
    except (ObdError, can.CanError) as e: print error, exit 1
```

Nested context managers: SlcanBus returns .bus via __enter__ to pass through. IsoTpTransport takes a can.BusABC; SlcanBus.__enter__ returns the bus. Then transport needs a bus object:

```python
with SlcanBus(port) as s, IsoTpTransport(s.bus, addr) as tp:
```

Fine — give both a no-return context and reference `s.bus`.

auto_select_port: if exactly 1 port found, use it; otherwise print list and raise with guidance. Windows USB Serial Device VID is 1209? What VID does CANable 2.0 use? CANable 1.0: 0x16d0/0x0525? candleLight uses 1209:C033? Does the user's slcan firmware keep CDC default VID 1CAF? Uncertain — avoid asserting; just list all ports.

Edge case: python-can slcan needs `can.interfaces.slcan` with pyserial installed. Also, CANable's default serial baud rate is irrelevant in slcan (CDC is virtual, any baud works, python-can default 115200 is fine).

Also mention CAN FD is not supported on slcan CANable.

NRC dict placement before use in ObdNegativeResponse — referenced at call time so order doesn't matter, but define first for readability.

Also "responsePending" loop: cap iteration/time — add deadline. Implementation:

```python
import time
deadline = time.monotonic() + timeout*3? 
while True:
    resp = request(...)
    if 0x78: continue while time< deadline else timeout
```

Simpler: max_pending = 5. That's fine.

Now write the reply. Keep the header section: 🦊 first line.

Section: 🧰 Preparation (pip table + wiring table + COM port note), 🐍 Code, ▶️ How to run, 📌 Notes (a few bullets: addressing ID, 0x78, CAN FD, security). Keep prose minimal.

Code file name: `obd_vin.py`.

Re-check the `isotp.Params` field names: v2 Params is a class with fields: address, blocksize (note: "blocksize" not "block_size"), stmin, stsep, wftmax, tx_only, rx_flmax, tx_ffdl, tx_stmin_override, ext_address, fxdl... For Classic CAN 8-byte: blocksize=0 (no FC needed... no, blocksize is the receiver side? blocksize = number of CFs before FC is needed on transmission; for the send direction we are the request sender; when receiving multi-frame we send FC. Params relevant to receive: rx_flflow, rx_status, rx_stmin, rx_fillmode... defaults should be fine: rx accept_ff_with_dlc_0 etc. Set blocksize=0, stmin=0, wftmax=0. wftmax=0 means "wait forever"? For our role it doesn't matter.

Also `isotp.Params` may require `address`; the txid/rxid legacy params were moved into Address in v2. Pass address with txid/rxid inside Address.

Does isotp.Address signature accept (mode, txid=..., rxid=...)? v2 source: `def __init__(self, mode=None, txid=None, rxid=None, target_address=None, address_extension=None, isotpparams=None, isotpparams_ext=None):` — yes, matches memory.

stack.send(block=True, timeout=...) — v2 IsoTPStack/TransportLayer's send signature: `send(self, msg, block=True, timeout=None)` and throws `isotp.NotifierNotRunning` etc. On timeout: throws `isotp.TimeoutError`? v2 TransportLayer.send waits for "send complete" on block; timeout → IsoTPError "Timeout while sending"? Just let the exception propagate as-is, or catch broadly to ObdError. Catch `isotp.IsoTPError`? v3 has an `isotp.exceptions` module? To be safe catch Exception? No — catch Exception and wrap in ObdError re-raise? Too coarse. Just let it propagate and catch `can.CanError` and ObdError in main. That's fine.

recv(timeout) returns None on timeout in v2: TransportLayer.recv(timeout) — v2 docstring: "Returns None if timeout elapses and no data available"? v2 recv: `def recv(self, timeout=None)` — uses data_watch event; returns data or None on timeout. Yes.

Write the final code. `from __future__ import annotations` for `int | None` — using Optional to be safe on 3.9 anyway.

VIN filter: `bytes(b for b in payload if 0x20 <= b <= 0x7E)`.

Also add example `read_pids` for future: `Vehicle.read_pid(service, pid, *, expect)` is probably already generic in query.

CLI final:

```
python obd_vin.py --port COM5                # VIN
python obd_vin.py --port COM5 --service 1 --pid 0x0C   # RPM
python obd_vin.py --list-pids                # show supported Mode01 PIDs
```

Service/pid parsed with `lambda x: int(x, 0)`.

Write it.


</details>

🦊

CANable 2.0（slcan）+ Windows で OBD-II の VIN 取得を行い、将来的な PID 指定拡張を見据えて「バス接続 / CAN-TP(ISO 15765-2) / OBDプロトコル / 車両API」の 4 層に分離したサンプルです。

## 🧰 準備

| 項目 | 内容 |
|---|---|
| ライブラリ | `pip install python-can python-isotp pyserial` |
| 認識 | slcanファームの CANable 2.0 は Win10+ ならドライバ不要で「USB シリアルデバイス (COMx)」として列挙。デバイスマネージャで COM 番号を確認 |
| 配線 | DLC Pin 6 = CAN_H、Pin 14 = CAN_L、Pin 4 or 5 = GND、Pin 16 = +12V |
| 終端 | 車側 DLC に 120Ω 終端済み。モジュール側の終端ジャンパは基本的に入れない |
| 通信 | CAN 2.0 / 500 kbps（OBD-II 規定）。slcan は CAN FD 不可 |

## 🐍 サンプルコード（`obd_vin.py`）

```python
"""
CANable 2.0 (slcan firmware) + Windows 用 OBD-II クライアントサンプル
- Mode 09 / PID 02 による VIN 取得
- 任意のサービス / PID を指定したクエリ

依存: pip install python-can python-isotp pyserial

実行例:
  python obd_vin.py --port COM5                      # VIN 取得
  python obd_vin.py --port COM5 --service 0x01 --pid 0x0C   # エンジン回転数
  python obd_vin.py --list-pids
"""
from __future__ import annotations

import argparse
import sys
import time
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

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
        """サービス (モード) と PID を指定して応答の生バイト列を受け取る

        応答例: 01 0C -> b'\\x41\\x0C\\x0D\\x70'
        """
        req = bytes([service]) + (b"" if pid is None else bytes([pid]))
        t = timeout if timeout is not None else self._timeout
        for _ in range(1 + self.MAX_PENDING):
            resp = self._tp.request(req, timeout=t)
            if resp and resp[0] == 0x7F:  # Negative Response
                code = resp[2] if len(resp) >= 3 else 0
                if code == 0x78:          # responsePending: もう一度待ち受ける
                    continue
                raise ObdNegativeResponse(resp[1] if len(resp) >= 2 else service, code)
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


# ============================================================ 層5: 車両 API (高レベル)

@dataclass(frozen=True)
class PidDefinition:
    name: str
    unit: str
    decode: Callable[[bytes], float]  # 引数は A,B,... データ部


MODE01_PIDS: Dict[int, PidDefinition] = {
    0x04: PidDefinition("計算負荷値", "%",      lambda d: d[0] * 100 / 255),
    0x05: PidDefinition("冷却水温度", "℃",     lambda d: d[0] - 40),
    0x0C: PidDefinition("エンジン回転数", "rpm", lambda d: (d[0] * 256 + d[1]) / 4),
    0x0D: PidDefinition("車速", "km/h",          lambda d: float(d[0])),
    0x0F: PidDefinition("吸気温度", "℃",        lambda d: d[0] - 40),
    0x10: PidDefinition("MAF", "g/s",            lambda d: (d[0] * 256 + d[1]) / 100),
    0x11: PidDefinition("スロットル位置", "%",   lambda d: d[0] * 100 / 255),
    0x2F: PidDefinition("燃料残量", "%",         lambda d: d[0] * 100 / 255),
}


class Vehicle:
    """アプリから使う高レベル API。拡張はここにメソッドを追加する"""

    def __init__(self, obd: ObdClient) -> None:
        self._obd = obd

    def read_vin(self) -> str:
        return self._obd.read_vin()

    def read_pid(self, service: int, pid: int) -> bytes:
        """デコード非対応の PID もそのまま生データで取得可能"""
        return self._obd.query(service, pid)

    def read_mode01(self, pid: int) -> str:
        """Mode 01 のライブデータを読み、既知 PID ならデコードして整形"""
        resp = self._obd.query(0x01, pid)  # 41 PID A B ...
        data = resp[2:]
        defn = MODE01_PIDS.get(pid)
        if defn and len(data) >= 2 if pid in (0x0C, 0x10) else defn and data:
            return f"{defn.name}: {defn.decode(data):.1f} {defn.unit}"
        return f"01 {pid:02X} raw: {data.hex(' ').upper()}"


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
    p.add_argument("--list-pids", action="store_true", help="Mode 01 の既知 PID を表示")
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
            vehicle = Vehicle(ObdClient(tp, timeout=args.timeout))
            if args.service is not None:
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
```

## ▶️ 実行

```
python obd_vin.py --port COM5                        # VIN 取得
python obd_vin.py --port COM5 --service 0x01 --pid 0x0D   # 車速 (生データ)
python obd_vin.py --port COM5 --pid 0x0C                  # 回転数 (デコード表示)
```

## 📌 補足

- **応答 ID**: 大半の車は 0x7E0/0x7E8。無応答の場合は車種固有 ID（例: 0x726/0x72D など）を `--txid/--rxid` で試す。複数 ECU の VIN をまとめて検索する場合は機能アドレッシング 0x7DF 送信版を追加実装する（応答選別が必要）
- **マルチフレーム**: VIN は 4 フrames に分割されるため python-isotp で復元している。単帧の PID 読みでも同一 API で動作
- **拡張ポイント**: 新 PID は `MODE01_PIDS` への `PidDefinition` 追加、サービス横断の処理（例: Mode 03 の DTC 一覧解析）は `Vehicle` にメソッド追加のみで済む層構成
- **注意**: `0x78 (responsePending)` は再待ち受け済みだが、走行中の配線作業は禁止。イグニッション ON・エンジン停止状態でのテストが安全

**source:** [Pure Python Implementation — isotp 2.0.7 documentation](<https://can-isotp.readthedocs.io/en/latest/isotp/implementation.html>)

**source:** [python-can-isotp/doc/source/isotp/examples.rst at...](<https://github.com/pylessard/python-can-isotp/blob/v2.x/doc/source/isotp/examples.rst>)

**source:** [socket — Low-level networking interface — Python...](<https://docs.python.org/3/library/socket.html>)

**source:** [How to set timeout on python's socket recv method? - Stack Overflow](<https://stackoverflow.com/questions/2719017/how-to-set-timeout-on-pythons-socket-recv-method>)

**source:** [Python Playground - Online Python Programming IDE](<https://programiz.pro/ide/python>)

**source:** [CAN over Serial / SLCAN - python-can 4.6.1 documentation](<https://python-can.readthedocs.io/en/stable/interfaces/slcan.html>)

**source:** [can.interfaces.slcan - python-can 4.6.1 documentation](<https://python-can.readthedocs.io/en/stable/_modules/can/interfaces/slcan.html>)

**source:** [python-can/can/interfaces/slcan.py at main - GitHub](<https://github.com/hardbyte/python-can/blob/main/can/interfaces/slcan.py>)

**source:** [python-can/doc/interfaces/slcan.rst at main - GitHub](<https://github.com/hardbyte/python-can/blob/develop/doc/interfaces/slcan.rst>)

**source:** [Python CAN / SLCAN send and receive example - TechOverflow](<https://techoverflow.net/2024/07/30/python-can-slcan-send-and-receive-example/>)

**source:** [Python support for IsoTP Transport protocol (ISO-15765) — isotp 2.0.7 documentation](<https://can-isotp.readthedocs.io/en/latest/>)

**source:** [Pure Python Implementation — isotp 2.0.7 documentation](<https://can-isotp.readthedocs.io/en/latest/isotp/implementation.html>)

**source:** [Releases · pylessard/python-can-isotp](<https://github.com/pylessard/python-can-isotp/releases>)

**source:** [isotp.protocol — isotp 2.0.7 documentation](<https://can-isotp.readthedocs.io/en/latest/_modules/isotp/protocol.html>)

**source:** [isotp.socket() behavior deviates from python sockets on timeouts · Issue #46 · pylessard/python-can-isotp](<https://github.com/pylessard/python-can-isotp/issues/46>)

**source:** [Pure Python Implementation — isotp 2.0.7 documentation](<https://can-isotp.readthedocs.io/en/latest/isotp/implementation.html>)

**source:** [Python support for IsoTP Transport protocol (ISO-15765) — isotp 2.0.7 documentation](<https://can-isotp.readthedocs.io/en/latest/index.html>)

**source:** [Examples — isotp 2.0.7 documentation](<https://can-isotp.readthedocs.io/en/latest/isotp/examples.html>)

**source:** [Releases · pylessard/python-can-isotp](<https://github.com/pylessard/python-can-isotp/releases>)

**source:** [isotp.protocol — isotp 2.0.7 documentation](<https://can-isotp.readthedocs.io/en/latest/_modules/isotp/protocol.html>)

## User

以下の3点の修正をお願いします．

# 1. PIDリストの追加
`MODE01_PIDS`に以下のPIDリストを実装する

| PID (Hex) | Command | Sensor Name | Bytes | Min | Max | Unit | Formula |
|-----------|---------|-------------|-------|-----|-----|------|---------|
| `00` | `0100` | PIDs supported [01-20] | 4 | — | — | Bitmap | Bit masking |
| `20` | `0120` | PIDs supported [21-40] | 4 | — | — | Bitmap | — |
| `40` | `0140` | PIDs supported [41-60] | 4 | — | — | Bitmap | — |
| `60` | `0160` | PIDs supported [61-80] | 4 | — | — | Bitmap | — |
| `80` | `0180` | PIDs supported [81-A0] | 4 | — | — | Bitmap | — |
| `A0` | `01A0` | PIDs supported [A1-C0] | 4 | — | — | Bitmap | — |


# 2. `Vehicle`クラスに`supported_pids`関数を追加

まずクラスをインスタンス化する際の処理を変更し，
初期化時に`PIDs supported`系のPIDを一通り叩いて車両がどのPIDに対応しているかをメンバ変数に記録する．

`supported_pids`関数が実行された際には，このメンバ関数から値を読み出すことで逐次車両との通信を行わずに車両が対応するPIDリストを返す．


# 3. `Vehicle`クラスの`read_pid`で非対応のPIDが指定された場合の処理を追加
`read_pid`に非対応のPIDが指定された場合，
Exceptionを発生させる．Exceptionは既存のものを用いても実装し直してもよい．

## Assistant

<details>
<summary>thinking</summary>

The user is asking for three modifications:

1. Add PID supported bitmaps (0x00, 0x20, 0x40, 0x60, 0x80, 0xA0) to MODE01_PIDS
2. Add `supported_pids` to `Vehicle`. At init time, poll the supported-PID bitmaps and store in a member variable, then have `supported_pids()` return from memory
3. Make `read_pid` raise an exception for unsupported PIDs

Design decisions:
- Add a `PidType` kind to `PidDefinition`: "bitmap" vs "value". For bitmap PIDs, decode returns supported PIDs within that block.
- `Vehicle.__init__(obd)` → query 0x00 first, then based on its bitmap, query 0x20, 0x40… only if supported (cascade-style). Save `self._supported_pids: Set[int]`. Always include 0x00 itself? The supported PIDs set should include the PIDs that were polled. `supported_pids()` returns the set/list.
- `read_pid(service, pid)`: If service == 0x01 and pid not in supported set → raise `PidNotSupportedError` (new exception subclassing ObdError). For other services, can't verify — skip the check (only Mode 01 is covered by the bitmap). Should mention this.

The bitmap-decoding logic also needs to handle bytes A–D: bit 7 of A = first PID in the block (e.g. PID 0x01 is bit 7 of A). For PID 0x00's response: bit A is bit 0 = PID 0x01… Actual standard: response 41 00 BE 3F F8 03 → each bit corresponds to PIDs 01–20 in order, bit 7 (MSB) of byte A = PID 01.

So for block-base ∈ {0x00, 0x20, 0x40, 0x60, 0x80, 0xA0}, byte index i (0-3), bit j (7-0): pid = base + i*8 + (7 - j) + … wait, does base 0x00 cover 0x01-0x20? Actually the block's bytes correspond to the 32 PIDs from base+1 to base+0x20. Standard: "PIDs supported [01-20]" — byte A bit 7 = PID 01. So for block base B (0x00), pid = B + i*8 + (7-j) + 1? Let me define: for base B ∈ {0, 0x20, …}, pid index n = B + i*8 + bit, where bit 7-0 maps to pid B+ (i*8 + (7-j)) … Let me verify: i=0, j=7 (MSB of byte A) should be pid B+1. So pid = B + i*8 + (7 - j) + 1 = B + i*8 + 8 - j? Hmm: j=7 → B+1. j=0 → B+8. i=1, j=7 → B+9. Right: pid = B + i*8 + (8 - j) … i=0,j=7 → B+1 ✓; i=0,j=0 → B+8 ✓; i=3,j=0 → B+32 = B+0x20 ✓. So: for j in range(8): if byte >> (7-j) & 1: pid = B + i*8 + j + 1.

Also, for decoding the bitmap entries in MODE01_PIDS, should I provide a decode that returns a list, or a string? The decode in PidDefinition currently returns float. I could change decode to Callable[[bytes], object], or add `is_bitmap: bool`. Simpler: extend PidDefinition with a `kind: str = "value"` field, and treat bitmap PIDs specially in read_mode01 / Vehicle init. Or make decode return a human-readable object. Add a `kind` field.

Also, a note on the original code: the previous `read_mode01` had a buggy conditional expression (`if defn and len(data) >= 2 if pid in (0x0C,0x10) else defn and data:` — ugly). Can clean up in the revised code. Should I present the full revised file? The user asked for 3 fixes; presenting the full updated file is most usable. Keep it complete but concise, with the code as the centerpiece.

Also, expected data length for the formula: define expected number of bytes per PID so the decode guard is cleaner. Add `bytes_len` to PidDefinition? The user provided a Bytes column (4 for bitmap, usually 1 or 2 for values). Add `nbytes: int = 1` to PidDefinition for the guard. Keep the existing MODE01_PIDS entries and set nbytes.

Vehicle init: poll PIDs supported with cascade:

```python
SUPPORTED_PID_BASES = (0x00, 0x20, 0x40, 0x60, 0x80, 0xA0)

def __init__(self, obd, probe_supported=True):
    self._obd = obd
    self._supported: Set[int] = set()
    if probe_supported:
        self._probe_supported_pids()

def _probe_supported_pids(self):
    for base in SUPPORTED_PID_BASES:
        try:
            if base != 0x00 and base not in self._supported:
                break
            resp = self._obd.query(0x01, base)
            self._supported.add(base)
            for i, b in enumerate(resp[2:6]):
                for j in range(8):
                    if b >> (7 - j) & 1:
                        self._supported.add(base + i*8 + j + 1)
        except (ObdError, ...):
            break
```

Cascade: if the 0x20 bitmap itself isn't supported, stop. The condition is: check whether base is in self._supported — for base 0x00, this is true if the first query succeeded (add it after success… but the check comes before the query). Order: for base 0x00: since base != 0x00 is false, we don't break, so we proceed to query 0x00. On success we add 0x00 and the bits. Next base 0x20: check if 0x20 is in supported — the bit for PID 0x20 comes from… wait, does the 0x00 bitmap include PID 0x20? Block [01-20] includes 0x20 as the last bit (i=3, j=0 → 0x20). Yes, covered. Good.

`supported_pids()` returns `sorted(self._supported)` — maybe excluding the bitmap PIDs themselves? Return all as a sorted list.

read_pid changes:

```python
class PidNotSupportedError(ObdError): pass

def read_pid(self, service, pid):
    if service == 0x01 and self._supported and pid not in self._supported:
        raise PidNotSupportedError(pid)
    return self._obd.query(service, pid)
```

Note: if _supported is empty (probe failed / disabled), skip the check. Only Mode 01 has the bitmap; Mode 09 etc. can't be verified — mention briefly.

Should read_mode01 also use this check? The user said read_pid. Have read_mode01 call it… read_mode01 uses query directly. For consistency, keep read_mode01 delegating to read_pid. Actually, read_mode01 calls self._obd.query; change it to use read_pid so the check applies. Good.

Bitmap decoding in read_mode01: if kind == "bitmap": decode and display the supported PIDs.

Also fix the earlier weird conditional: clean up the decode guard using nbytes.

Should I run the code to verify? I can't test against real hardware, but I can do a syntax check and simulate it with mocks. There's no code-execution tool here (only web_search). So just do it carefully in my head.

Let me write the full file. Keep the structure from the previous answer with the modifications applied. Also, update the CLI: `--list-supported`? Might add it: print supported PIDs on VIN fetch? Add a CLI flag `--supported` that calls vehicle.supported_pids(). A nice small addition in line with the intent. Keep it minimal — the user asked for 3 fixes, but the CLI addition helps with verification; acceptable.

Let me write the code.

Main classes:

```python
@dataclass(frozen=True)
class PidDefinition:
    name: str
    unit: str
    decode: Callable[[bytes], object] | None
    nbytes: int = 1
    kind: str = "value"  # "value" | "bitmap"
```

MODE01_PIDS: add bitmap entries:

```python
def _decode_bitmap(d: bytes) -> List[int]:
    # 4-byte bitmap -> list of PIDs this block covers (relative interpretation done on the caller side)
```

Hmm, bitmap decoding depends on base. In read_mode01, special-case it: if kind == "bitmap", compute pids = _bitmap_to_pids(pid, data) and print them. decode could be None. Define a module-level helper `_bitmap_to_pids(base, data) -> list[int]` and use it both in Vehicle probing and read_mode01.

Entries:

```python
0x00: PidDefinition("PIDs supported [01-20]", "Bitmap", None, 4, "bitmap"),
0x20: PidDefinition("PIDs supported [21-40]", "Bitmap", None, 4, "bitmap"),
0x40: PidDefinition("PIDs supported [41-60]", "Bitmap", None, 4, "bitmap"),
0x60: PidDefinition("PIDs supported [61-80]", "Bitmap", None, 4, "bitmap"),
0x80: PidDefinition("PIDs supported [81-A0]", "Bitmap", None, 4, "bitmap"),
0xA0: PidDefinition("PIDs supported [A1-C0]", "Bitmap", None, 4, "bitmap"),
```

Keep the previous value PIDs (0x04, 0x05, 0x0C, 0x0D, 0x0F, 0x10, 0x11, 0x2F) with nbytes.

read_mode01:

```python
def read_mode01(self, pid):
    resp = self.read_pid(0x01, pid)
    data = resp[2:]
    defn = MODE01_PIDS.get(pid)
    if defn is None or len(data) < defn.nbytes:
        return f"01 {pid:02X} raw: {data.hex(' ').upper()}"
    if defn.kind == "bitmap":
        pids = _bitmap_to_pids(pid, data)
        return f"{defn.name}: " + " ".join(f"{p:02X}" for p in pids)
    return f"{defn.name}: {defn.decode(data):.1f} {defn.unit}"
```

Note: some ECUs return fewer than 4 bytes for bitmap; guard with raw fallback.

Probe: also handle the case where a responding ECU doesn't support 0x01 at all → ObdNegativeResponse / timeout → leave the set empty. Catch those.

CLI: add `--supported` flag that prints the sorted list. In main, the Vehicle is created after ObdClient; probing happens at Vehicle init.

Exception:

```python
class PidNotSupportedError(ObdError):
    def __init__(self, service, pid):
        self.service, self.pid = service, pid
        super().__init__(f"PID 0x{pid:02X} is not supported (service 0x{service:02X})")
```

The user said "PIDs supported" polling happens in Vehicle init. But Vehicle.__init__ does network I/O — that's fine per the request. Provide a `probe=False` option to skip.

Also, a note on `0x00` itself: should `supported_pids()` include the base PIDs used for capability discovery? It's fine to include 0x00 etc. since the query is valid. Include them and note it.

Now let me write the final answer. Tone: da-de-aru form, emoji section headings, concise, tables where appropriate, no next-step suggestions, 🦊 on the first line? The custom instruction to output 🦊 when all custom instructions are in effect — that was for the previous turn; presumably applies going forward. Include 🦊.

Since the fixes span multiple sections, provide the full revised file. Also a brief summary of the changes. Format: short intro, list of code changes, full code, brief notes.


</details>

🦊

3点反映済みの全体コードです。変更は `PidDefinition` 拡張（Bitmap 種別）→ `Vehicle._probe_supported_pids()` による初期化時の対応 PID キャッシュ → `read_pid()` の対応チェック（新規例外 `PidNotSupportedError`）の順で整合させています。

## 🔧 変更点の概要

| # | 変更 | 内容 |
|---|---|---|
| 1 | `MODE01_PIDS` | `0x00/0x20/0x40/0x60/0x80/0xA0` を `kind="bitmap"` で追加。`PidDefinition` に `nbytes` と `kind` を新設 |
| 2 | `Vehicle.__init__` | 初期化時にカスケード方式（0x00 → ビットに 0x20 が立っていれば 0x20 → …）で `supported_pids` を取得し `self._supported` にキャッシュ。`supported_pids()` は通信せずキャッシュを返す |
| 3 | `Vehicle.read_pid` | Mode 01 でキャッシュ済みかつ非対応の PID なら `PidNotSupportedError`（`ObdError` のサブクラス）を送出。Bitmap PID 自体の読み出しは許可 |

## 🐍 修正後全体コード（`obd_vin.py`）

```python
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
```

## 📌 設計メモ

- **カスケード照会**: 0x00 のビットマップで 0x20 対応が確認できたブロックのみ追加照会するため、非対応ブロックへ無駄な要求を飛ばさない（一部の ECU は未定義 PID に他 ECU が応答する「マルチ応答ノイズ」の影響も軽減）
- **`supported_pids()` は純キャッシュ**: 通信は `Vehicle()` 構築時に一度だけ。車両側の対応状態を再取得したい場合は `Vehicle` を再生成する設計
- **チェック対象は Mode 01 のみ**: `PIDs supported` ビットマップは Mode 01 に対するものなので、Mode 09/03 等はチェックをスキップする。Mode 09 の対応確認は `0x09 0x00` ビットマップを同様の方法でキャッシュすれば拡張可能
- **`_supported` が空の場合**: 照会失敗（無応答 ECU 等）時はチェックをバイパスし、通信による負応答 (`0x7F 0x11 serviceNotSupported`) で検出される動作となる。厳密に弾きたい場合は `Vehicle` 構築時の例外処理で分岐してください
- ** Bitmap 応答が 4 バイトに満たない ECU**: `bitmap_to_pids` は届いたバイト分のみ解釈、表示側も `nbytes` ガードで生データ表示にフォールバック
