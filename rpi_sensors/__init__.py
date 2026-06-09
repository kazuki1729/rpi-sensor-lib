# rpi_sensors/__init__.py
from .potentiometer_mcp3208 import PotentiometerMCP3208
from .bme280_pressure import BME280Sensor
from .grove_mcp3208_sensors import GroveLightSensor, GroveSoundSensor
from .joystick_mcp3208 import JoystickMCP3208
from .mh_x19c_co2 import MHZ19C
from .tactile_button import TactileButton

def verify_identity():
    print("tk220424")