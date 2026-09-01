/**
 * ログ表示
 * 文字列を受け取り，時刻(yyyy-MM-dd hh:mm:ss)やログレベルを付与して整形してログ表示する
 * また，同時にコンソールにも出力する，
 * @param {string} text - ログに表示する文字列
 * @param {string} level - ログレベル（"info", "warn", "error"）を指定する
**/
function log(level,text) {
  const log = document.getElementById("log");
  const now = new Date();
  const timestamp = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')} ${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}:${String(now.getSeconds()).padStart(2, '0')}`;
  let prefix = "";
  switch (level) {
    case "info":
      prefix = "[INFO]";
      break;
    case "warn":
      prefix = "[WARN]";
      break;
    case "error":
      prefix = "[ERROR]";
      break;
    default:
      prefix = "[INFO]";
  }
  log.textContent += `${timestamp} ${prefix} ${text}\n`;
  console.log(`${timestamp} ${prefix} ${text}`);
}


/**
 * 初期化成功ハンドラ
 * 初期化に成功した際の処理を記述する．
 * @param {GeolocationPosition} obj - 初期化成功時のオブジェクト
**/
function initSuccess(obj) {
  log("info","GPS初期化成功\t緯度:" + Math.trunc(obj.coords.latitude * 10000) / 10000 + " 経度:" + Math.trunc(obj.coords.longitude * 10000) / 10000 + " 精度:" + obj.coords.accuracy);
  map.panTo([obj.coords.latitude,obj.coords.longitude], { animate: true, duration: 2 });
}


/**
 * 初期化失敗ハンドラ
 * 初期化に失敗した際の処理を記述する
 * @param {GeolocationPositionError} obj - 初期化失敗時のオブジェクト
**/
function initError(obj) {
  log("error",`GPS初期化失敗\t${obj.message}`);
  alert("GPSの利用が許可されませんでした．\nページを更新して再度権限の許可を行ってください．");
}


/**
 * 位置情報更新ハンドラ
 * 位置情報が更新された際の処理を記述する
 * @param {GeolocationPosition} obj - 位置情報更新時のオブジェクト
**/
function updateSuccess(obj) {
  // ログ出力
  log("info", "GPS更新\t緯度:" + Math.trunc(obj.coords.latitude * 10000) / 10000 + " 経度:" + Math.trunc(obj.coords.longitude * 10000) / 10000 + " 精度:" + obj.coords.accuracy);

  // 地図の中心地を現在地に更新
  map.panTo([obj.coords.latitude, obj.coords.longitude], { animate: true, duration: 2 });
  map.removeLayer(marker);
  map.removeLayer(circle);
  marker =  L.marker([obj.coords.latitude, obj.coords.longitude]).addTo(map);
  circle = L.circle([obj.coords.latitude, obj.coords.longitude], obj.coords.accuracy).addTo(map);

  // バックエンドに位置情報を送信
  sock.send(JSON.stringify({
    "type": "GPS UPDATE",
    "latitude": obj.coords.latitude,
    "longitude": obj.coords.longitude,
    "accuracy": obj.coords.accuracy
  }));
}

/**
 * Websocketを開く
 * ブラウザから取得したGPS座標をバックエンドに報告するために
 * SocketIOを利用してWebSocketを開きバックエンドとの通信状況を確認する．
 **/
const sock = io();
try {
  sock.send('{"type": "CLIENT HELLO"}');
  sock.on("message", function (data) {
    if (data == '{"type": "SERVER HELLO"}') {
      log("info", "WebSocket接続成功");
    } else {
      log("error","WebSocket接続失敗");
      alert("WebSocket接続に失敗しました．\nページを更新して再度接続を試みてください．");
    }
  });
} catch{
  log("error","WebSocket接続失敗");
  alert("WebSocket接続に失敗しました．\nページを更新して再度接続を試みてください．");
}

// socketが閉じた際には数秒待機してページをリロードする
sock.on("disconnect", function () {
  log("error","WebSocket切断");
  setTimeout(function() {
    location.reload();
  }, 5000);
});


/** マップ描写 **/
// leaflet.jsのマップを初期化
const map = L.map('map', {
  zoomControl: false,
  zoomAnimation: true,
  zoomAnimationThreshold: 4,
  fadeAnimation: true,
  easeLinearity: 0.5
})
.setView([35.684263, 139.748433], 14);
// タイルレイヤー（地図画像）を追加
L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '<a href="https://www.openstreetmap.org/copyright">© OpenStreetMap</a>'
}).addTo(map);
var marker = L.marker([35.684263, 139.748433]).addTo(map);
var circle = L.circle([35.684263, 139.748433], 100).addTo(map);


/** 初期化処理 **/
navigator.geolocation.getCurrentPosition(initSuccess, initError);

/** 座標移動時処理 **/
navigator.geolocation.watchPosition(updateSuccess);
