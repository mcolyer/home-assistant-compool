"""Select platform for Compool pool controller."""

from __future__ import annotations

import logging

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import HEATER_MODES
from .coordinator import CompoolConfigEntry, CompoolStatusDataUpdateCoordinator
from .entity import CompoolEntity

_LOGGER = logging.getLogger(__name__)

COMPOOL_SELECT_ENTITIES: tuple[SelectEntityDescription, ...] = (
    SelectEntityDescription(
        key="pool_heater_mode",
        translation_key="pool_heater_mode",
        options=HEATER_MODES,
        icon="mdi:fire",
        name="Pool Heater Mode",
    ),
    SelectEntityDescription(
        key="spa_heater_mode",
        translation_key="spa_heater_mode",
        options=HEATER_MODES,
        icon="mdi:fire",
        name="Spa Heater Mode",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: CompoolConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Compool select entities."""
    coordinator = config_entry.runtime_data.coordinator
    device_name = "Pool Controller"

    entities = []
    for description in COMPOOL_SELECT_ENTITIES:
        if description.key == "pool_heater_mode":
            entities.append(
                CompoolPoolHeaterModeSelect(coordinator, description, device_name)
            )
        elif description.key == "spa_heater_mode":
            entities.append(
                CompoolSpaHeaterModeSelect(coordinator, description, device_name)
            )

    async_add_entities(entities)


class CompoolPoolHeaterModeSelect(CompoolEntity, SelectEntity):
    """Pool heater mode select entity."""

    def __init__(
        self,
        coordinator: CompoolStatusDataUpdateCoordinator,
        description: SelectEntityDescription,
        device_name: str,
    ) -> None:
        """Initialize the pool heater mode select."""
        super().__init__(coordinator, description, device_name)

    @property
    def current_option(self) -> str | None:
        """Return the current pool heater mode."""
        if self.coordinator.data is None:
            return None

        # Read heat source configuration directly from status data
        return self.coordinator.data.get("heat_source")

    async def async_select_option(self, option: str) -> None:
        """Set pool heater mode."""
        success = await self.coordinator.async_set_heater_mode(option, "pool")
        if success:
            # Trigger a coordinator update to refresh data
            await self.coordinator.async_request_refresh()
        else:
            _LOGGER.error("Failed to set pool heater mode to %s", option)


class CompoolSpaHeaterModeSelect(CompoolEntity, SelectEntity):
    """Spa heater mode select entity."""

    def __init__(
        self,
        coordinator: CompoolStatusDataUpdateCoordinator,
        description: SelectEntityDescription,
        device_name: str,
    ) -> None:
        """Initialize the spa heater mode select."""
        super().__init__(coordinator, description, device_name)

    @property
    def current_option(self) -> str | None:
        """Return the current spa heater mode."""
        if self.coordinator.data is None:
            return None

        # Read spa heat source configuration directly from status data
        return self.coordinator.data.get("spa_heat_source")

    async def async_select_option(self, option: str) -> None:
        """Set spa heater mode."""
        success = await self.coordinator.async_set_heater_mode(option, "spa")
        if success:
            # Trigger a coordinator update to refresh data
            await self.coordinator.async_request_refresh()
        else:
            _LOGGER.error("Failed to set spa heater mode to %s", option)
