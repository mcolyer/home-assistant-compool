"""The Compool component."""

from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.const import Platform

DOMAIN = "compool"

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.SENSOR,
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
KEY_FIRMWARE = "firmware"
KEY_TIME = "time"
KEY_POOL_WATER_TEMP = "pool_water_temp_f"
KEY_SPA_WATER_TEMP = "spa_water_temp_f"
KEY_SPA_SOLAR_TEMP = "spa_solar_temp_f"
KEY_POOL_AIR_TEMP = "pool_air_temp_f"
KEY_SOLAR_COLLECTOR_TEMP = "solar_collector_temp_f"
KEY_ACTIVE_HEAT_SOURCE = "active_heat_source"
KEY_HEAT_DELAY_ACTIVE = "heat_delay_active"
KEY_FREEZE_PROTECTION_ACTIVE = "freeze_protection_active"
KEY_AIR_SENSOR_FAULT = "air_sensor_fault"
KEY_SOLAR_SENSOR_FAULT = "solar_sensor_fault"
KEY_WATER_SENSOR_FAULT = "water_sensor_fault"
KEY_SOLAR_PRESENT = "solar_present"
