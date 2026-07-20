import os
import sys
import types
import unittest
from unittest.mock import patch

from rpi_sensors import GroveLightSensor, JoystickMCP3208, PotentiometerMCP3208
from rpi_sensors import _spi_resource


class FakeSpiDev:
    instances = []

    def __init__(self):
        self.open_args = None
        self.max_speed_hz = None
        self.close_count = 0
        self.transfers = []
        FakeSpiDev.instances.append(self)

    def open(self, bus, device):
        self.open_args = (bus, device)

    def xfer2(self, data):
        self.transfers.append(list(data))
        return [0x00, 0x0A, 0xBC]

    def close(self):
        self.close_count += 1


class Mcp3208ResourceTest(unittest.TestCase):
    def setUp(self):
        FakeSpiDev.instances.clear()
        self.spidev_module = types.ModuleType("spidev")
        self.spidev_module.SpiDev = FakeSpiDev
        self.modules_patch = patch.dict(sys.modules, {"spidev": self.spidev_module})
        self.env_patch = patch.dict(os.environ, {"RPI_SENSOR_BACKEND": "direct"})
        self.modules_patch.start()
        self.env_patch.start()
        _spi_resource._reset_for_tests()

    def tearDown(self):
        _spi_resource._reset_for_tests()
        self.env_patch.stop()
        self.modules_patch.stop()

    def test_all_mcp3208_classes_share_one_connection(self):
        light = GroveLightSensor(channel=0)
        joystick = JoystickMCP3208()
        potentiometer = PotentiometerMCP3208(channel=2)

        self.assertEqual(len(FakeSpiDev.instances), 1)
        self.assertEqual(light.read_raw(), 0xABC)
        self.assertEqual(joystick.read_xy(0, 1), (0xABC, 0xABC))
        self.assertEqual(potentiometer.read_raw(), 0xABC)

        light.close()
        light.close()
        self.assertEqual(FakeSpiDev.instances[0].close_count, 0)
        self.assertEqual(potentiometer.read_raw(), 0xABC)
        joystick.close()
        potentiometer.close()
        self.assertEqual(FakeSpiDev.instances[0].close_count, 1)

    def test_different_bus_or_device_uses_different_connection(self):
        sensor0 = GroveLightSensor(channel=0, spi_bus=0, spi_device=0)
        sensor1 = GroveLightSensor(channel=1, spi_bus=0, spi_device=1)
        self.assertEqual(len(FakeSpiDev.instances), 2)
        self.assertEqual(FakeSpiDev.instances[0].open_args, (0, 0))
        self.assertEqual(FakeSpiDev.instances[1].open_args, (0, 1))
        sensor0.close()
        sensor1.close()

    def test_invalid_adc_configuration_fails_before_hardware_access(self):
        with self.assertRaises(ValueError):
            GroveLightSensor(channel=8)
        with self.assertRaises(ValueError):
            JoystickMCP3208(deadzone=2047)
        with self.assertRaises(ValueError):
            PotentiometerMCP3208(channel=0, interval_sec=-1)
        self.assertEqual(FakeSpiDev.instances, [])


if __name__ == "__main__":
    unittest.main()
