#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__author__ = "tk220424"

import time
from typing import Optional

from ._spi_resource import SpiLease, acquire_spi
from ._validation import (
    require_int_range,
    require_non_negative_number,
    require_positive_number,
)


class PotentiometerMCP3208:
    """
    汎用的な半固定抵抗（ポテンショメータ）をMCP3208経由で読み取るクラス。
    キャッシュ機能（読み取り間隔の制限）を備え、メインループの負荷を軽減します。

    環境変数RPI_SENSOR_BACKEND（direct|pi4gpio、デフォルトdirect）で
    ハードウェアアクセス経路を切り替えられる（pi4gpioプロジェクトの
    MIGRATION_PLAN.md参照）。
    """

    def __init__(
        self,
        channel: int,
        spi_bus: int = 0,
        spi_device: int = 0,
        vref: float = 3.3,
        interval_sec: float = 0.0,
    ) -> None:
        """
        :param channel: MCP3208の接続チャンネル (0〜7)
        :param spi_bus: SPIバス番号 (通常は0)
        :param spi_device: SPIデバイス番号 (CE0の場合は0)
        :param vref: 基準電圧 (デフォルト3.3V)
        :param interval_sec: 読み取り間隔の制限（秒）。0の場合は制限なし。
        """
        self.channel = require_int_range("channel", channel, 0, 7)
        self.vref = require_positive_number("vref", vref)
        self.interval_sec = require_non_negative_number("interval_sec", interval_sec)

        # キャッシュ用の変数
        self._last_read_time = 0.0
        self._cached_raw = -1

        self._spi: Optional[SpiLease] = acquire_spi(spi_bus, spi_device)

    def read_raw(self) -> int:
        """12ビット(0〜4095)の生データを取得する（キャッシュ対応）"""
        if self._spi is None:
            raise RuntimeError("potentiometer is closed")
        current_time = time.monotonic()

        # 指定したインターバルが経過している場合のみSPI通信を行う
        if (current_time - self._last_read_time) >= self.interval_sec:
            cmd1 = 0x06 | (self.channel >> 2)
            cmd2 = (self.channel & 3) << 6
            adc = self._spi.xfer2([cmd1, cmd2, 0])
            if len(adc) != 3:
                raise IOError(f"MCP3208 returned {len(adc)} bytes; expected 3")
            self._cached_raw = ((adc[1] & 0x0F) << 8) + adc[2]
            self._last_read_time = current_time

        return self._cached_raw

    def read_voltage(self) -> float:
        """現在の出力電圧(V)を計算して返す"""
        raw = self.read_raw()
        return (raw * self.vref) / 4095.0

    def read_ratio(self) -> float:
        """0.0 (最小) 〜 1.0 (最大) の割合で返す"""
        return self.read_raw() / 4095.0

    def read_percentage(self) -> float:
        """ツマミの回転具合を 0.0% 〜 100.0% の数値で返す"""
        return self.read_ratio() * 100.0

    def read_angle(self, max_angle: float = 300.0) -> float:
        """
        ツマミの現在の回転角度を返す
        :param max_angle: 部品の最大回転角度 (一般的な半固定抵抗は280〜300度)
        """
        return self.read_ratio() * require_positive_number("max_angle", max_angle)

    def __enter__(self) -> "PotentiometerMCP3208":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    def close(self) -> None:
        """SPI通信を解放する"""
        if self._spi is not None:
            self._spi.close()
            self._spi = None


# ---------------------------------------------------------
# 単体テスト用ブロック
# ---------------------------------------------------------
if __name__ == "__main__":
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
            angle = pot.read_angle()

            print(
                f"回転: {percent:>5.1f} %  |  角度: {angle:>5.1f}°  |  "
                f"電圧: {voltage:.2f}V (Raw: {raw_val:4d})"
            )

            # メインループ自体は高速に回す（キャッシュ機能のテスト）
            time.sleep(0.01)

    except KeyboardInterrupt:
        print("\nテストを終了します。")
    finally:
        pot.close()
