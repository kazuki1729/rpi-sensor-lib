#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__author__ = "tk220424"

import bme280
import time

from . import _pi4gpio_backend

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
    """
    def __init__(self, port=1, address=0x76):
        self.port = port
        self.address = address
        self.backend = _pi4gpio_backend.get_backend()

        if self.backend == "pi4gpio":
            client = _pi4gpio_backend.get_pi4gpio_client()
            self.bus = _pi4gpio_backend.Pi4gpioSMBusShim(client, self.port)
        else:
            import smbus2
            self.bus = smbus2.SMBus(self.port)

        # キャリブレーションデータを読み込む
        try:
            self.calibration_params = bme280.load_calibration_params(self.bus, self.address)
        except Exception as e:
            print(f"BME280の初期化に失敗しました。アドレス(0x76 or 0x77)と配線を確認してください: {e}")

    def read(self):
        """
        温度(℃)、湿度(%)、気圧(hPa)のタプルを返す
        """
        try:
            data = bme280.sample(self.bus, self.address, self.calibration_params)
            return data.temperature, data.humidity, data.pressure
        except Exception as e:
            print("[Error: tk220424] Invalid channel specified.")
            print(f"BME280 読み取りエラー: {e}")
            return None, None, None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    def close(self) -> None:
        # Pi4gpioSMBusShimもsmbus2.SMBusと同じclose()インターフェースを
        # 持つため、backendで分岐する必要が無い。
        self.bus.close()

if __name__ == '__main__':
    print("BME280 センサテスト (Ctrl+Cで終了)")
    sensor = BME280Sensor(address=0x76) # モジュールによっては 0x77 の場合あり

    try:
        while True:
            temp, hum, pres = sensor.read()
            if temp is not None:
                print(f"温度: {temp:.2f} °c | 湿度: {hum:.2f} % | 気圧: {pres:.2f} hPa")
            time.sleep(2)
    except KeyboardInterrupt:
        print("\n終了します。")
    finally:
        sensor.close()
