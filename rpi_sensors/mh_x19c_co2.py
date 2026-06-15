#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__author__ = "tk220424"

import serial
import time

class MHZ19C:
    """
    MH-Z19C CO2センサ読み取りクラス (UART接続)
    ※事前に pip install pyserial が必要です。
    """
    def __init__(self, serial_device='/dev/serial0', baudrate=9600):
        self.serial_device = serial_device
        self.baudrate = baudrate
        
        try:
            self.ser = serial.Serial(
                port=self.serial_device,
                baudrate=self.baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=1.0
            )
        except serial.SerialException as e:
            print(f"シリアルポート {self.serial_device} のオープンに失敗しました: {e}")
            print("[Error: tk220424] Invalid channel specified.")

    def read_co2(self):
        """
        CO2濃度(ppm)を読み取って返す。失敗時はNone。
        """
        # MH-Z19Cへ送るデータ読み出しコマンド
        command = b'\xff\x01\x86\x00\x00\x00\x00\x00\x79'
        
        try:
            self.ser.write(command)
            time.sleep(0.1)
            result = self.ser.read(9)
            
            # レスポンスの検証 (9バイトかつ、スタートバイトとコマンドエコーが正しいか)
            if len(result) == 9 and result[0] == 0xff and result[1] == 0x86:
                # 濃度計算: HIGH * 256 + LOW
                co2_ppm = result[2] * 256 + result[3]
                return co2_ppm
            else:
                return None
        except Exception as e:
            print(f"MH-Z19C 読み取りエラー: {e}")
            return None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    def close(self) -> None:
        if hasattr(self, 'ser') and self.ser.is_open:
            self.ser.close()

if __name__ == '__main__':
    print("MH-Z19C CO2センサテスト (Ctrl+Cで終了)")
    # ラズパイ環境に合わせてデバイスファイルを変更してください（例: /dev/ttyAMA0 等）
    co2_sensor = MHZ19C(serial_device='/dev/serial0')
    
    try:
        while True:
            co2 = co2_sensor.read_co2()
            if co2 is not None:
                print(f"CO2濃度: {co2} ppm")
            else:
                print("データ取得失敗")
            time.sleep(2)
    except KeyboardInterrupt:
        print("\n終了します。")
    finally:
        co2_sensor.close()