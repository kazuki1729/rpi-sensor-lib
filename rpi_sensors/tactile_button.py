#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__author__ = "tk220424"

import time

from . import _pi4gpio_backend

class TactileButton:
    """
    物理ボタンの入力を読み取るクラス（チャタリング対策 ＆ 長押し計測対応版）

    環境変数RPI_SENSOR_BACKEND（direct|pi4gpio、デフォルトdirect）で
    ハードウェアアクセス経路を切り替えられる。directはlgpioで直接、
    pi4gpioはpi4gpiodデーモン経由（pi4gpioプロジェクトのMIGRATION_PLAN.md
    参照）。
    """
    _handle = None
    _use_count = 0

    def __init__(self, pin, debounce_time=0.05):
        self.pin = pin
        self.debounce_time = debounce_time
        self.backend = _pi4gpio_backend.get_backend()

        # 状態記憶用の変数
        self.last_state = False
        self.press_start_time = 0.0
        self.last_toggle_time = 0.0

        if self.backend == "pi4gpio":
            self._client = _pi4gpio_backend.get_pi4gpio_client()
            # gpio_read()の呼び出しごとにpi4gpiod側でclaim_input(pull=up)
            # し直す設計のため、ここでの明示的な初期化は不要（_read_pressed参照）。
            return

        import lgpio
        self._lgpio = lgpio

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
            print("[Error: tk220424] Invalid channel specified.")

    def _read_pressed(self) -> bool:
        """物理的に押されていればTrueを返す（プルアップ＋押下時にGNDへ落ちる配線を想定）。"""
        if self.backend == "pi4gpio":
            return not self._client.gpio_read(self.pin, pull="up")
        return self._lgpio.gpio_read(TactileButton._handle, self.pin) == 0

    def update(self):
        """
        メインループ内で毎回呼び出して、ボタンの全ステータスを取得する関数。
        戻り値のタプル: (just_pressed, released_duration, current_held_time)
        """
        current_state = self._read_pressed()
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

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    def close(self):
        if self.backend == "pi4gpio":
            self._client.gpio_release(self.pin)
            return

        TactileButton._use_count -= 1
        if TactileButton._use_count <= 0 and TactileButton._handle is not None:
            self._lgpio.gpiochip_close(TactileButton._handle)
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
