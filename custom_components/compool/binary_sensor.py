"""Compool binary sensors."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import (
    KEY_AIR_SENSOR_FAULT,
    KEY_FREEZE_PROTECTION_ACTIVE,
    KEY_HEAT_DELAY_ACTIVE,
    KEY_SOLAR_PRESENT,
    KEY_SOLAR_SENSOR_FAULT,
    KEY_WATER_SENSOR_FAULT,
)
from .coordinator import CompoolConfigEntry
from .entity import CompoolEntity

COMPOOL_BINARY_SENSORS: tuple[BinarySensorEntityDescription, ...] = (
    BinarySensorEntityDescription(
        key="heat_delay_active",
        translation_key="heat_delay_active",
        icon="mdi:timer-sand",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    BinarySensorEntityDescription(
        key="freeze_protection_active",
        translation_key="freeze_protection_active",
        icon="mdi:snowflake-alert",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    BinarySensorEntityDescription(
        key="air_sensor_fault",
        translation_key="air_sensor_fault",
        device_class=BinarySensorDeviceClass.PROBLEM,
        icon="mdi:thermometer-alert",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    BinarySensorEntityDescription(
        key="solar_sensor_fault",
        translation_key="solar_sensor_fault",
        device_class=BinarySensorDeviceClass.PROBLEM,
        icon="mdi:solar-panel-large",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    BinarySensorEntityDescription(
        key="water_sensor_fault",
        translation_key="water_sensor_fault",
        device_class=BinarySensorDeviceClass.PROBLEM,
        icon="mdi:water-alert",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    BinarySensorEntityDescription(
        key="solar_present",
        translation_key="solar_present",
        icon="mdi:solar-power",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: CompoolConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Compool binary sensors."""
    compool_domain_data = config_entry.runtime_data
    coordinator = compool_domain_data.coordinator

    device_name = f"Pool Controller {coordinator.host}:{coordinator.port}"

    entities: list[CompoolBinarySensor] = []

    for description in COMPOOL_BINARY_SENSORS:
        entities.append(
            CompoolBinarySensor(
                coordinator=coordinator,
                description=description,
                device_name=device_name,
            )
        )

    async_add_entities(entities)


class CompoolBinarySensor(CompoolEntity, BinarySensorEntity):
    """Binary sensor for Compool pool controller."""

    @property
    def is_on(self) -> bool:
        """Return the state of the binary sensor."""
        if not self.coordinator.data:
            return False

        sensor_key = self.entity_description.key
        status = self.coordinator.data

        if sensor_key == "heat_delay_active":
            return status.get(KEY_HEAT_DELAY_ACTIVE, False)
        elif sensor_key == "freeze_protection_active":
            return status.get(KEY_FREEZE_PROTECTION_ACTIVE, False)
        elif sensor_key == "air_sensor_fault":
            return status.get(KEY_AIR_SENSOR_FAULT, False)
        elif sensor_key == "solar_sensor_fault":
            return status.get(KEY_SOLAR_SENSOR_FAULT, False)
        elif sensor_key == "water_sensor_fault":
            return status.get(KEY_WATER_SENSOR_FAULT, False)
        elif sensor_key == "solar_present":
            return status.get(KEY_SOLAR_PRESENT, False)

        return False
