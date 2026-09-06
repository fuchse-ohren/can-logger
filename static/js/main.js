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
  const can_data = data.message
  const eg_load = can_data[4] ?? 0;
  const water_temp = can_data[5] ?? 0;
  const eg_rpm = can_data[12] ?? 0;
  const speed = can_data[13] ?? 0;
  const air_temp = can_data[15] ?? 0;
  const air_flow = can_data[16] ?? 0;
  const sys_load = can_data[67] ?? 0;
  const lambda = can_data[68] ?? 0;
  const throttle = can_data[73] ?? 0;
  const throttle_acc = can_data[76] ?? 0;

  document.getElementById("x04").textContent = eg_load;
  meter_04.setValue(eg_load);
  document.getElementById("x05").textContent = water_temp;
  meter_05.setValue(water_temp);
  document.getElementById("x0C").textContent = eg_rpm;
  meter_0C.setValue(eg_rpm);
  document.getElementById("x0D").textContent = speed;
  meter_0D.setValue(speed);
  document.getElementById("x0F").textContent = air_temp;
  meter_0F.setValue(air_temp);
  document.getElementById("x10").textContent = air_flow;
  meter_10.setValue(air_flow);
  document.getElementById("x43").textContent = sys_load;
  meter_43.setValue(sys_load);
  document.getElementById("x44").textContent = lambda;
  meter_44.setValue(lambda);
  document.getElementById("x49").textContent = throttle;
  meter_49.setValue(throttle);
  document.getElementById("x4C").textContent = throttle_acc;
  meter_4C.setValue(throttle_acc);

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
  function(){ sock.send('{"type":"CAN_DATA"}') }, 200
);


// socketが閉じた際には数秒待機してページをリロードする
sock.on("disconnect", function () {
  console.log("error","WebSocket切断");
  setTimeout(function() {
    location.reload();
  }, 5000);
});
