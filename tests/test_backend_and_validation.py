import os
import unittest
from unittest.mock import patch

from rpi_sensors import _pi4gpio_backend
from rpi_sensors._validation import (
    require_int_range,
    require_non_negative_int,
    require_non_negative_number,
    require_positive_number,
)


class BackendSelectionTest(unittest.TestCase):
    def test_backend_defaults_to_direct(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(_pi4gpio_backend.get_backend(), "direct")

    def test_backend_is_normalized(self):
        with patch.dict(os.environ, {"RPI_SENSOR_BACKEND": " Pi4GPIO "}):
            self.assertEqual(_pi4gpio_backend.get_backend(), "pi4gpio")

    def test_unknown_backend_is_rejected(self):
        with patch.dict(os.environ, {"RPI_SENSOR_BACKEND": "automatic"}):
            with self.assertRaises(ValueError):
                _pi4gpio_backend.get_backend()


class ValidationTest(unittest.TestCase):
    def test_integer_range_rejects_bool_and_out_of_range(self):
        with self.assertRaises(TypeError):
            require_int_range("channel", True, 0, 7)
        with self.assertRaises(ValueError):
            require_int_range("channel", 8, 0, 7)

    def test_numeric_guards(self):
        self.assertEqual(require_non_negative_int("pin", 0), 0)
        self.assertEqual(require_positive_number("vref", 3.3), 3.3)
        self.assertEqual(require_non_negative_number("interval", 0), 0.0)
        with self.assertRaises(ValueError):
            require_non_negative_int("pin", -1)
        with self.assertRaises(ValueError):
            require_positive_number("vref", 0)
        with self.assertRaises(ValueError):
            require_non_negative_number("interval", -0.1)


if __name__ == "__main__":
    unittest.main()
