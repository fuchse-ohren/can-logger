import argparse
import json
import logging
from datetime import datetime

from flask import Flask, redirect
from flask_socketio import SocketIO

import gps
import log

# ============================================================
#  ログ設定
# ============================================================
LOG_FORMAT = "%(asctime)s,%(msecs)03d [%(levelname)s] %(name)s - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT, datefmt=DATE_FORMAT)
lprint = logging.getLogger(__name__)


app = Flask(__name__)
sock = SocketIO(app)

# 静的ファイルのルートを設定
app.static_folder = "static"


def ws_can_data_request(msg):
    """
    WebSocketでCANデータの取得を要求された際のハンドラ
    """
    return json.dumps({"type": "CAN_DATA", "message": cl.can_data})


# WebSocketメッセージのルーティング
@sock.on("message")
def handle_message(_msg):
    """
    WebSocketのメッセージ処理用ルーター

    Parameters
    ----------
        _msg (str): 受信したメッセージ
    """
    lprint.debug("socket_rcv:", _msg)

    # メッセージタイプごとに分岐
    msg = json.loads(_msg)
    res = None
    if msg["type"] == "CLIENT_HELLO":
        res = gps.ws_client_hello(msg)
    if msg["type"] == "GPS_UPDATE":
        res = gps.ws_gps_update(cl, msg)
    if msg["type"] == "CAN_DATA":
        res = ws_can_data_request(msg)

    if res != None:
        lprint.debug("socket_send:", res)
        sock.send(res)


@app.errorhandler(404)
def not_found(error):
    """
    404発生時に`/static/index.html`に飛ばす
    """
    return redirect("/static/index.html")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--output-path",
        default=f"./log/can_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
        help="ログ出力先",
    )
    parser.add_argument("--port", default="COM6", help="CANデバイスのCOMポート")
    parser.add_argument("--bitrate", type=int, default=500000, help="CANビットレート")

    args = parser.parse_args()

    cl = log.Logger(output_path=args.output_path, port=args.port, bitrate=args.bitrate)

    cl.run()
    app.run()
    # Flaskのプロセスが死んだらclを消す
    del cl
