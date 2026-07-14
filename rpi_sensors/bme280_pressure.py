#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__author__ = "tk220424"

import time

import bme280

from . import _pi4gpio_backend


class BME280InitializationError(RuntimeError):
    """BME280のキャリブレーションデータ読み込みに失敗した場合の例外。"""


class BME280Sensor:
    """
    BME280 温湿度・気圧センサ読み取りクラス
    ※事前に pip install RPi.bme280 smbus2 が必要です。

    環境変数RPI_SENSOR_BACKEND（direct|pi4gpio、デフォルトdirect）で
    ハードウェアアクセス経路を切り替えられる。directはsmbus2で直接、
    pi4gpioはpi4gpiodデーモン経由（pi4gpioプロジェクトのMIGRATION_PLAN.md
    参照）。`bme280`パッケージ自体はどちらのモードでも無改造で動く
    ——smbus2.SMBusと同じインターフェース（read_byte_data等）さえ
    満たしていれば良いため（`_pi4gpio_backend.Pi4gpioSMBusShim`参照）。

    設計上の注意（過去のバグ経緯）:
    以前の実装は、コンストラクタでのキャリブレーション読み込み失敗を
    print()するだけで握りつぶし、calibration_paramsが未設定のまま
    オブジェクト生成を「成功」させていた。本番で起動直後に一時的な
    I2Cエラー(Errno 5等)が1回起きただけで、以降read()を呼ぶたびに
    'calibration_params'属性が存在せずAttributeErrorになり続け、
    プロセスを再起動するまで気圧が永久にNoneになる障害を実際に起こした。
    この教訓から、read()側で毎回「未初期化なら再初期化を試みる」設計に
    改めている。一方コンストラクタ自体は例外を投げない——他に7種類の
    センサーを扱う呼び出し側(sensor_client_tiered.py等)にとって、
    BME280の一時的な初期化失敗だけで全センサーの起動が巻き添えで
    止まるのは望ましくないため。
    """
    def __init__(self, port=1, address=0x76):
        self.port = port
        self.address = address
        self.backend = _pi4gpio_backend.get_backend()
        self.bus = None
        self.calibration_params = None
        self._open_bus()
        self._load_calibration()

    def _open_bus(self):
        """I2Cバスを(再)接続する。既存のバスがあれば先に閉じる。"""
        if self.bus is not None:
            try:
                self.bus.close()
            except Exception:
                pass

        if self.backend == "pi4gpio":
            client = _pi4gpio_backend.get_pi4gpio_client()
            self.bus = _pi4gpio_backend.Pi4gpioSMBusShim(client, self.port)
        else:
            import smbus2
            self.bus = smbus2.SMBus(self.port)

    def _load_calibration(self):
        """キャリブレーションデータを読み込む。

        失敗しても例外は送出せず、calibration_paramsをNoneのままにする
        (read()側での再試行に委ねるため)。ここで例外を投げてコンストラクタ
        全体を失敗させると、他の7種のセンサーの初期化・送信まで巻き添えで
        止まってしまう。
        """
        try:
            self.calibration_params = bme280.load_calibration_params(self.bus, self.address)
        except Exception as e:
            self.calibration_params = None
            print(f"BME280の初期化に失敗しました。アドレス(0x76 or 0x77)と配線を確認してください: {e}")

    def read(self):
        """
        温度(℃)、湿度(%)、気圧(hPa)のタプルを返す。

        calibration_paramsが未取得(前回までの初期化失敗)の場合、read()の
        たびにバスを開き直してキャリブレーション読み込みを再試行する。
        これでも取得できなければBME280InitializationErrorを送出する
        (呼び出し側は他のセンサークラスと同様、read()自体の例外として
        捕捉できる——以前の「内部で握りつぶしNoneを返す」動作と違い、
        呼び出し側の失敗センサー一覧に正しく計上されるようになる)。
        """
        if self.calibration_params is None:
            self._open_bus()
            self._load_calibration()
            if self.calibration_params is None:
                raise BME280InitializationError(
                    "BME280のキャリブレーションデータが読み込めていません"
                    "（配線・電源、またはI2Cバスの状態を確認してください）")

        try:
            data = bme280.sample(self.bus, self.address, self.calibration_params)
        except Exception:
            # 読み取り自体が失敗した場合も、次回read()時に再初期化を試みる
            self.calibration_params = None
            raise
        return data.temperature, data.humidity, data.pressure

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    def close(self) -> None:
        # Pi4gpioSMBusShimもsmbus2.SMBusと同じclose()インターフェースを
        # 持つため、backendで分岐する必要が無い。
        if self.bus is not None:
            self.bus.close()


if __name__ == '__main__':
    print("BME280 センサテスト (Ctrl+Cで終了)")
    sensor = BME280Sensor(address=0x76)  # モジュールによっては 0x77 の場合あり

    try:
        while True:
            try:
                temp, hum, pres = sensor.read()
                print(f"温度: {temp:.2f} °c | 湿度: {hum:.2f} % | 気圧: {pres:.2f} hPa")
            except BME280InitializationError as e:
                print(f"読み取り失敗: {e}")
            time.sleep(2)
    except KeyboardInterrupt:
        print("\n終了します。")
    finally:
        sensor.close()
