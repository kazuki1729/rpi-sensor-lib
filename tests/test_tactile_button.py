import os
import sys
import types
import unittest
from unittest.mock import patch

from rpi_sensors import TactileButton, TactileButtonInitializationError


class FakeLgpio(types.ModuleType):
    SET_PULL_UP = 1

    def __init__(self):
        super().__init__("lgpio")
        self.open_count = 0
        self.close_count = 0
        self.free_count = 0
        self.claim_failure = False

    def gpiochip_open(self, chip):
        self.open_count += 1
        return 100 + chip

    def gpiochip_close(self, handle):
        self.close_count += 1

    def gpio_claim_input(self, handle, pin, pull):
        if self.claim_failure:
            raise OSError("claim failed")

    def gpio_free(self, handle, pin):
        self.free_count += 1

    def gpio_read(self, handle, pin):
        return 1


class TactileButtonTest(unittest.TestCase):
    def setUp(self):
        self.lgpio = FakeLgpio()
        self.modules_patch = patch.dict(sys.modules, {"lgpio": self.lgpio})
        self.env_patch = patch.dict(os.environ, {"RPI_SENSOR_BACKEND": "direct"})
        self.modules_patch.start()
        self.env_patch.start()
        TactileButton._handle = None
        TactileButton._use_count = 0

    def tearDown(self):
        TactileButton._handle = None
        TactileButton._use_count = 0
        self.env_patch.stop()
        self.modules_patch.stop()

    def test_multiple_buttons_share_chip_and_close_idempotently(self):
        first = TactileButton(pin=17)
        second = TactileButton(pin=18)
        self.assertEqual(self.lgpio.open_count, 1)
        first.close()
        first.close()
        self.assertEqual(self.lgpio.close_count, 0)
        with self.assertRaises(RuntimeError):
            first.update()
        second.close()
        self.assertEqual(self.lgpio.close_count, 1)
        self.assertEqual(self.lgpio.free_count, 2)

    def test_claim_failure_closes_new_handle_and_raises(self):
        self.lgpio.claim_failure = True
        with self.assertRaises(TactileButtonInitializationError):
            TactileButton(pin=17)
        self.assertEqual(self.lgpio.close_count, 1)
        self.assertIsNone(TactileButton._handle)

    def test_invalid_configuration_is_rejected(self):
        with self.assertRaises(ValueError):
            TactileButton(pin=-1)
        with self.assertRaises(ValueError):
            TactileButton(pin=17, debounce_time=-0.1)


if __name__ == "__main__":
    unittest.main()
