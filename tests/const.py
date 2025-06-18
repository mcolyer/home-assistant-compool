"""Constants for Compool tests."""

MOCK_CONFIG = {"host": "192.168.1.100", "port": 8899}

MOCK_POOL_STATUS = {
    "version": 23,  # Firmware version as integer
    "time": "15:30",  # Time as HH:MM string
    "pool_water_temp_f": 82.5,
    "spa_water_temp_f": 104.2,
    "spa_solar_temp": 78.1,  # No _f suffix for spa solar
    "air_temp_f": 75.8,
    "pool_solar_temp_f": 95.3,  # This is the solar collector temp
    "heater_on": False,
    "solar_on": True,
    "active_heat_source": "solar",  # Will be computed by coordinator
    "heat_delay_active": False,
    "freeze_protection_active": False,
    "air_sensor_fault": False,
    "solar_sensor_fault": False,
    "water_sensor_fault": False,
    "solar_present": True,
}
