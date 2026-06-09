#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import lgpio
import time

class TactileButton:
    """
    物理ボタンの入力を読み取るクラス（チャタリング対策 ＆ 長押し計測対応版）
    """
    _handle = None
    _use_count = 0

    def __init__(self, pin, debounce_time=0.05):
        self.pin = pin
        self.debounce_time = debounce_time
        
        # 状態記憶用の変数
        self.last_state = False
        self.press_start_time = 0.0
        self.last_toggle_time = 0.0
        
        if TactileButton._handle is None:
            TactileButton._handle = lgpio.gpiochip_open(0)
        TactileButton._use_count += 1
        
        try:
            lgpio.gpio_claim_input(
                TactileButton._handle, 
                self.pin, 
                lgpio.SET_PULL_UP
            )
        except Exception as e:
            print(f"GPIO {self.pin} の初期化に失敗しました: {e}")

    def update(self):
        """
        メインループ内で毎回呼び出して、ボタンの全ステータスを取得する関数。
        戻り値のタプル: (just_pressed, released_duration, current_held_time)
        """
        current_state = (lgpio.gpio_read(TactileButton._handle, self.pin) == 0)
        current_time = time.time()
        
        just_pressed = False
        released_duration = 0.0
        current_held_time = 0.0

        # 状態が変化した時（かつチャタリング回避時間を超えている場合）
        if current_state != self.last_state and (current_time - self.last_toggle_time) > self.debounce_time:
            self.last_toggle_time = current_time
            self.last_state = current_state
            
            if current_state:
                # 離されている -> 押された（押した瞬間）
                just_pressed = True
                self.press_start_time = current_time
            else:
                # 押されている -> 離された（離した瞬間）
                released_duration = current_time - self.press_start_time
                self.press_start_time = 0.0

        # 現在押しっぱなしにしている時間の計算（リアルタイム取得用）
        if self.last_state and self.press_start_time > 0:
            current_held_time = current_time - self.press_start_time

        return just_pressed, released_duration, current_held_time

    def close(self):
        TactileButton._use_count -= 1
        if TactileButton._use_count <= 0 and TactileButton._handle is not None:
            lgpio.gpiochip_close(TactileButton._handle)
            TactileButton._handle = None

# ---------------------------------------------------------
# 単体テスト用ブロック
# ---------------------------------------------------------
if __name__ == '__main__':
    TEST_PIN = 17
    print(f"GPIO {TEST_PIN} 長押しテスト (Ctrl+Cで終了)")
    btn = TactileButton(pin=TEST_PIN)
    
    try:
        while True:
            # 🌟 update() を呼ぶだけで、欲しい情報がすべて手に入る
            just_pressed, released_duration, held_time = btn.update()
            
            # ① 押した瞬間
            if just_pressed:
                print("🔴 カチッ！ (押下開始)")
            
            # ② 押しっぱなしにしている最中（例: 3秒を超えたら発動）
            if held_time > 0:
                print(f"   ⏳ 押しています... {held_time:.1f}秒", end="\r")
                if held_time >= 3.0:
                    print("\n💥 3秒長押し発動！ (リセットします)")
                    btn.press_start_time = time.time() # カウントをリセット
            
            # ③ 離した瞬間（合計で何秒押されていたかが分かる）
            if released_duration > 0:
                print(f"\n🟢 パッ！ ({released_duration:.2f} 秒間 押されていました)")
                
            time.sleep(0.01)
    except KeyboardInterrupt:
        pass
    finally:
        btn.close()