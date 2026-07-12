#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""direct/pi4gpioバックエンド切り替えの共通ヘルパー。

各センサークラスは、環境変数`RPI_SENSOR_BACKEND`（direct|pi4gpio、
デフォルトdirect）でハードウェアアクセス経路を切り替えられる
（pi4gpioプロジェクトのMIGRATION_PLAN.md参照:
https://github.com/kazuki1729/pi4gpio/blob/main/MIGRATION_PLAN.md）。

pi4gpioバックエンドは明示的にオプトインした場合のみ`pi4gpio_client`を
インポートする。directモードのみの利用者に、まだPyPI未公開の
pi4gpio_clientへの依存を強制しないため。
"""

import os

_BACKEND_ENV_VAR = "RPI_SENSOR_BACKEND"

_shared_client = None


def get_backend() -> str:
    """"direct"または"pi4gpio"を返す。デフォルトは"direct"。"""
    return os.environ.get(_BACKEND_ENV_VAR, "direct")


def is_pi4gpio_backend() -> bool:
    return get_backend() == "pi4gpio"


def get_pi4gpio_client():
    """プロセス内で1つの接続を使い回す。

    pi4gpiodのLockTableは接続単位でロックを保持するため、センサー
    クラスごとに別接続を作ると、同じバスへの複数センサーからの
    アクセスがバス単位ロックの意味を持たなくなる（例: 複数のMCP3208系
    センサーが同じSPIバスを別々の接続で叩くと、お互いを「他クライアント」
    とみなしロック競合してしまう）。全センサークラスがこの関数経由で
    1つの共有接続を使うことで、これを防ぐ。
    """
    global _shared_client
    if _shared_client is None:
        try:
            from pi4gpio_client import DEFAULT_SOCKET_PATH, Pi4gpioClient
        except ImportError as e:
            raise ImportError(
                "RPI_SENSOR_BACKEND=pi4gpioを使うにはpi4gpio_clientが必要です。"
                "pip install -e <pi4gpioリポジトリ>/clients/python でインストールしてください。"
            ) from e
        # デーモン起動時と同じ環境変数名。root権限なしで検証する場合など、
        # /run/pi4gpio以外のソケットパスを使う開発・検証用途に対応する。
        socket_path = os.environ.get("PI4GPIO_SOCKET_PATH", DEFAULT_SOCKET_PATH)
        _shared_client = Pi4gpioClient(socket_path=socket_path)
        _shared_client.connect()
    return _shared_client


class Pi4gpioSMBusShim:
    """`smbus2.SMBus`と同じインターフェースを、pi4gpioクライアント経由で
    提供するアダプタ。`smbus2.SMBus`の全メソッドは実装しておらず、
    `bme280`パッケージ（`bme280/__init__.py`・`bme280/reader.py`）が実際に
    呼び出す4つ（`write_byte_data`/`read_byte_data`/`read_word_data`/
    `read_i2c_block_data`）のみに絞っている。他のI2Cセンサーで追加の
    メソッドが必要になったら、その時点で拡張する。

    `smbus2.SMBus(port)`のように`port`（I2Cバス番号）をコンストラクタで
    固定し、以降は`smbus2`と同じシグネチャ（`i2c_addr`が呼び出しごとの
    引数）で呼べる。
    """

    def __init__(self, client, bus: int):
        self._client = client
        self._bus = bus

    def write_byte_data(self, i2c_addr: int, register: int, value: int) -> None:
        self._client.i2c_write(self._bus, i2c_addr, bytes([register, value]))

    def read_byte_data(self, i2c_addr: int, register: int) -> int:
        data = self._client.i2c_write_read(self._bus, i2c_addr, bytes([register]), 1)
        return data[0]

    def read_word_data(self, i2c_addr: int, register: int) -> int:
        # SMBus Read Wordはリトルエンディアン（下位バイトが先）で送られてくる
        # （bme280/reader.pyのコメント「default is little endian」参照）。
        data = self._client.i2c_write_read(self._bus, i2c_addr, bytes([register]), 2)
        return data[0] | (data[1] << 8)

    def close(self) -> None:
        """`smbus2.SMBus.close()`と同じインターフェース。バスのロックのみ
        解放し、プロセス共有の`Pi4gpioClient`接続自体は閉じない。"""
        self._client.i2c_release(self._bus)

    def read_i2c_block_data(self, i2c_addr: int, register: int, length: int) -> list:
        data = self._client.i2c_write_read(self._bus, i2c_addr, bytes([register]), length)
        return list(data)


class Pi4gpioSpiTransferShim:
    """`spidev.SpiDev`と同じインターフェースを、pi4gpioクライアント経由で
    提供するアダプタ。MCP3208系センサー（`grove_mcp3208_sensors.py`・
    `joystick_mcp3208.py`・`potentiometer_mcp3208.py`）は`xfer2()`のみを
    使うため、それ以外のspidev属性/メソッド（`mode`・`bits_per_word`等）は
    実装していない。`spidev.SpiDev()`＋`.open(bus, device)`という2段階の
    構築とは異なり、コンストラクタで`bus`/`chip_select`を直接指定する
    （呼び出し側の`xfer2()`呼び出し自体は変更不要）。
    """

    def __init__(self, client, bus: int, chip_select: int):
        self._client = client
        self._bus = bus
        self._chip_select = chip_select

    def xfer2(self, data) -> list:
        result = self._client.spi_transfer(self._bus, self._chip_select, bytes(data))
        return list(result)

    def close(self) -> None:
        self._client.spi_release(self._bus, self._chip_select)
