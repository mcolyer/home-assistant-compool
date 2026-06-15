"""Constants for Compool tests."""

from datetime import timedelta

from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.compool.const import (
    DOMAIN,
    RECONCILE_DELAY_SECONDS,
    WRITE_BATCH_INTERVAL_SECONDS,
)
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util


async def flush_writes(hass: HomeAssistant) -> None:
    """Advance time past the batch window so the queued write batch is sent."""
    async_fire_time_changed(
        hass, dt_util.utcnow() + timedelta(seconds=WRITE_BATCH_INTERVAL_SECONDS + 1)
    )
    await hass.async_block_till_done()


async def flush_reconcile(hass: HomeAssistant) -> None:
    """Advance time past the post-write reconcile delay so the re-poll fires."""
    async_fire_time_changed(
        hass, dt_util.utcnow() + timedelta(seconds=RECONCILE_DELAY_SECONDS + 1)
    )
    await hass.async_block_till_done()


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
    "pool_heat_source": 1,  # Pool heat mode code (int): 1 -> heater
    "spa_heat_source": 2,  # Spa heat mode code (int): 2 -> solar-priority
    "heater_on": True,  # Boolean: heater actively running
    "solar_on": False,
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
