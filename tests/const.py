"""Constants for Compool tests."""

MOCK_CONFIG = {"host": "192.168.1.100", "port": 8899}

MOCK_POOL_STATUS = {
    "firmware": "v2.1.3",
    "time": "2025-06-18T15:30:00Z",
    "pool_water_temp_f": 82.5,
    "spa_water_temp_f": 104.2,
    "spa_solar_temp_f": 78.1,
    "pool_air_temp_f": 75.8,
    "solar_collector_temp_f": 95.3,
    "active_heat_source": "solar",
    "heat_delay_active": False,
    "freeze_protection_active": False,
    "air_sensor_fault": False,
    "solar_sensor_fault": False,
    "water_sensor_fault": False,
    "solar_present": True,
}
