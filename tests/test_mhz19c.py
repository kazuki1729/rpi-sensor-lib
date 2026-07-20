import os
import sys
import types
import unittest
from unittest.mock import patch

from rpi_sensors import (
    MHZ19C,
    MHZ19CChecksumError,
    MHZ19CInitializationError,
    MHZ19CReadError,
)
from rpi_sensors.mh_x19c_co2 import _mhz19_checksum


class FakeSerialException(Exception):
    pass


class FakeSerial:
    response = b""
    fail_on_open = False
    instances = []

    def __init__(self, **kwargs):
        if self.fail_on_open:
            raise FakeSerialException("port unavailable")
        self.kwargs = kwargs
        self.is_open = True
        self.writes = []
        self.reset_count = 0
        self.close_count = 0
        FakeSerial.instances.append(self)

    def reset_input_buffer(self):
        self.reset_count += 1

    def write(self, data):
        self.writes.append(data)
        return len(data)

    def read(self, length):
        return self.response[:length]

    def close(self):
        self.is_open = False
        self.close_count += 1


def response_for(ppm):
    frame = bytearray([0xFF, 0x86, ppm >> 8, ppm & 0xFF, 0, 0, 0, 0, 0])
    frame[8] = _mhz19_checksum(bytes(frame))
    return bytes(frame)


class Mhz19cTest(unittest.TestCase):
    def setUp(self):
        FakeSerial.instances.clear()
        FakeSerial.fail_on_open = False
        FakeSerial.response = response_for(500)
        serial_module = types.ModuleType("serial")
        serial_module.Serial = FakeSerial
        serial_module.SerialException = FakeSerialException
        serial_module.EIGHTBITS = 8
        serial_module.PARITY_NONE = "N"
        serial_module.STOPBITS_ONE = 1
        self.modules_patch = patch.dict(sys.modules, {"serial": serial_module})
        self.env_patch = patch.dict(os.environ, {"RPI_SENSOR_BACKEND": "direct"})
        self.sleep_patch = patch("rpi_sensors.mh_x19c_co2.time.sleep")
        self.modules_patch.start()
        self.env_patch.start()
        self.sleep_patch.start()

    def tearDown(self):
        self.sleep_patch.stop()
        self.env_patch.stop()
        self.modules_patch.stop()

    def test_valid_response_returns_ppm_and_clears_stale_input(self):
        sensor = MHZ19C()
        self.assertEqual(sensor.read_co2(), 500)
        self.assertEqual(FakeSerial.instances[0].reset_count, 1)
        sensor.close()
        sensor.close()
        self.assertEqual(FakeSerial.instances[0].close_count, 1)

    def test_corrupt_checksum_is_rejected(self):
        corrupt = bytearray(response_for(500))
        corrupt[8] ^= 0x01
        FakeSerial.response = bytes(corrupt)
        with MHZ19C() as sensor:
            with self.assertRaises(MHZ19CChecksumError):
                sensor.read_co2()

    def test_partial_response_is_rejected(self):
        FakeSerial.response = response_for(500)[:5]
        with MHZ19C() as sensor:
            with self.assertRaises(MHZ19CReadError):
                sensor.read_co2()

    def test_serial_open_failure_is_explicit(self):
        FakeSerial.fail_on_open = True
        with self.assertRaises(MHZ19CInitializationError):
            MHZ19C()


if __name__ == "__main__":
    unittest.main()
