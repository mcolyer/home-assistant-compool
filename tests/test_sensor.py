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

    # Check temperature sensors exist and have valid values
    temperature_sensors = [
        s for s in sensors if s.attributes.get("device_class") == "temperature"
    ]
    assert len(temperature_sensors) == 5, (
        f"Expected 5 temperature sensors, got {len(temperature_sensors)}"
    )

    # Check that temperature sensors have valid units and numeric values
    for temp_sensor in temperature_sensors:
        unit = temp_sensor.attributes.get("unit_of_measurement")
        state_value = temp_sensor.state

        # Temperature should be in either °F or °C (HA may convert based on system config)
        assert unit in ["°F", "°C"], (
            f"Expected °F or °C, got {unit} for {temp_sensor.entity_id}"
        )

        # State should be a valid temperature (not None, not 'unavailable')
        assert state_value not in [None, "unavailable", "unknown"], (
            f"Invalid state {state_value} for {temp_sensor.entity_id}"
        )

        # Temperature should be numeric (don't validate range due to test environment unit conversion)
        try:
            float(state_value)
        except (ValueError, TypeError):
            pytest.fail(
                f"Temperature value '{state_value}' is not numeric for {temp_sensor.entity_id}"
            )
