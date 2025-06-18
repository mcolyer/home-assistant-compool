#!/usr/bin/env python3
"""Debug script to see actual entity IDs."""

import asyncio
from pytest_homeassistant_custom_component.common import MockConfigEntry
from custom_components.compool.const import DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from tests.const import MOCK_CONFIG
from tests.conftest import bypass_get_data

async def debug_entity_ids():
    """Debug entity ID generation."""
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_registry import async_get
    
    hass = HomeAssistant()
    await hass.async_start()
    
    # Mock the data
    bypass_get_data(hass)
    
    # Setup the integration
    config_entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG)
    config_entry.add_to_hass(hass)
    
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    
    # Get all entities
    all_states = hass.states.async_all()
    binary_sensors = [s for s in all_states if s.entity_id.startswith("binary_sensor.")]
    sensors = [s for s in all_states if s.entity_id.startswith("sensor.")]
    
    print("Binary sensors:")
    for s in binary_sensors:
        print(f"  {s.entity_id} -> {s.attributes.get('friendly_name', 'No name')}")
    
    print("\nSensors:")
    for s in sensors:
        print(f"  {s.entity_id} -> {s.attributes.get('friendly_name', 'No name')}")
    
    await hass.async_stop()

if __name__ == "__main__":
    asyncio.run(debug_entity_ids())