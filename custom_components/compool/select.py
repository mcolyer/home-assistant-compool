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

        # Extract heat source configuration from status data
        # This would need to be added to the coordinator's _enhance_status_data method
        # For now, we'll determine from the boolean flags
        status = self.coordinator.data

        # Check if pool heater/solar are on to determine current mode
        heater_on = status.get("heater_on", False)
        solar_on = status.get("solar_on", False)

        if not heater_on and not solar_on:
            return "off"
        elif heater_on and solar_on:
            return "solar-priority"  # Both are active
        elif heater_on:
            return "heater"
        elif solar_on:
            return "solar-only"
        else:
            return "off"

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

        # Extract spa heat source configuration from status data
        # This would need to be enhanced based on the actual pycompool data structure
        # For 3830 systems, spa heater and solar status are in separate bits
        status = self.coordinator.data

        # Check spa-specific heater/solar status (for 3830 systems)
        # These fields may need to be added to the coordinator's data parsing
        spa_heater_on = status.get("spa_heater_on", False)
        spa_solar_on = status.get("spa_solar_on", False)

        if not spa_heater_on and not spa_solar_on:
            return "off"
        elif spa_heater_on and spa_solar_on:
            return "solar-priority"  # Both are active
        elif spa_heater_on:
            return "heater"
        elif spa_solar_on:
            return "solar-only"
        else:
            return "off"

    async def async_select_option(self, option: str) -> None:
        """Set spa heater mode."""
        success = await self.coordinator.async_set_heater_mode(option, "spa")
        if success:
            # Trigger a coordinator update to refresh data
            await self.coordinator.async_request_refresh()
        else:
            _LOGGER.error("Failed to set spa heater mode to %s", option)
