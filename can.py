import threading,csv,time

class canlogger:

    def __init__(self):
        # GPS座標を入れておく変数を作る
        self.lat =  36.00000000000000
        self.long = 139.00000000000000
        self.acc = 0

        # ワーカースレッドを起動
        self.event = threading.Event()
        self.logworker = threading.Thread(target=self.logworker)
        self.logworker.start()


    def logworker(self):
        """
        ワーカーとして別スレッドとして起動し、CANデータと位置情報をCSVに記録する.
        """
        while self.event.is_set() == False:
            time.sleep(1)
            print("worker running...")


if __name__ == '__main__':
    """
    デバッグ用にコマンドから実行された場合のみ自力でワーカーを動かす
    """
    cl = canlogger()
    time.sleep(10)
    cl.event.set()
