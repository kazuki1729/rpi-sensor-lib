# rpi_sensors

Raspberry Piに接続された各種センサーやアナログ入出力（ADC）モジュールを、オブジェクト指向でクリーンかつ簡単に操作するためのPythonライブラリです。

チャタリング対策済みの物理ボタン、SPI経由のA/Dコンバータ（MCP3208）を用いたアナログセンサー（照度・音・ジョイスティック・半固定抵抗）、I2C接続の温湿度・気圧センサー（BME280）、GPIO直接駆動の温湿度センサー（DHT22）、UART接続のCO2センサー（MH-Z19C）に幅広く対応しています。環境データの取得からMariaDB等へのロギングといった、IoTシステム開発のベースとして最適です。

---

## 1. 前提条件とハードウェア接続

本ライブラリを使用する前に、Raspberry Pi側で **SPI**, **I2C**, **Serial Port (UART)** が有効化されていることを確認してください（`sudo raspi-config` の `Interface Options` から設定可能）。

### 🔌 ハードウェア接続の標準構成

各モジュール・サンプルのデフォルトのピン配置および接続方法は以下の通りです。

#### 1. SPI通信 (MCP3208 経由のアナログ入力)
MCP3208はRaspberry Piの標準SPIピン（SPI0）に接続します。
* **VREF / VDD**: 3.3V
* **AGND / DGND**: GND
* **CLK**: GPIO 11 (SCLK)
* **DOUT**: GPIO 9 (MISO)
* **DIN**: GPIO 10 (MOSI)
* **CS/SHDN**: GPIO 8 (CE0)

| MCP3208 チャンネル | 対象モジュール / センサー | 該当クラス |
| :--- | :--- | :--- |
| **CH0** | Grove 照度センサー | `GroveLightSensor` |
| **CH1** | Grove サウンドセンサー | `GroveSoundSensor` |
| **CH2** | 半固定抵抗 (ポテンショメータ) | `PotentiometerMCP3208` |
| **CH0 / CH1** (別構成例) | アナログジョイスティック (X軸 / Y軸) | `JoystickMCP3208` |

#### 2. その他のセンサー・コンポーネント (GPIO / I2C / UART)

| センサー名 | 通信規格 | Raspberry Pi 接続ピン (デフォルト) | 該当クラス |
| :--- | :--- | :--- | :--- |
| **BME280** | I2C | GPIO 2 (SDA) / GPIO 3 (SCL) <br>※I2Cアドレス: `0x76` (または `0x77`) | `BME280Sensor` |
| **DHT22** | デジタル単線 | **GPIO 26** | `DHT22` |
| **MH-Z19C** | UART (シリアル) | GPIO 14 (TXD) / GPIO 15 (RXD) <br>※デバイスファイル: `/dev/serial0` | `MHZ19C` |
| **タクタイルボタン** | デジタル入力 | **GPIO 17** (内蔵プルアップ使用、GND接続) | `TactileButton` |

---

## 2. インストール方法

### 📦 リモート（GitHub）からの直接インストール
GitHubリポジトリから直接 `pip` を使用して、依存関係（`lgpio`, `spidev`, `smbus2`, `RPi.bme280`, `pyserial`）ごと一括インストールします。

```bash
pip install git+[https://github.com/kazuki1729/rpi-sensor-lib.git](https://github.com/kazuki1729/rpi-sensor-lib.git)

