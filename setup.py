from setuptools import setup, find_packages

setup(
    name="rpi_sensors",               # pipで表示されるパッケージ名
    version="0.1.0",                  # バージョン
    description="Raspberry Pi用の各種センサー読み取りライブラリ",
    author="Kazuki Kumahata",          # 作者名
    packages=find_packages(),         # rpi_sensorsフォルダを自動検出
    install_requires=[                # 依存する外部ライブラリを列挙
        "spidev",
        "smbus2",
        "RPi.bme280",
        "lgpio",
        "pyserial"
    ],
    python_requires=">=3.6",
    entry_points={
        'console_scripts': [
            # 左側がターミナルで打ち込むコマンド名、右側が実行される関数
            'rpi-sensors-verify=rpi_sensors:verify_identity',
        ],
    },
)