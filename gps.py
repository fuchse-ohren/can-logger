if __name__ == '__main__':
    """
    デバッグ用にコマンドから実行された場合のみ自力でサーバを立ち上げる
    """
    from flask import Flask
    from flask_socketio import SocketIO
    import json

    app = Flask(__name__)
    sock = SocketIO(app)

    # 静的ファイルのルートを設定
    app.static_folder = 'static'


def ws_client_hello(msg):
    '''
    WebSocketのCLIENT HELLOメッセージ処理

    Parameters
    ----------
        msg (dict): 受信したメッセージ
    Returns
    -------
        str: クライアントへの返信メッセージ
    '''
    return '{"type": "SERVER HELLO"}'


def ws_gps_update(msg):
    '''
    WebSocketのGPS UPDATEメッセージ処理

    Parameters
    ----------
        msg (dict): 受信したメッセージ

    Returns
    -------
        str: クライアントへの返信メッセージ
    '''
    print("GPS:", msg)
    return None


if __name__ == '__main__':
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
        if msg["type"] == "CLIENT HELLO":
            ws_client_hello(msg)
        if msg["type"] == "GPS UPDATE":
            ws_gps_update(msg)

    app.run(debug=True)
