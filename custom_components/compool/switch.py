"""Switch for controlling auxiliary equipment from Compool."""

from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import (
    KEY_AUX1_ON,
    KEY_AUX2_ON,
    KEY_AUX3_ON,
    KEY_AUX4_ON,
    KEY_AUX5_ON,
    KEY_AUX6_ON,
    KEY_AUX7_ON,
    KEY_AUX8_ON,
)
from .coordinator import CompoolConfigEntry
from .entity import CompoolEntity

COMPOOL_SWITCHES: tuple[SwitchEntityDescription, ...] = (
    SwitchEntityDescription(
        key="aux1",
        translation_key="aux1",
        icon="mdi:pool",
    ),
    SwitchEntityDescription(
        key="aux2",
        translation_key="aux2",
        icon="mdi:lightbulb",
    ),
    SwitchEntityDescription(
        key="aux3",
        translation_key="aux3",
        icon="mdi:lightbulb",
    ),
    SwitchEntityDescription(
        key="aux4",
        translation_key="aux4",
        icon="mdi:lightbulb",
    ),
    SwitchEntityDescription(
        key="aux5",
        translation_key="aux5",
        icon="mdi:lightbulb",
    ),
    SwitchEntityDescription(
        key="aux6",
        translation_key="aux6",
        icon="mdi:lightbulb",
    ),
    SwitchEntityDescription(
        key="aux7",
        translation_key="aux7",
        icon="mdi:lightbulb",
    ),
    SwitchEntityDescription(
        key="aux8",
        translation_key="aux8",
        icon="mdi:lightbulb",
    ),
)

# Map switch keys to their corresponding status keys
AUX_KEY_MAPPING = {
    "aux1": KEY_AUX1_ON,
    "aux2": KEY_AUX2_ON,
    "aux3": KEY_AUX3_ON,
    "aux4": KEY_AUX4_ON,
    "aux5": KEY_AUX5_ON,
    "aux6": KEY_AUX6_ON,
    "aux7": KEY_AUX7_ON,
    "aux8": KEY_AUX8_ON,
}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: CompoolConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Compool switches."""

    compool_domain_data = config_entry.runtime_data
    coordinator = compool_domain_data.coordinator

    device_name = "Pool Controller"

    entities: list[CompoolSwitch] = []

    for description in COMPOOL_SWITCHES:
        entities.append(
            CompoolSwitch(
                coordinator=coordinator,
                description=description,
                device_name=device_name,
            )
        )

    async_add_entities(entities)


class CompoolSwitch(CompoolEntity, SwitchEntity):
    """Representation of a Compool auxiliary equipment switch."""

    @property
    def is_on(self) -> bool | None:
        """Return true if the switch is on."""
        if not self.coordinator.data:
            return None

        switch_key = self.entity_description.key
        status_key = AUX_KEY_MAPPING.get(switch_key)

        if status_key:
            return self.coordinator.data.get(status_key, False)

        return None

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        switch_key = self.entity_description.key
        aux_num = int(switch_key.replace("aux", ""))

        success = await self.coordinator.async_set_aux_equipment(aux_num, True)
        if success:
            # Request immediate coordinator refresh to update state
            await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        switch_key = self.entity_description.key
        aux_num = int(switch_key.replace("aux", ""))

        success = await self.coordinator.async_set_aux_equipment(aux_num, False)
        if success:
            # Request immediate coordinator refresh to update state
            await self.coordinator.async_request_refresh()

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return the state attributes."""
        if not self.coordinator.data:
            return None

        return {
            "host": self.coordinator.host,
            "port": self.coordinator.port,
            "last_updated": self.coordinator.last_update_success,
        }
