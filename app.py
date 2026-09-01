from flask import Flask
from flask_socketio import SocketIO
import json
import gps

app = Flask(__name__)
sock = SocketIO(app)

# 静的ファイルのルートを設定
app.static_folder = 'static'

# WebSocketメッセージのルーティング
@sock.on("message")
def handle_message(_msg):
    '''
    WebSocketのメッセージ処理用ルーター

    Parameters
    ----------
        _msg (str): 受信したメッセージ
    '''
    print("socket_rcv:", _msg)

    # メッセージタイプごとに分岐
    msg = json.loads(_msg)
    res = None
    if msg["type"] == "CLIENT HELLO":
        res = gps.ws_client_hello(msg)
    if msg["type"] == "GPS UPDATE":
        res = gps.ws_gps_update(msg)

    if res != None:
        sock.send(res)


if __name__ == '__main__':
    print(app.url_map)
    app.run(debug=True)
