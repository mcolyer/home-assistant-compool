"""The compool integration."""

from __future__ import annotations

import voluptuous as vol

from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryNotReady

from .const import (
    ATTR_MODE,
    ATTR_TARGET,
    ATTR_TEMPERATURE,
    ATTR_UNIT,
    DOMAIN,
    HEATER_MODES,
    PLATFORMS,
    SERVICE_SET_HEATER_MODE,
    SERVICE_SET_POOL_TEMPERATURE,
    SERVICE_SET_SPA_TEMPERATURE,
    TARGETS,
    TEMP_MAX_F,
    TEMP_MIN_F,
)
from .coordinator import (
    CompoolConfigEntry,
    CompoolRuntimeData,
    CompoolStatusDataUpdateCoordinator,
)


async def async_setup_entry(hass: HomeAssistant, entry: CompoolConfigEntry) -> bool:
    """Set up compool from a config entry."""

    config = entry.data
    host = config[CONF_HOST]
    port = config[CONF_PORT]

    try:
        coordinator = CompoolStatusDataUpdateCoordinator(
            hass=hass, config_entry=entry, host=host, port=port
        )

        # Perform initial refresh to verify connection
        await coordinator.async_config_entry_first_refresh()

        entry.runtime_data = CompoolRuntimeData(coordinator=coordinator)

        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

        # Register services
        async_register_services(hass, coordinator)
    except Exception as ex:
        raise ConfigEntryNotReady(
            f"Unable to connect to pool controller at {host}:{port}"
        ) from ex
    else:
        return True


async def async_unload_entry(hass: HomeAssistant, entry: CompoolConfigEntry) -> bool:
    """Unload a config entry."""
    # Unregister services
    async_unregister_services(hass)

    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


def async_register_services(
    hass: HomeAssistant, coordinator: CompoolStatusDataUpdateCoordinator
) -> None:
    """Register Compool services."""

    # Service schemas
    set_temperature_schema = vol.Schema(
        {
            vol.Required(ATTR_TEMPERATURE): vol.All(
                vol.Coerce(float), vol.Range(min=TEMP_MIN_F, max=TEMP_MAX_F)
            ),
            vol.Optional(ATTR_UNIT, default="f"): vol.In(["f", "c"]),
        }
    )

    set_heater_mode_schema = vol.Schema(
        {
            vol.Required(ATTR_MODE): vol.In(HEATER_MODES),
            vol.Required(ATTR_TARGET): vol.In(TARGETS),
        }
    )

    async def async_set_pool_temperature(call: ServiceCall) -> None:
        """Handle set pool temperature service call."""
        temperature = call.data[ATTR_TEMPERATURE]
        unit = call.data[ATTR_UNIT]
        await coordinator.async_set_pool_temperature(temperature, unit)

    async def async_set_spa_temperature(call: ServiceCall) -> None:
        """Handle set spa temperature service call."""
        temperature = call.data[ATTR_TEMPERATURE]
        unit = call.data[ATTR_UNIT]
        await coordinator.async_set_spa_temperature(temperature, unit)

    async def async_set_heater_mode(call: ServiceCall) -> None:
        """Handle set heater mode service call."""
        mode = call.data[ATTR_MODE]
        target = call.data[ATTR_TARGET]
        await coordinator.async_set_heater_mode(mode, target)

    # Register services
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_POOL_TEMPERATURE,
        async_set_pool_temperature,
        schema=set_temperature_schema,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_SPA_TEMPERATURE,
        async_set_spa_temperature,
        schema=set_temperature_schema,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_HEATER_MODE,
        async_set_heater_mode,
        schema=set_heater_mode_schema,
    )


def async_unregister_services(hass: HomeAssistant) -> None:
    """Unregister Compool services."""
    hass.services.async_remove(DOMAIN, SERVICE_SET_POOL_TEMPERATURE)
    hass.services.async_remove(DOMAIN, SERVICE_SET_SPA_TEMPERATURE)
    hass.services.async_remove(DOMAIN, SERVICE_SET_HEATER_MODE)
