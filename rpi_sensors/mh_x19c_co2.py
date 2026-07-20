#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__author__ = "tk220424"

import time
from typing import Optional, Protocol

from . import _pi4gpio_backend
from ._validation import require_non_negative_int, require_positive_number


class MHZ19CError(RuntimeError):
    """Base exception for MH-Z19C communication failures."""


class MHZ19CInitializationError(MHZ19CError):
    """Raised when the UART device cannot be opened."""


class MHZ19CReadError(MHZ19CError):
    """Raised when the sensor does not return a complete valid frame."""


class MHZ19CChecksumError(MHZ19CReadError):
    """Raised when the response checksum does not match the payload."""


class SerialLike(Protocol):
    is_open: bool

    def write(self, data: bytes) -> int: ...

    def read(self, length: int) -> bytes: ...

    def close(self) -> None: ...


def _mhz19_checksum(frame: bytes) -> int:
    """Return the protocol checksum for bytes 1 through 7 of a 9-byte frame."""
    if len(frame) != 9:
        raise ValueError("MH-Z19C frames must contain exactly 9 bytes")
    return (-sum(frame[1:8])) & 0xFF


class MHZ19C:
    """
    MH-Z19C CO2センサ読み取りクラス (UART接続)
    ※事前に pip install pyserial が必要です。

    環境変数RPI_SENSOR_BACKEND（direct|pi4gpio、デフォルトdirect）で
    ハードウェアアクセス経路を切り替えられる（pi4gpioプロジェクトの
    MIGRATION_PLAN.md参照）。pi4gpioモードでは`serial_device`引数は
    使わず、pi4gpiodの命名規約に従う数値ポートを`pi4gpio_port`で指定する
    （デフォルト0、`/dev/ttyS0`）。
    """

    def __init__(
        self,
        serial_device: str = "/dev/serial0",
        baudrate: int = 9600,
        timeout: float = 1.0,
        pi4gpio_port: int = 0,
    ) -> None:
        if not isinstance(serial_device, str) or not serial_device:
            raise ValueError("serial_device must be a non-empty string")
        self.serial_device = serial_device
        self.baudrate = require_non_negative_int("baudrate", baudrate)
        if self.baudrate == 0:
            raise ValueError("baudrate must be greater than zero")
        self.timeout = require_positive_number("timeout", timeout)
        self.pi4gpio_port = require_non_negative_int("pi4gpio_port", pi4gpio_port)
        self.backend = _pi4gpio_backend.get_backend()
        self.ser: Optional[SerialLike] = None

        if self.backend == "pi4gpio":
            client = _pi4gpio_backend.get_pi4gpio_client()
            self.ser = _pi4gpio_backend.Pi4gpioSerialShim(
                client, port=self.pi4gpio_port, baud_rate=self.baudrate
            )
            return

        import serial

        try:
            self.ser = serial.Serial(
                port=self.serial_device,
                baudrate=self.baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=self.timeout,
            )
        except serial.SerialException as exc:
            raise MHZ19CInitializationError(
                f"failed to open serial port {self.serial_device}"
            ) from exc

    def read_co2(self) -> int:
        """
        CO2濃度(ppm)を読み取って返す。失敗時は専用例外を送出する。
        """
        # MH-Z19Cへ送るデータ読み出しコマンド
        command = b"\xff\x01\x86\x00\x00\x00\x00\x00\x79"

        if self.ser is None:
            raise MHZ19CReadError("serial connection is closed")
        try:
            reset_input_buffer = getattr(self.ser, "reset_input_buffer", None)
            if reset_input_buffer is not None:
                reset_input_buffer()
            self.ser.write(command)
            time.sleep(0.1)
            result = self.ser.read(9)
        except Exception as exc:
            raise MHZ19CReadError("UART communication failed") from exc

        if len(result) != 9:
            raise MHZ19CReadError(f"incomplete response: received {len(result)} of 9 bytes")
        if result[0] != 0xFF or result[1] != 0x86:
            raise MHZ19CReadError("invalid response header")
        expected_checksum = _mhz19_checksum(result)
        if result[8] != expected_checksum:
            raise MHZ19CChecksumError(
                f"checksum mismatch: received 0x{result[8]:02x}, "
                f"expected 0x{expected_checksum:02x}"
            )
        return result[2] * 256 + result[3]

    def __enter__(self) -> "MHZ19C":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    def close(self) -> None:
        if self.ser is not None and getattr(self.ser, "is_open", True):
            self.ser.close()
        self.ser = None


if __name__ == "__main__":
    print("MH-Z19C CO2センサテスト (Ctrl+Cで終了)")
    # ラズパイ環境に合わせてデバイスファイルを変更してください（例: /dev/ttyAMA0 等）
    co2_sensor = MHZ19C(serial_device="/dev/serial0")

    try:
        while True:
            try:
                co2 = co2_sensor.read_co2()
                print(f"CO2濃度: {co2} ppm")
            except MHZ19CError as exc:
                print(f"データ取得失敗: {exc}")
            time.sleep(2)
    except KeyboardInterrupt:
        print("\n終了します。")
    finally:
        co2_sensor.close()
