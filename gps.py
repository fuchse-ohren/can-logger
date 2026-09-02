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
    return '{"type": "SERVER_HELLO"}'


def ws_gps_update(logger,msg):
    '''
    WebSocketのGPS UPDATEメッセージ処理

    Parameters
    ----------
        logger (CanLogger): CanLoggerのインスタンス
        msg (dict): 受信したメッセージ

    Returns
    -------
        str: クライアントへの返信メッセージ
    '''
    print("GPS:", msg)
    logger.lat = msg["latitude"]
    logger.long = msg["longitude"]
    logger.acc = msg["accuracy"]
    return '{"type": "GPS_UPDATE","status": "ok","message": "ok"}'


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
        if msg["type"] == "CLIENT_HELLO":
            ws_client_hello(msg)
        if msg["type"] == "GPS_UPDATE":
            ws_gps_update(msg)

    app.run(debug=True)
