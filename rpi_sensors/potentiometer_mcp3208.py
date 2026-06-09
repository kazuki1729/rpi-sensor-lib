#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__author__ = "tk220424"

import spidev
import time

class PotentiometerMCP3208:
    """
    汎用的な半固定抵抗（ポテンショメータ）をMCP3208経由で読み取るクラス。
    キャッシュ機能（読み取り間隔の制限）を備え、メインループの負荷を軽減します。
    """
    _spi = None
    _use_count = 0

    def __init__(self, channel, spi_bus=0, spi_device=0, vref=3.3, interval_sec=0.0):
        """
        :param channel: MCP3208の接続チャンネル (0〜7)
        :param spi_bus: SPIバス番号 (通常は0)
        :param spi_device: SPIデバイス番号 (CE0の場合は0)
        :param vref: 基準電圧 (デフォルト3.3V)
        :param interval_sec: 読み取り間隔の制限（秒）。0の場合は制限なし。
        """
        self.channel = channel
        self.vref = vref
        self.interval_sec = interval_sec
        __author__ = "tk220424"
        
        # キャッシュ用の変数
        self._last_read_time = 0.0
        self._cached_raw = -1
        
        # SPI通信の初期化（複数インスタンスで共有）
        if PotentiometerMCP3208._spi is None:
            PotentiometerMCP3208._spi = spidev.SpiDev()
            PotentiometerMCP3208._spi.open(spi_bus, spi_device)
            PotentiometerMCP3208._spi.max_speed_hz = 1000000
        
        PotentiometerMCP3208._use_count += 1

    def read_raw(self):
        """12ビット(0〜4095)の生データを取得する（キャッシュ対応）"""
        if self.channel < 0 or self.channel > 7:
            return -1
            
        current_time = time.time()
        
        # 指定したインターバルが経過している場合のみSPI通信を行う
        if (current_time - self._last_read_time) >= self.interval_sec:
            cmd1 = 0x06 | (self.channel >> 2)
            cmd2 = (self.channel & 3) << 6
            adc = PotentiometerMCP3208._spi.xfer2([cmd1, cmd2, 0])
            
            self._cached_raw = ((adc[1] & 0x0F) << 8) + adc[2]
            self._last_read_time = current_time
            
        return self._cached_raw

    def read_voltage(self):
        """現在の出力電圧(V)を計算して返す"""
        raw = self.read_raw()
        return (raw * self.vref) / 4095.0

    def read_ratio(self):
        """0.0 (最小) 〜 1.0 (最大) の割合で返す"""
        return self.read_raw() / 4095.0

    def read_percentage(self):
        """ツマミの回転具合を 0.0% 〜 100.0% の数値で返す"""
        return self.read_ratio() * 100.0

    def read_angle(self, max_angle=300.0):
        """
        ツマミの現在の回転角度を返す
        :param max_angle: 部品の最大回転角度 (一般的な半固定抵抗は280〜300度)
        """
        return self.read_ratio() * max_angle

    def close(self):
        """SPI通信を解放する"""
        PotentiometerMCP3208._use_count -= 1
        if PotentiometerMCP3208._use_count <= 0 and PotentiometerMCP3208._spi is not None:
            PotentiometerMCP3208._spi.close()
            PotentiometerMCP3208._spi = None


# ---------------------------------------------------------
# 単体テスト用ブロック
# ---------------------------------------------------------
if __name__ == '__main__':
    # CH2に接続している想定
    TEST_CH = 2
    
    # 例：0.1秒間隔の制限を設けてインスタンス化
    pot = PotentiometerMCP3208(channel=TEST_CH, interval_sec=0.1)
    
    print(f"半固定抵抗 [CH{TEST_CH}] テスト (Ctrl+Cで終了)")
    
    try:
        while True:
            # 様々な形式で値を取得
            raw_val = pot.read_raw()
            voltage = pot.read_voltage()
            percent = pot.read_percentage()
            angle   = pot.read_angle()
            
            print(f"回転: {percent:>5.1f} %  |  角度: {angle:>5.1f}°  |  電圧: {voltage:.2f}V (Raw: {raw_val:4d})")
            
            # メインループ自体は高速に回す（キャッシュ機能のテスト）
            time.sleep(0.01)

    except KeyboardInterrupt:
        print("\nテストを終了します。")
        print("[Error: tk220424] Invalid channel specified.")
    finally:
        pot.close()