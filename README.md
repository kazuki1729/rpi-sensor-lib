# rpi-sensor-lib

[![PyPI](https://img.shields.io/pypi/v/rpi-sensor-lib.svg)](https://pypi.org/project/rpi-sensor-lib/)
![Python](https://img.shields.io/badge/Python-3.9%2B-blue?logo=python&logoColor=white)
![Raspberry Pi](https://img.shields.io/badge/Raspberry%20Pi-supported-c51a4a?logo=raspberrypi&logoColor=white)
![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)

Raspberry Piに接続した温湿度・気圧・CO2・照度・アナログ入力などを、
統一されたPython APIで読み取るためのライブラリです。

![動作の様子](https://raw.githubusercontent.com/kazuki1729/rpi-sensor-lib/main/docs/demo.jpg)

## 対応ハードウェア

| センサー／部品 | 通信 | 公開クラス |
| --- | --- | --- |
| BME280 | I2C | `BME280Sensor` |
| DHT22 | GPIO | `RobustDHT22` |
| MH-Z19C | UART | `MHZ19C` |
| MCP3208 + Grove照度 | SPI | `GroveLightSensor` |
| MCP3208 + Groveサウンド | SPI | `GroveSoundSensor` |
| MCP3208 + ジョイスティック | SPI | `JoystickMCP3208` |
| MCP3208 + 半固定抵抗 | SPI | `PotentiometerMCP3208` |
| タクタイルボタン | GPIO | `TactileButton` |

すべての公開クラスは`with`文に対応しています。0.2.0から不正な設定値や
通信エラーは、誤った測定値や`None`ではなく明示的な例外として通知します。

## インストール

パッケージ本体だけをインストールする場合、または別途導入したpi4gpio経由で
利用する場合:

```bash
pip install rpi-sensor-lib
```

Raspberry Piからセンサーへ直接アクセスする場合:

```bash
pip install "rpi-sensor-lib[direct]"
```

必要なドライバーだけを選ぶこともできます。

```bash
pip install "rpi-sensor-lib[adc]"      # MCP3208 / spidev
pip install "rpi-sensor-lib[bme280]"   # BME280 / smbus2
pip install "rpi-sensor-lib[gpio]"     # DHT22・ボタン / lgpio
pip install "rpi-sensor-lib[uart]"     # MH-Z19C / pyserial
```

GitHubの最新コミットを直接試す場合:

```bash
pip install "rpi-sensor-lib[direct] @ git+https://github.com/kazuki1729/rpi-sensor-lib.git"
```

## Raspberry Piの準備

`sudo raspi-config`の`Interface Options`から、使用する通信方式に応じて
SPI、I2C、Serial Portを有効にしてください。

### MCP3208標準配線

| MCP3208 | Raspberry Pi |
| --- | --- |
| VREF / VDD | 3.3V |
| AGND / DGND | GND |
| CLK | GPIO 11 (SCLK) |
| DOUT | GPIO 9 (MISO) |
| DIN | GPIO 10 (MOSI) |
| CS/SHDN | GPIO 8 (CE0) |

### その他の標準設定

| センサー | デフォルト設定 |
| --- | --- |
| BME280 | I2C bus 1、address `0x76`または`0x77` |
| DHT22 | GPIO 26 |
| MH-Z19C | `/dev/serial0`、9600 baud |
| タクタイルボタン | GPIO 17、内蔵プルアップ、押下時GND |

## クイックスタート

### MCP3208アナログ入力

```python
from rpi_sensors import GroveLightSensor, GroveSoundSensor

with GroveLightSensor(channel=0) as light, GroveSoundSensor(channel=1) as sound:
    print(light.read_raw())
    print(light.read_voltage())
    print(sound.read_ratio())
```

```python
from rpi_sensors import JoystickMCP3208, PotentiometerMCP3208

with JoystickMCP3208(deadzone=150) as joystick:
    print(joystick.read_xy(ch_x=0, ch_y=1, normalize=True))

with PotentiometerMCP3208(channel=2, interval_sec=0.1) as potentiometer:
    print(potentiometer.read_percentage())
    print(potentiometer.read_angle())
```

### BME280

```python
from rpi_sensors import BME280InitializationError, BME280Sensor

with BME280Sensor(port=1, address=0x76) as sensor:
    try:
        temperature, humidity, pressure = sensor.read()
        print(temperature, humidity, pressure)
    except BME280InitializationError as exc:
        print(f"BME280を初期化できません: {exc}")
```

一時的なI2C障害で初期化できなかった場合、次の`read()`でバス接続と
キャリブレーション読込を再試行します。

### DHT22

```python
from rpi_sensors import DHT22ReadError, RobustDHT22

with RobustDHT22(pin=26, max_retries=5, read_interval=2.0) as sensor:
    try:
        print(sensor.read())
    except DHT22ReadError as exc:
        print(f"読み取り失敗: {exc}")
```

### MH-Z19C

```python
from rpi_sensors import MHZ19C, MHZ19CError

with MHZ19C(serial_device="/dev/serial0") as sensor:
    try:
        print(sensor.read_co2())
    except MHZ19CError as exc:
        print(f"CO2読み取り失敗: {exc}")
```

UART応答は長さ、ヘッダー、コマンド、チェックサムを検証します。

### タクタイルボタン

```python
import time
from rpi_sensors import TactileButton

with TactileButton(pin=17) as button:
    while True:
        just_pressed, released_duration, held_time = button.update()
        if just_pressed:
            print("押下")
        time.sleep(0.01)
```

## pi4gpioバックエンド

すべてのセンサーをpi4gpiod経由で利用する場合は、`pi4gpio_client`を別途
導入し、プロセス起動前に次を設定します。

```bash
export RPI_SENSOR_BACKEND=pi4gpio
export PI4GPIO_SOCKET_PATH=/run/pi4gpio/pi4gpiod.sock  # 変更する場合だけ指定
```

`RPI_SENSOR_BACKEND`は`direct`または`pi4gpio`だけを受け付けます。

## 開発

```bash
pip install -e ".[dev]"
python -m unittest discover -s tests -v
python -m build
twine check dist/*
```

変更履歴は[CHANGELOG.md](CHANGELOG.md)、脆弱性報告方法は
[SECURITY.md](SECURITY.md)を参照してください。

## ライセンス

MIT License
