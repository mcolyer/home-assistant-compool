"""Select platform for Compool pool controller."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import HEATER_MODES, KEY_POOL_HEAT_SOURCE, KEY_SPA_HEAT_SOURCE
from .coordinator import CompoolConfigEntry, CompoolStatusDataUpdateCoordinator
from .entity import CompoolEntity

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

        # Read normalized heat source configuration from status data
        return self.coordinator.data.get(KEY_POOL_HEAT_SOURCE)

    async def async_select_option(self, option: str) -> None:
        """Set pool heater mode."""
        await self.coordinator.async_set_heater_mode(option, "pool")


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

        # Read normalized spa heat source configuration from status data
        return self.coordinator.data.get(KEY_SPA_HEAT_SOURCE)

    async def async_select_option(self, option: str) -> None:
        """Set spa heater mode."""
        await self.coordinator.async_set_heater_mode(option, "spa")
