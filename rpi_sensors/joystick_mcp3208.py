#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__author__ = "tk220424"

from typing import Optional, Tuple, Union

from ._spi_resource import SpiLease, acquire_spi
from ._validation import require_int_range


class JoystickMCP3208:
    """
    MCP3208経由でアナログジョイスティックを制御する汎用クラス

    環境変数RPI_SENSOR_BACKEND（direct|pi4gpio、デフォルトdirect）で
    ハードウェアアクセス経路を切り替えられる（pi4gpioプロジェクトの
    MIGRATION_PLAN.md参照）。
    """

    def __init__(self, spi_bus: int = 0, spi_device: int = 0, deadzone: int = 150) -> None:
        """
        :param spi_bus: SPIバス番号（基本は0）
        :param spi_device: SPIデバイス番号（基本は0）
        :param deadzone: スティック中心の「遊び」の幅（ドリフト防止）
        """
        self.deadzone = require_int_range("deadzone", deadzone, 0, 2046)
        self.spi: Optional[SpiLease] = acquire_spi(spi_bus, spi_device)

    def _read_adc(self, channel: int) -> int:
        """MCP3208から12ビット(0〜4095)の生データを読み取る内部関数"""
        channel = require_int_range("channel", channel, 0, 7)
        if self.spi is None:
            raise RuntimeError("joystick is closed")
        # MCP3208用のSPI通信フォーマット
        cmd1 = 0x06 | (channel >> 2)
        cmd2 = (channel & 3) << 6
        adc = self.spi.xfer2([cmd1, cmd2, 0])
        if len(adc) != 3:
            raise IOError(f"MCP3208 returned {len(adc)} bytes; expected 3")
        # 12ビットのデータを取り出す（adc[1]の下位4ビット + adc[2]の8ビット）
        data = ((adc[1] & 0x0F) << 8) + adc[2]
        return data

    def read_xy(
        self, ch_x: int, ch_y: int, normalize: bool = False
    ) -> Tuple[Union[int, float], Union[int, float]]:
        """
        指定したチャンネルのX軸とY軸の値を同時に取得する関数。

        :param ch_x: X軸が繋がっているチャンネル番号(0〜7)
        :param ch_y: Y軸が繋がっているチャンネル番号(0〜7)
        :param normalize: Trueにすると -1.0 ～ 1.0 のゲーム用数値に変換して返す
        :return: (x_val, y_val) のタプル
        """
        raw_x = self._read_adc(ch_x)
        raw_y = self._read_adc(ch_y)

        if not normalize:
            # 生データ（0〜4095）をそのまま返す
            return raw_x, raw_y

        # --- ここから下はゲーム向けの正規化（-1.0 ~ 1.0）処理 ---
        def apply_deadzone_and_normalize(val: int) -> float:
            center = 2048  # 12ビット(4096)の中心
            diff = val - center

            # デッドゾーン（遊び）以内なら、中心(0.0)とみなす
            if abs(diff) < self.deadzone:
                return 0.0

            # デッドゾーンを超えた分を -1.0 ～ 1.0 の比率に変換
            if diff > 0:
                return round((diff - self.deadzone) / (2047 - self.deadzone), 3)
            else:
                return round((diff + self.deadzone) / (2048 - self.deadzone), 3)

        norm_x = apply_deadzone_and_normalize(raw_x)
        norm_y = apply_deadzone_and_normalize(raw_y)

        return norm_x, norm_y

    def __enter__(self) -> "JoystickMCP3208":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    def close(self) -> None:
        """SPI通信を終了する"""
        if self.spi is not None:
            self.spi.close()
            self.spi = None


if __name__ == "__main__":
    import time

    joy = JoystickMCP3208(deadzone=150)

    try:
        print("MCP3208 ジョイスティックテスト (Ctrl+Cで終了)")
        while True:
            # CH0をX軸、CH1をY軸として、正規化して読み取る
            x, y = joy.read_xy(ch_x=0, ch_y=1, normalize=True)
            print(f"X軸: {x:>5.2f} | Y軸: {y:>5.2f}")
            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\n終了します。")
    finally:
        joy.close()
