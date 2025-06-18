"""Test Compool sensor platform."""

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.compool.const import DOMAIN
from homeassistant.core import HomeAssistant

from .const import MOCK_CONFIG


@pytest.mark.usefixtures("bypass_get_data")
async def test_sensors(hass: HomeAssistant) -> None:
    """Test setting up creates the sensors."""
    config_entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG)
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    # Check that sensor entities exist
    sensors = [
        state
        for state in hass.states.async_all()
        if state.entity_id.startswith("sensor.")
    ]

    # We should have 8 sensors
    assert len(sensors) == 8

    # All sensors should be from this integration
    for sensor in sensors:
        assert sensor.entity_id.startswith("sensor.pool_controller_192_168_1_100_8899")
        assert (
            sensor.attributes.get("attribution")
            == "Data provided by Compool pool controller"
        )
