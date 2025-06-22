"""Test the Compool select platform."""

from unittest.mock import patch

from homeassistant.components.select import DOMAIN as SELECT_DOMAIN
from homeassistant.const import ATTR_ENTITY_ID, ATTR_OPTION
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .const import MOCK_CONFIG_ENTRY


async def test_select_setup(hass: HomeAssistant, bypass_get_data) -> None:
    """Test select platform setup."""
    entry = MOCK_CONFIG_ENTRY
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    entity_registry = er.async_get(hass)

    # Check pool heater mode select entity
    pool_heater_entity = entity_registry.async_get(
        f"{SELECT_DOMAIN}.pool_controller_pool_heater_mode"
    )
    assert pool_heater_entity is not None
    assert pool_heater_entity.unique_id == f"{entry.entry_id}_pool_heater_mode"

    # Check spa heater mode select entity
    spa_heater_entity = entity_registry.async_get(
        f"{SELECT_DOMAIN}.pool_controller_spa_heater_mode"
    )
    assert spa_heater_entity is not None
    assert spa_heater_entity.unique_id == f"{entry.entry_id}_spa_heater_mode"


async def test_pool_heater_mode_value(hass: HomeAssistant, bypass_get_data) -> None:
    """Test pool heater mode select entity value."""
    entry = MOCK_CONFIG_ENTRY
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get(f"{SELECT_DOMAIN}.pool_controller_pool_heater_mode")
    assert state is not None
    # Based on MOCK_POOL_STATUS heater_on=True, solar_on=False
    assert state.state == "heater"
    assert "off" in state.attributes["options"]
    assert "heater" in state.attributes["options"]
    assert "solar-priority" in state.attributes["options"]
    assert "solar-only" in state.attributes["options"]


async def test_spa_heater_mode_value(hass: HomeAssistant, bypass_get_data) -> None:
    """Test spa heater mode select entity value."""
    entry = MOCK_CONFIG_ENTRY
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get(f"{SELECT_DOMAIN}.pool_controller_spa_heater_mode")
    assert state is not None
    # Based on MOCK_POOL_STATUS spa_heater_on=False, spa_solar_on=False
    assert state.state == "off"


async def test_set_pool_heater_mode(hass: HomeAssistant, bypass_get_data) -> None:
    """Test setting pool heater mode."""
    entry = MOCK_CONFIG_ENTRY
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    with patch(
        "custom_components.compool.coordinator.PoolController.set_heater_mode",
        return_value=True,
    ) as mock_set_mode:
        await hass.services.async_call(
            SELECT_DOMAIN,
            "select_option",
            {
                ATTR_ENTITY_ID: f"{SELECT_DOMAIN}.pool_controller_pool_heater_mode",
                ATTR_OPTION: "solar-priority",
            },
            blocking=True,
        )

        mock_set_mode.assert_called_once_with("solar-priority", "pool")


async def test_set_spa_heater_mode(hass: HomeAssistant, bypass_get_data) -> None:
    """Test setting spa heater mode."""
    entry = MOCK_CONFIG_ENTRY
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    with patch(
        "custom_components.compool.coordinator.PoolController.set_heater_mode",
        return_value=True,
    ) as mock_set_mode:
        await hass.services.async_call(
            SELECT_DOMAIN,
            "select_option",
            {
                ATTR_ENTITY_ID: f"{SELECT_DOMAIN}.pool_controller_spa_heater_mode",
                ATTR_OPTION: "heater",
            },
            blocking=True,
        )

        mock_set_mode.assert_called_once_with("heater", "spa")
