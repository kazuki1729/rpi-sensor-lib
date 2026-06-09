#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import smbus2
import bme280
import time

class BME280Sensor:
    """
    BME280 温湿度・気圧センサ読み取りクラス
    ※事前に pip install RPi.bme280 smbus2 が必要です。
    """
    def __init__(self, port=1, address=0x76):
        self.port = port
        self.address = address
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
            print(f"BME280 読み取りエラー: {e}")
            return None, None, None

    def close(self):
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