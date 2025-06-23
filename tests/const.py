"""Constants for Compool tests."""

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.compool.const import DOMAIN

MOCK_CONFIG = {"host": "192.168.1.100", "port": 8899}

MOCK_CONFIG_ENTRY = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG)

MOCK_POOL_STATUS = {
    "version": 23,  # Firmware version as integer
    "time": "15:30",  # Time as HH:MM string
    "pool_water_temp_f": 82.5,
    "spa_water_temp_f": 104.2,
    "spa_solar_temp": 78.1,  # No _f suffix for spa solar
    "air_temp_f": 75.8,
    "pool_solar_temp_f": 95.3,  # This is the solar collector temp
    "desired_pool_temp_f": 80.0,  # Target pool temperature
    "desired_spa_temp_f": 104.0,  # Target spa temperature
    "heater_on": True,
    "solar_on": False,
    "spa_heater_on": False,  # For spa heater mode select
    "spa_solar_on": False,  # For spa heater mode select
    "active_heat_source": "heater",  # Will be computed by coordinator
    "heat_delay_active": False,
    "freeze_protection_active": False,
    "air_sensor_fault": False,
    "solar_sensor_fault": False,
    "water_sensor_fault": False,
    "solar_present": True,
    # Auxiliary equipment status
    "aux1_on": True,
    "aux2_on": False,
    "aux3_on": True,
    "aux4_on": False,
    "aux5_on": False,
    "aux6_on": True,
    "aux7_on": False,
    "aux8_on": False,
}
