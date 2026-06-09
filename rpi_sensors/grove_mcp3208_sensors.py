#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import spidev
import time

class GroveAnalogSensorMCP3208:
    """
    MCP3208を経由してアナログセンサを読み取るための共通ベースクラス。
    複数のセンサ（インスタンス）を作成しても、SPI通信のコネクションを
    クラス変数で共有し、リソースを安全に管理します。
    """
    _spi = None
    _use_count = 0

    def __init__(self, channel, spi_bus=0, spi_device=0, vref=3.3):
        """
        :param channel: MCP3208の接続チャンネル (0〜7)
        :param spi_bus: SPIバス番号
        :param spi_device: SPIデバイス番号
        :param vref: MCP3208の基準電圧 (デフォルト3.3V)
        """
        self.channel = channel
        self.vref = vref
        
        # 初回インスタンス化時のみSPIを開く（tactile_button.pyの設計を踏襲）
        if GroveAnalogSensorMCP3208._spi is None:
            GroveAnalogSensorMCP3208._spi = spidev.SpiDev()
            GroveAnalogSensorMCP3208._spi.open(spi_bus, spi_device)
            GroveAnalogSensorMCP3208._spi.max_speed_hz = 1000000
        
        GroveAnalogSensorMCP3208._use_count += 1

    def read_raw(self):
        """12ビット(0〜4095)の生データを読み取る"""
        if self.channel < 0 or self.channel > 7:
            return -1
            
        cmd1 = 0x06 | (self.channel >> 2)
        cmd2 = (self.channel & 3) << 6
        adc = GroveAnalogSensorMCP3208._spi.xfer2([cmd1, cmd2, 0])
        
        data = ((adc[1] & 0x0F) << 8) + adc[2]
        return data

    def read_voltage(self):
        """生データを元に、現在の出力電圧(V)を計算して返す"""
        raw = self.read_raw()
        return (raw * self.vref) / 4095.0

    def read_ratio(self):
        """0.0 (最小) 〜 1.0 (最大) の割合で返す（計算や閾値設定に便利です）"""
        return self.read_raw() / 4095.0

    def close(self):
        """インスタンス破棄時に呼び出す。最後の1つが閉じられた時のみSPIを解放する"""
        GroveAnalogSensorMCP3208._use_count -= 1
        if GroveAnalogSensorMCP3208._use_count <= 0 and GroveAnalogSensorMCP3208._spi is not None:
            GroveAnalogSensorMCP3208._spi.close()
            GroveAnalogSensorMCP3208._spi = None


class GroveLightSensor(GroveAnalogSensorMCP3208):
    """
    Grove 照度センサ用のクラス
    ※ ベースクラスの機能をそのまま引き継ぎますが、将来的に
       ルクス(Lux)への変換式などを追加する場合はここに記述します。
    """
    pass


class GroveSoundSensor(GroveAnalogSensorMCP3208):
    """
    Grove サウンドセンサ用のクラス
    ※ 同様に、将来的にデシベル(dB)変換や、特定の波形取得処理を
       追加する場合はここに記述します。
    """
    pass


# ---------------------------------------------------------
# 単体テスト用ブロック
# ---------------------------------------------------------
if __name__ == '__main__':
    # チャンネル設定 (配線に合わせて変更してください)
    LIGHT_CH = 0
    SOUND_CH = 1

    print("Grove センサ MCP3208 読み取りテスト (Ctrl+Cで終了)")
    
    # センサをそれぞれ独立してインスタンス化
    light_sensor = GroveLightSensor(channel=LIGHT_CH)
    sound_sensor = GroveSoundSensor(channel=SOUND_CH)
    
    try:
        while True:
            # 照度センサの取得
            l_raw = light_sensor.read_raw()
            l_vol = light_sensor.read_voltage()
            l_rat = light_sensor.read_ratio()
            
            # サウンドセンサの取得
            s_raw = sound_sensor.read_raw()
            s_vol = sound_sensor.read_voltage()
            s_rat = sound_sensor.read_ratio()
            
            # 結果を1行でフォーマットして表示
            print(f"☀️ 照度 [CH{LIGHT_CH}]: {l_raw:>4} ({l_rat:>4.1%} / {l_vol:>4.2f}V)  |  "
                  f"🎤 音 [CH{SOUND_CH}]: {s_raw:>4} ({s_rat:>4.1%} / {s_vol:>4.2f}V)")
            
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\nテストを終了します。")
    finally:
        # どちらの close() を呼んでも、内部のカウントによって正しくSPIが解放されます
        light_sensor.close()
        sound_sensor.close()