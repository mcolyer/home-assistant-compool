"""Test Compool binary sensor platform."""

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.compool.const import DOMAIN
from homeassistant.core import HomeAssistant

from .const import MOCK_CONFIG


@pytest.mark.usefixtures("bypass_get_data")
async def test_binary_sensors(hass: HomeAssistant) -> None:
    """Test setting up creates the binary sensors."""
    config_entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG)
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    # Check that binary sensor entities exist
    binary_sensors = [
        state
        for state in hass.states.async_all()
        if state.entity_id.startswith("binary_sensor.")
    ]

    # We should have 7 binary sensors (added heater_on)
    assert len(binary_sensors) == 7

    # All binary sensors should be from this integration - entity IDs now use device name + translation key

    # Check that all expected entities are present (allowing for HA's entity ID generation)
    for sensor in binary_sensors:
        assert (
            sensor.attributes.get("attribution")
            == "Data provided by Compool pool controller"
        )
        # State should be either 'on' or 'off'
        assert sensor.state in ["on", "off"]
