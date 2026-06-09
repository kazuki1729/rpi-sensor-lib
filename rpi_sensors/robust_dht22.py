#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "tk220424"

import lgpio
import time

class DHT22ReadError(Exception):
    """DHT22の読み取りが規定回数失敗した場合に発生する例外"""
    pass

class RobustDHT22:
    """
    Linuxのマルチタスクによるタイミングのズレ（DHT22の癖）を考慮し、
    自動リトライ処理や読み取り間隔の制限（キャッシュ）を組み込んだDHT22クラス。
    """
    def __init__(self, pin=26, max_retries=5, read_interval=2.0):
        self.pin = pin
        self.max_retries = max_retries
        self.read_interval = read_interval  # DHT22は仕様上2秒以上の間隔が必要
        
        self._handle = lgpio.gpiochip_open(0)
        
        # キャッシュ用の変数
        self._last_read_time = 0.0
        self._cached_temp = None
        self._cached_hum = None

    def read(self):
        """
        温湿度を取得します。
        前回の取得から規定秒数以内の場合は、キャッシュした前回の値を返します。
        """
        current_time = time.time()
        
        # 1. キャッシュの確認（2秒以内の連続アクセスを防止）
        if (current_time - self._last_read_time) < self.read_interval:
            if self._cached_temp is not None:
                return self._cached_temp, self._cached_hum
        
        # 2. 自動リトライループ
        for attempt in range(self.max_retries):
            try:
                temp, hum = self._read_raw()
                
                # 取得成功時の処理
                self._cached_temp = temp
                self._cached_hum = hum
                self._last_read_time = time.time()
                return temp, hum
                
            except Exception:
                # 失敗した場合は仕様通り2秒待ってから再トライ
                if attempt < self.max_retries - 1:
                    time.sleep(self.read_interval)
                
        # 規定回数すべて失敗した場合
        raise DHT22ReadError(f"GPIO{self.pin}のDHT22読み取りに{self.max_retries}回失敗しました。")

    def _read_raw(self):
        """lgpioを利用して生の波形を読み取り、温湿度に変換する内部関数"""
        lgpio.gpio_claim_output(self._handle, self.pin)
        
        # スタートシグナル送信 (LOWを18ms保持したあと、HIGHにして入力モードへ)
        lgpio.gpio_write(self._handle, self.pin, 0)
        time.sleep(0.018)
        lgpio.gpio_write(self._handle, self.pin, 1)
        
        # 入力モード(プルアップ)に切り替えて波形を監視
        lgpio.gpio_claim_input(self._handle, self.pin, lgpio.SET_PULL_UP)
        
        data = []
        last_state = -1
        unchanged_count = 0
        max_unchanged = 100
        
        # 【超高速ループ】ピンの状態変化を記録し続ける
        while True:
            current_state = lgpio.gpio_read(self._handle, self.pin)
            data.append(current_state)
            if last_state != current_state:
                unchanged_count = 0
                last_state = current_state
            else:
                unchanged_count += 1
                # 一定時間状態が変わらなければ通信終了とみなす
                if unchanged_count > max_unchanged:
                    break

        # 記録した波形から、HIGH期間の長さ（パルス長）を抽出
        lengths = []
        current_len = 0
        state = 1
        # 状態遷移: 1:初期LOW, 2:初期HIGH, 3:データLOW, 4:データHIGH, 5:データLOW
        for val in data:
            current_len += 1
            if state == 1 and val == 0:
                state = 2
            elif state == 2 and val == 1:
                state = 3
            elif state == 3 and val == 0:
                state = 4
            elif state == 4 and val == 1:
                current_len = 0
                state = 5
            elif state == 5 and val == 0:
                lengths.append(current_len)
                state = 4

        # データ数の検証 (40ビット = 5バイト分あるか)
        if len(lengths) != 40:
            raise ValueError("データ欠損")

        # 長いパルス(1)と短いパルス(0)の閾値を計算
        threshold = min(lengths) + (max(lengths) - min(lengths)) / 2
        bits = [1 if length > threshold else 0 for length in lengths]

        # ビット列を5つのバイトデータに変換
        the_bytes = []
        byte_val = 0
        for i, bit in enumerate(bits):
            byte_val = (byte_val << 1) | bit
            if (i + 1) % 8 == 0:
                the_bytes.append(byte_val)
                byte_val = 0

        # チェックサムの検証 (最初の4バイトの合計の下位8ビットと、5バイト目が一致するか)
        checksum = sum(the_bytes[0:4]) & 0xFF
        if the_bytes[4] != checksum:
            raise ValueError("CRCエラー")

        # バイトデータを温湿度に変換
        humidity = ((the_bytes[0] << 8) + the_bytes[1]) / 10.0
        
        temp_raw = (the_bytes[2] << 8) + the_bytes[3]
        temperature = temp_raw / 10.0
        if temp_raw & 0x8000: # 最上位ビットが1ならマイナス温度
            temperature = - (temp_raw & 0x7FFF) / 10.0

        return temperature, humidity

    def close(self):
        """リソースの解放"""
        if self._handle is not None:
            lgpio.gpiochip_close(self._handle)
            self._handle = None


# ---------------------------------------------------------
# 単体テスト用ブロック
# ---------------------------------------------------------
if __name__ == '__main__':
    # GPIO 26 でテスト
    TEST_PIN = 26
    
    print(f"DHT22 (GPIO {TEST_PIN}) 堅牢化クラス テスト (Ctrl+Cで終了)")
    print("※ 内部でリトライ処理を行うため、最初の取得に数秒かかる場合があります。")
    
    # max_retries=5 を指定しているため、OSの邪魔が入っても最大5回まで自動で粘ります
    sensor = RobustDHT22(pin=TEST_PIN, max_retries=5)
    
    try:
        while True:
            try:
                # 利用する側は、単純に read() を呼ぶだけでOK
                temp, hum = sensor.read()
                print(f"温度: {temp:.1f} °C | 湿度: {hum:.1f} %")
                
            except DHT22ReadError as e:
                # 5回連続で失敗するような致命的なエラー時のみここに入ります
                print(f"\nエラー: {e}")
                print("配線やピン番号が正しいか確認してください。")
            
            # メインループを高速で回しても、クラス側がキャッシュを返すため安全です
            time.sleep(1.0)
            
    except KeyboardInterrupt:
        print("\nテストを終了します。")
    finally:
        sensor.close()