"""Number platform for Compool pool controller."""

from __future__ import annotations

import logging

from homeassistant.components.number import (
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import TEMP_MAX_F, TEMP_MIN_F
from .coordinator import CompoolConfigEntry, CompoolStatusDataUpdateCoordinator
from .entity import CompoolEntity

_LOGGER = logging.getLogger(__name__)

COMPOOL_NUMBER_ENTITIES: tuple[NumberEntityDescription, ...] = (
    NumberEntityDescription(
        key="pool_target_temperature",
        translation_key="pool_target_temperature",
        native_min_value=TEMP_MIN_F,
        native_max_value=TEMP_MAX_F,
        native_step=1,
        native_unit_of_measurement=UnitOfTemperature.FAHRENHEIT,
        mode=NumberMode.SLIDER,
        icon="mdi:thermometer",
        name="Pool Target Temperature",
    ),
    NumberEntityDescription(
        key="spa_target_temperature",
        translation_key="spa_target_temperature",
        native_min_value=TEMP_MIN_F,
        native_max_value=TEMP_MAX_F,
        native_step=1,
        native_unit_of_measurement=UnitOfTemperature.FAHRENHEIT,
        mode=NumberMode.SLIDER,
        icon="mdi:thermometer",
        name="Spa Target Temperature",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: CompoolConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Compool number entities."""
    coordinator = config_entry.runtime_data.coordinator
    device_name = "Pool Controller"

    entities = []
    for description in COMPOOL_NUMBER_ENTITIES:
        if description.key == "pool_target_temperature":
            entities.append(
                CompoolPoolTargetTemperatureNumber(
                    coordinator, description, device_name
                )
            )
        elif description.key == "spa_target_temperature":
            entities.append(
                CompoolSpaTargetTemperatureNumber(coordinator, description, device_name)
            )

    async_add_entities(entities)


class CompoolPoolTargetTemperatureNumber(CompoolEntity, NumberEntity):
    """Pool target temperature number entity."""

    def __init__(
        self,
        coordinator: CompoolStatusDataUpdateCoordinator,
        description: NumberEntityDescription,
        device_name: str,
    ) -> None:
        """Initialize the pool target temperature number."""
        super().__init__(coordinator, description, device_name)

    @property
    def native_value(self) -> float | None:
        """Return the current pool target temperature."""
        if self.coordinator.data is None:
            return None
        # Default to 80°F if desired temperature not available
        return self.coordinator.data.get("desired_pool_temp_f", 80.0)

    async def async_set_native_value(self, value: float) -> None:
        """Set pool target temperature."""
        success = await self.coordinator.async_set_pool_temperature(value, "f")
        if success:
            # Trigger a coordinator update to refresh data
            await self.coordinator.async_request_refresh()
        else:
            _LOGGER.error("Failed to set pool target temperature to %s°F", value)


class CompoolSpaTargetTemperatureNumber(CompoolEntity, NumberEntity):
    """Spa target temperature number entity."""

    def __init__(
        self,
        coordinator: CompoolStatusDataUpdateCoordinator,
        description: NumberEntityDescription,
        device_name: str,
    ) -> None:
        """Initialize the spa target temperature number."""
        super().__init__(coordinator, description, device_name)

    @property
    def native_value(self) -> float | None:
        """Return the current spa target temperature."""
        if self.coordinator.data is None:
            return None
        # Default to 104°F if desired temperature not available
        return self.coordinator.data.get("desired_spa_temp_f", 104.0)

    async def async_set_native_value(self, value: float) -> None:
        """Set spa target temperature."""
        success = await self.coordinator.async_set_spa_temperature(value, "f")
        if success:
            # Trigger a coordinator update to refresh data
            await self.coordinator.async_request_refresh()
        else:
            _LOGGER.error("Failed to set spa target temperature to %s°F", value)
