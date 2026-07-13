"""`_decode_dht22_edges`（DHT22の40ビットデコードロジック）の合成データテスト。

実センサー無しでも、既知のビット列から合成したエッジ列を通せば、デコード
ロジック自体の正しさを検証できる。pi4gpioプロジェクトとの実機検証
（2026-07-13、VERIFICATION_LOG.md）で、このセンサー個体では40ビット目の
終端エッジが観測できないことがあると判明し、チェックサムからの逆算処理を
追加した際の回帰テストも兼ねる。
"""

import sys
import types
import unittest

# rpi_sensorsパッケージの__init__.pyは全センサーモジュールを即座にimportし、
# その中にはRaspberry Pi実機専用ライブラリ（bme280/smbus2/spidev/serial/
# lgpio）へのトップレベルimportを含むものがある。CI・開発機（非Pi環境）
# でも本テストが動くよう、実際には使わないこれらをスタブで満たす。
for _mod_name in ("bme280", "smbus2", "spidev", "serial", "lgpio"):
    sys.modules.setdefault(_mod_name, types.ModuleType(_mod_name))

from rpi_sensors.robust_dht22 import _decode_dht22_edges  # noqa: E402


def _build_edges(temp_c, hum_pct, drop_last_edge=False, corrupt_checksum=False, drop_extra=0):
    """既知の温湿度値から、DHT22が実際に送出するのと同じ形のタイムスタンプ
    付きエッジ列を合成する。`drop_last_edge`で40ビット目の終端エッジを
    落とし、実機で確認された欠落パターンを再現できる。
    """
    hum_raw = round(hum_pct * 10)
    temp_raw = round(abs(temp_c) * 10)
    if temp_c < 0:
        temp_raw |= 0x8000
    byte0 = (hum_raw >> 8) & 0xFF
    byte1 = hum_raw & 0xFF
    byte2 = (temp_raw >> 8) & 0xFF
    byte3 = temp_raw & 0xFF
    checksum = (byte0 + byte1 + byte2 + byte3) & 0xFF
    if corrupt_checksum:
        checksum ^= 0xFF
    the_bytes = [byte0, byte1, byte2, byte3, checksum]

    bits = []
    for b in the_bytes:
        for i in range(7, -1, -1):
            bits.append((b >> i) & 1)

    edges = []
    t = 0
    edges.append({"timestamp_ns": t, "rising": False})
    t += 80_000
    edges.append({"timestamp_ns": t, "rising": True})
    t += 80_000
    for i, bit in enumerate(bits):
        is_last = i == len(bits) - 1
        edges.append({"timestamp_ns": t, "rising": False})
        t += 50_000
        edges.append({"timestamp_ns": t, "rising": True})
        t += 70_000 if bit else 27_000
        if is_last and drop_last_edge:
            continue
        edges.append({"timestamp_ns": t, "rising": False})
        t += 1
    if drop_extra:
        edges = edges[: len(edges) - drop_extra]
    return edges


class DecodeDht22EdgesTest(unittest.TestCase):
    def test_normal_case(self):
        edges = _build_edges(23.4, 65.5)
        temp, hum = _decode_dht22_edges(edges)
        self.assertAlmostEqual(temp, 23.4, places=1)
        self.assertAlmostEqual(hum, 65.5, places=1)

    def test_negative_temperature(self):
        edges = _build_edges(-5.3, 40.2)
        temp, hum = _decode_dht22_edges(edges)
        self.assertAlmostEqual(temp, -5.3, places=1)
        self.assertAlmostEqual(hum, 40.2, places=1)

    def test_last_edge_missing_reconstructs_bit0(self):
        edges = _build_edges(23.4, 65.5, drop_last_edge=True)
        temp, hum = _decode_dht22_edges(edges)
        self.assertAlmostEqual(temp, 23.4, places=1)
        self.assertAlmostEqual(hum, 65.5, places=1)

    def test_last_edge_missing_reconstructs_bit1(self):
        edges = _build_edges(24.6, 68.0, drop_last_edge=True)
        temp, hum = _decode_dht22_edges(edges)
        self.assertAlmostEqual(temp, 24.6, places=1)
        self.assertAlmostEqual(hum, 68.0, places=1)

    def test_last_edge_missing_with_corrupt_checksum_raises(self):
        edges = _build_edges(23.4, 65.5, drop_last_edge=True, corrupt_checksum=True)
        with self.assertRaises(ValueError):
            _decode_dht22_edges(edges)

    def test_multiple_edges_missing_raises(self):
        edges = _build_edges(23.4, 65.5, drop_extra=3)
        with self.assertRaises(ValueError):
            _decode_dht22_edges(edges)


if __name__ == "__main__":
    unittest.main()
