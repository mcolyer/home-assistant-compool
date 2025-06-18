"""Platform for shared base classes for sensors."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import CompoolStatusDataUpdateCoordinator


class CompoolEntity(CoordinatorEntity[CompoolStatusDataUpdateCoordinator]):
    """Base entity class for Compool pool controller."""

    _attr_attribution = "Data provided by Compool pool controller"
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: CompoolStatusDataUpdateCoordinator,
        description: EntityDescription,
        device_name: str,
    ) -> None:
        """Class initializer."""
        super().__init__(coordinator)
        self.entity_description = description

        # Create a comprehensive unique ID
        self._attr_unique_id = f"{DOMAIN}_{coordinator.host}_{coordinator.port}_{description.key}"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{coordinator.host}:{coordinator.port}")},
            manufacturer="Compool",
            model="Pool Controller",
            name=device_name,
            configuration_url=f"http://{coordinator.host}",
        )

    async def async_added_to_hass(self) -> None:
        """Request an update when added."""
        await super().async_added_to_hass()
        # We do not ask for an update with async_add_entities()
        # because it will update disabled entities
        await self.coordinator.async_request_refresh()
