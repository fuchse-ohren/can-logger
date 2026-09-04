import threading,time
import datetime

class Logger:

    def __init__(self,**kwargs):
        '''
        canloggerクラスを初期化する

        Parameters
        ----------
            output_path= (str): 出力先のパス

        '''

        # GPS座標を入れておく変数を作る
        self.lat =  123.01234567890123
        self.long = 123.01234567890123
        self.acc = 0

        # CSVの保存に関する設定
        try:
            open(kwargs.output_path,"a").close()
        except:
            self.output_path = "./can.log"
        else:
            self.output_path = kwargs.output_path

        # ワーカースレッドを準備
        self.event = threading.Event()
        self.logworker = threading.Thread(target=self.logworker)


    def run(self):
        """
        ワーカースレッドを起動する
        """
        self.logworker.start()
        print("Log Worker Start")


    def logworker(self):
        """
        ワーカーを別スレッドとして起動し、CANデータと位置情報をCSVに記録する.
        """

        while self.event.is_set() == False:
            time.sleep(1)
            # 現在時刻
            now = datetime.datetime.now().isoformat()

            # ファイルに書き込み
            with open(self.output_path,"a") as fp:
                buff = now + ", " \
                + str(self.lat) + ", " \
                + str(self.long) + ", " \
                + str(self.acc) + "\n"
                fp.write(buff)



if __name__ == '__main__':
    """
    デバッグ用にコマンドから実行された場合のみ自力でワーカーを動かす
    """
    cl = Logger()
    cl.run()
    time.sleep(10)
    cl.event.set()
