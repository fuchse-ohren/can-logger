import threading,time,datetime,logging

import obd

# ============================================================
#  ログ設定
# ============================================================
LOG_FORMAT = "%(asctime)s,%(msecs)03d [%(levelname)s] %(name)s - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    datefmt=DATE_FORMAT
)
lprint = logging.getLogger(__name__)


class Logger:

    def __init__(self,**kwargs):
        '''
        canloggerクラスを初期化する

        Parameters
        ----------
          - output_path = (str) - 出力先のパス
          - port = (str): CANバスのCOMポート
          - bitrate = (int): CANバスのビットレート

        '''

        # GPS座標を入れておく変数を作る
        self.lat =  123.01234567890123
        self.long = 123.01234567890123
        self.acc = 0

        # スリープ用
        self.lastIteration = 0

        # CANを初期化
        self.can_transport = obd.CanTransport(
            obd.CanConfig(
                port = kwargs.get("port", "COM4"),
                bitrate = kwargs.get("bitrate", 500000)
            )
        )

        # ISOTPを初期化
        iso_tp = obd.IsoTpTransport(
            self.can_transport,
            obd.IsoTpConfig(
                tx_id=0x7DF,
                rx_id=0x7E8,
            )
        )

        # OBD-IIを初期化
        self.obd = obd.ObdClient(iso_tp)

        # CANをオープン
        try:
            self.can_transport.open()
            iso_tp.open()
        except:
            self.can_transport.close()
            raise Exception("ポート初期化に失敗")

        # CSVの保存に関する設定
        self.output_path = kwargs.get("output_path", "./can.log")
        try:
            open(self.output_path,"a").close()
        except:
            self.output_path = "./can.log"

        self.can_data = {}

        # ワーカースレッドを準備
        self.event = threading.Event()
        self.logworker = threading.Thread(target=self.logworker)


    def __del__(self):
        """
        プログラム終了時(インスタンス削除時)にCOMポートとワーカーを終了する
        """
        self.can_transport.close()
        self.event.set()
        time.sleep(1)


    def run(self):
        """
        ワーカースレッドを起動する
        """
        self.logworker.start()
        lprint.info("Log Worker Start")

    def isleep(self, wait: float):
        """
        処理時間を差し引いて一定時間待機する．
        繰り返し処理の際に用いる inverval sleep．

        Parameters
        ----------
         - time (float) - 待機時間(秒)
        """
        now = round(time.time() * 1000) / 1000

        # 現在時刻が前回の実行+waitより大きい場合
        # 遅延が発生していると見なしてwaitは行わない
        if now >= self.lastIteration + wait:
            lprint.info("処理遅延を検出しました")
        else:
            # 待機が必要な場合
            # lastIteration + wait時間まで待つ必要があるため，
            # (lastIteration + wait) - now = 待機時間となる
            #time.sleep((self.lastIteration + wait) - now)
            lprint.debug(f"sleep {(self.lastIteration + wait) - now}sec")
            time.sleep((self.lastIteration + wait) - now)

        self.lastIteration = round(time.time() * 1000) / 1000


    def logworker(self):
        """
        ワーカーを別スレッドとして起動し、CANデータと位置情報をCSVに記録する.
        """

        while self.event.is_set() == False:
            self.isleep(0.1)

            # 現在時刻
            now = datetime.datetime.now().isoformat()

            # OBDの値を取得
            can_outtext = "";
            for pid in self.obd.supported_pids:
                try:
                    res_bin = self.obd.request(0x01,pid)
                    res = self.obd.decoder(pid, res_bin)
                    self.can_data[pid] = res
                    can_outtext += res + ","
                except Exception as e:
                    can_outtext += ","
                    self.can_data[pid] = 0.0
                    lprint.error(e)


            # ファイルに書き込み
            with open(self.output_path,"a") as fp:
                buff = now + "," \
                + str(self.lat) + "," \
                + str(self.long) + "," \
                + str(self.acc) + "," \
                + can_outtext +  "\n"
                fp.write(buff)



#if __name__ == '__main__':
#    """
#    デバッグ用にコマンドから実行された場合のみ自力でワーカーを動かす
#    """
#    cl = Logger()
#    cl.run()
#    time.sleep(10)
#    cl.event.set()
