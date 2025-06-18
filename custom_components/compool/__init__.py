"""The compool integration."""

from __future__ import annotations

from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import DOMAIN, PLATFORMS
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
            hass=hass, 
            config_entry=entry, 
            host=host, 
            port=port
        )
        
        # Perform initial refresh to verify connection
        await coordinator.async_config_entry_first_refresh()
        
        entry.runtime_data = CompoolRuntimeData(coordinator=coordinator)
        
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
        
        return True
    except Exception as ex:
        raise ConfigEntryNotReady(f"Unable to connect to pool controller at {host}:{port}") from ex


async def async_unload_entry(hass: HomeAssistant, entry: CompoolConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


