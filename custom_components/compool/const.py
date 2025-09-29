"""The Compool component."""

from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.const import Platform

DOMAIN = "compool"

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
]

DEFAULT_NAME = "Compool Pool Controller"

# Compool local polling - check every 30 seconds
STATUS_SCAN_INTERVAL = timedelta(seconds=30)

_LOGGER = logging.getLogger(__package__)

# Configuration keys
CONF_HOST = "host"
CONF_PORT = "port"
DEFAULT_PORT = 8899

# Pool controller status data keys
KEY_FIRMWARE = "version"
KEY_TIME = "time"
KEY_POOL_WATER_TEMP = "pool_water_temp_f"
KEY_SPA_WATER_TEMP = "spa_water_temp_f"
KEY_SPA_SOLAR_TEMP = "spa_solar_temp"  # Note: no _f suffix in pycompool
KEY_POOL_AIR_TEMP = "air_temp_f"
KEY_SOLAR_COLLECTOR_TEMP = "pool_solar_temp_f"  # This is the solar collector temp
KEY_HEAT_SOURCE = (
    "heat_source"  # Pool heat mode: 'heater', 'solar-priority', 'solar-only', 'off'
)
KEY_SPA_HEAT_SOURCE = (
    "spa_heat_source"  # Spa heat mode: 'heater', 'solar-priority', 'solar-only', 'off'
)
KEY_HEATER_ON = "heater_on"  # Boolean: whether heater is actively running
KEY_HEAT_DELAY_ACTIVE = "heat_delay_active"
KEY_FREEZE_PROTECTION_ACTIVE = "freeze_protection_active"
KEY_AIR_SENSOR_FAULT = "air_sensor_fault"
KEY_SOLAR_SENSOR_FAULT = "solar_sensor_fault"
KEY_WATER_SENSOR_FAULT = "water_sensor_fault"
KEY_SOLAR_PRESENT = "solar_present"

# Auxiliary equipment status keys
KEY_AUX1_ON = "aux1_on"
KEY_AUX2_ON = "aux2_on"
KEY_AUX3_ON = "aux3_on"
KEY_AUX4_ON = "aux4_on"
KEY_AUX5_ON = "aux5_on"
KEY_AUX6_ON = "aux6_on"
KEY_AUX7_ON = "aux7_on"
KEY_AUX8_ON = "aux8_on"

# Service names
SERVICE_SET_POOL_TEMPERATURE = "set_pool_temperature"
SERVICE_SET_SPA_TEMPERATURE = "set_spa_temperature"
SERVICE_SET_HEATER_MODE = "set_heater_mode"

# Service field names
ATTR_TEMPERATURE = "temperature"
ATTR_UNIT = "unit"
ATTR_MODE = "mode"
ATTR_TARGET = "target"

# Valid heater modes
HEATER_MODES = ["off", "heater", "solar-priority", "solar-only"]

# Valid targets
TARGETS = ["pool", "spa"]

# Temperature ranges
TEMP_MIN_F = 50
TEMP_MAX_F = 104
TEMP_MIN_C = 10
TEMP_MAX_C = 40
