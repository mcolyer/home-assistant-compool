"""Test the Compool services."""

from unittest.mock import patch

from custom_components.compool.const import (
    ATTR_MODE,
    ATTR_TARGET,
    ATTR_TEMPERATURE,
    ATTR_UNIT,
    DOMAIN,
    SERVICE_SET_HEATER_MODE,
    SERVICE_SET_POOL_TEMPERATURE,
    SERVICE_SET_SPA_TEMPERATURE,
)
from homeassistant.core import HomeAssistant

from .const import MOCK_CONFIG_ENTRY


async def test_set_pool_temperature_service(
    hass: HomeAssistant, bypass_get_data
) -> None:
    """Test set pool temperature service."""
    entry = MOCK_CONFIG_ENTRY
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    with patch(
        "custom_components.compool.coordinator.PoolController.set_pool_temperature",
        return_value=True,
    ) as mock_set_temp:
        await hass.services.async_call(
            DOMAIN,
            SERVICE_SET_POOL_TEMPERATURE,
            {
                ATTR_TEMPERATURE: 82,
                ATTR_UNIT: "f",
            },
            blocking=True,
        )

        mock_set_temp.assert_called_once_with("82f")


async def test_set_pool_temperature_service_celsius(
    hass: HomeAssistant, bypass_get_data
) -> None:
    """Test set pool temperature service with Celsius."""
    entry = MOCK_CONFIG_ENTRY
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    with patch(
        "custom_components.compool.coordinator.PoolController.set_pool_temperature",
        return_value=True,
    ) as mock_set_temp:
        await hass.services.async_call(
            DOMAIN,
            SERVICE_SET_POOL_TEMPERATURE,
            {
                ATTR_TEMPERATURE: 27.8,
                ATTR_UNIT: "c",
            },
            blocking=True,
        )

        mock_set_temp.assert_called_once_with("27.8c")


async def test_set_pool_temperature_service_default_unit(
    hass: HomeAssistant, bypass_get_data
) -> None:
    """Test set pool temperature service with default unit."""
    entry = MOCK_CONFIG_ENTRY
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    with patch(
        "custom_components.compool.coordinator.PoolController.set_pool_temperature",
        return_value=True,
    ) as mock_set_temp:
        await hass.services.async_call(
            DOMAIN,
            SERVICE_SET_POOL_TEMPERATURE,
            {
                ATTR_TEMPERATURE: 80,
            },
            blocking=True,
        )

        mock_set_temp.assert_called_once_with("80f")


async def test_set_spa_temperature_service(
    hass: HomeAssistant, bypass_get_data
) -> None:
    """Test set spa temperature service."""
    entry = MOCK_CONFIG_ENTRY
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    with patch(
        "custom_components.compool.coordinator.PoolController.set_spa_temperature",
        return_value=True,
    ) as mock_set_temp:
        await hass.services.async_call(
            DOMAIN,
            SERVICE_SET_SPA_TEMPERATURE,
            {
                ATTR_TEMPERATURE: 104,
                ATTR_UNIT: "f",
            },
            blocking=True,
        )

        mock_set_temp.assert_called_once_with("104f")


async def test_set_heater_mode_service(hass: HomeAssistant, bypass_get_data) -> None:
    """Test set heater mode service."""
    entry = MOCK_CONFIG_ENTRY
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    with patch(
        "custom_components.compool.coordinator.PoolController.set_heater_mode",
        return_value=True,
    ) as mock_set_mode:
        await hass.services.async_call(
            DOMAIN,
            SERVICE_SET_HEATER_MODE,
            {
                ATTR_MODE: "solar-priority",
                ATTR_TARGET: "pool",
            },
            blocking=True,
        )

        mock_set_mode.assert_called_once_with("solar-priority", "pool")


async def test_set_heater_mode_service_spa(
    hass: HomeAssistant, bypass_get_data
) -> None:
    """Test set heater mode service for spa."""
    entry = MOCK_CONFIG_ENTRY
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    with patch(
        "custom_components.compool.coordinator.PoolController.set_heater_mode",
        return_value=True,
    ) as mock_set_mode:
        await hass.services.async_call(
            DOMAIN,
            SERVICE_SET_HEATER_MODE,
            {
                ATTR_MODE: "heater",
                ATTR_TARGET: "spa",
            },
            blocking=True,
        )

        mock_set_mode.assert_called_once_with("heater", "spa")
