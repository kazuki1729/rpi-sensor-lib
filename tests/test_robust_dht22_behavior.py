import os
import unittest
from unittest.mock import Mock, patch

from rpi_sensors import DHT22ReadError, RobustDHT22


class RobustDht22BehaviorTest(unittest.TestCase):
    def test_configuration_is_validated_before_hardware_access(self):
        with self.assertRaises(ValueError):
            RobustDHT22(max_retries=0)
        with self.assertRaises(ValueError):
            RobustDHT22(read_interval=1.9)

    def test_final_error_keeps_low_level_cause(self):
        client = Mock()
        with patch.dict(os.environ, {"RPI_SENSOR_BACKEND": "pi4gpio"}):
            with patch(
                "rpi_sensors.robust_dht22._pi4gpio_backend.get_pi4gpio_client",
                return_value=client,
            ):
                sensor = RobustDHT22(max_retries=2)
        sensor._read_raw = Mock(side_effect=ValueError("CRC error"))
        with patch("rpi_sensors.robust_dht22.time.sleep"):
            with self.assertRaises(DHT22ReadError) as caught:
                sensor.read()
        self.assertIsInstance(caught.exception.__cause__, ValueError)
        sensor.close()
        sensor.close()
        client.gpio_release.assert_called_once_with(26)

    def test_cache_uses_monotonic_elapsed_time(self):
        client = Mock()
        with patch.dict(os.environ, {"RPI_SENSOR_BACKEND": "pi4gpio"}):
            with patch(
                "rpi_sensors.robust_dht22._pi4gpio_backend.get_pi4gpio_client",
                return_value=client,
            ):
                sensor = RobustDHT22()
        sensor._read_raw = Mock(return_value=(22.0, 50.0))
        with patch(
            "rpi_sensors.robust_dht22.time.monotonic",
            side_effect=[100.0, 100.0, 101.0],
        ):
            self.assertEqual(sensor.read(), (22.0, 50.0))
            self.assertEqual(sensor.read(), (22.0, 50.0))
        sensor._read_raw.assert_called_once()
        sensor.close()


if __name__ == "__main__":
    unittest.main()
