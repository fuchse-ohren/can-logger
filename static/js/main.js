/**
 * HELLOメッセージハンドラ
 * WebSocketからメッセージを受信した際の処理を記述する
 * @param {Object} data - 受信したメッセージ
**/
function wsHelloHandler(data) {
  wsConnected = true;
  console.log("info", "WebSocket接続成功");
}


/**
 * CANデータハンドラ
 * Websocketから受信したCANデータを処理する
 **/
function wsCANHandler(data) {
  console.log("info", "CANデータ受信")
  console.log(data)
}


/**
 * Websocketを開く
 * ブラウザから取得したGPS座標をバックエンドに報告するために
 * SocketIOを利用してWebSocketを開きバックエンドとの通信状況を確認する．
 **/
const sock = io();
var wsConnected = false;
try {
  sock.send('{"type": "CLIENT_HELLO"}');
  sock.on("message", function (_data) {
    const data = JSON.parse(_data);

    // 各メッセージハンドラに振り分ける
    switch (data.type) {
      case "SERVER_HELLO":
        wsHelloHandler(data);
        break;
      case "GPS_UPDATE":
        break;
      case "CAN_DATA":
        wsCANHandler(data)
        break;
      default:
        console.log("warn", "不明なWebSocketメッセージを受信しました．\n" + _data);
    }
  });
} catch{
  console.log("error","WebSocket接続失敗");
  alert("WebSocket接続に失敗しました．\nページを更新して再度接続を試みてください．");
}

// CAN情報を要求する
setInterval(
  function(){ sock.send('{"type":"CAN_DATA"}') }, 1000
);


// socketが閉じた際には数秒待機してページをリロードする
sock.on("disconnect", function () {
  console.log("error","WebSocket切断");
  setTimeout(function() {
    location.reload();
  }, 5000);
});
