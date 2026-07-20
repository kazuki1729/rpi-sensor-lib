import os
import sys
import types
import unittest
from unittest.mock import patch

from rpi_sensors import BME280InitializationError, BME280Sensor


class FakeBus:
    instances = []
    open_failures = 0

    def __init__(self, port):
        if FakeBus.open_failures:
            FakeBus.open_failures -= 1
            raise OSError("temporary I2C error")
        self.port = port
        self.close_count = 0
        FakeBus.instances.append(self)

    def close(self):
        self.close_count += 1


class FakeBme280Module(types.ModuleType):
    def __init__(self):
        super().__init__("bme280")
        self.calibration_failures = 0
        self.sample_failures = 0

    def load_calibration_params(self, bus, address):
        if self.calibration_failures:
            self.calibration_failures -= 1
            raise OSError("calibration unavailable")
        return {"address": address}

    def sample(self, bus, address, calibration):
        if self.sample_failures:
            self.sample_failures -= 1
            raise OSError("sample failed")
        return types.SimpleNamespace(
            temperature=23.5,
            humidity=48.0,
            pressure=1008.2,
        )


class Bme280Test(unittest.TestCase):
    def setUp(self):
        FakeBus.instances.clear()
        FakeBus.open_failures = 0
        self.bme280_module = FakeBme280Module()
        smbus_module = types.ModuleType("smbus2")
        smbus_module.SMBus = FakeBus
        self.modules_patch = patch.dict(
            sys.modules,
            {"bme280": self.bme280_module, "smbus2": smbus_module},
        )
        self.env_patch = patch.dict(os.environ, {"RPI_SENSOR_BACKEND": "direct"})
        self.modules_patch.start()
        self.env_patch.start()

    def tearDown(self):
        self.env_patch.stop()
        self.modules_patch.stop()

    def test_bus_open_failure_does_not_break_constructor(self):
        FakeBus.open_failures = 1
        sensor = BME280Sensor()
        self.assertEqual(sensor.read(), (23.5, 48.0, 1008.2))
        sensor.close()

    def test_calibration_failure_is_retried_on_read(self):
        self.bme280_module.calibration_failures = 1
        sensor = BME280Sensor()
        self.assertEqual(sensor.read(), (23.5, 48.0, 1008.2))
        self.assertEqual(len(FakeBus.instances), 2)
        sensor.close()
        sensor.close()

    def test_repeated_initialization_failure_has_cause(self):
        self.bme280_module.calibration_failures = 2
        sensor = BME280Sensor()
        with self.assertRaises(BME280InitializationError) as caught:
            sensor.read()
        self.assertIsInstance(caught.exception.__cause__, OSError)

    def test_sample_failure_forces_reinitialization(self):
        self.bme280_module.sample_failures = 1
        sensor = BME280Sensor()
        with self.assertRaises(OSError):
            sensor.read()
        self.assertEqual(sensor.read(), (23.5, 48.0, 1008.2))


if __name__ == "__main__":
    unittest.main()
