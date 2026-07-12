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
