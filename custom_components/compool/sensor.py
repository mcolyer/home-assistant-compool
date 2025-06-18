"""Sensor for displaying pool controller data from Compool."""

from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.typing import StateType

from .const import (
    KEY_ACTIVE_HEAT_SOURCE,
    KEY_FIRMWARE,
    KEY_POOL_AIR_TEMP,
    KEY_POOL_WATER_TEMP,
    KEY_SOLAR_COLLECTOR_TEMP,
    KEY_SPA_SOLAR_TEMP,
    KEY_SPA_WATER_TEMP,
    KEY_TIME,
)
from .coordinator import CompoolConfigEntry
from .entity import CompoolEntity

COMPOOL_SENSORS: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(
        key="pool_controller_firmware",
        translation_key="pool_controller_firmware",
        icon="mdi:chip",
    ),
    SensorEntityDescription(
        key="pool_controller_time",
        translation_key="pool_controller_time",
        device_class=SensorDeviceClass.TIMESTAMP,
        icon="mdi:clock",
    ),
    SensorEntityDescription(
        key="pool_active_heat_source",
        translation_key="pool_active_heat_source",
        icon="mdi:fire",
    ),
    SensorEntityDescription(
        key="pool_water_temperature",
        translation_key="pool_water_temperature",
        suggested_display_precision=1,
        native_unit_of_measurement=UnitOfTemperature.FAHRENHEIT,
        device_class=SensorDeviceClass.TEMPERATURE,
        icon="mdi:pool-thermometer",
    ),
    SensorEntityDescription(
        key="spa_water_temperature",
        translation_key="spa_water_temperature",
        suggested_display_precision=1,
        native_unit_of_measurement=UnitOfTemperature.FAHRENHEIT,
        device_class=SensorDeviceClass.TEMPERATURE,
        icon="mdi:hot-tub",
    ),
    SensorEntityDescription(
        key="spa_solar_temperature",
        translation_key="spa_solar_temperature",
        suggested_display_precision=1,
        native_unit_of_measurement=UnitOfTemperature.FAHRENHEIT,
        device_class=SensorDeviceClass.TEMPERATURE,
        icon="mdi:solar-power-variant",
    ),
    SensorEntityDescription(
        key="pool_air_temperature",
        translation_key="pool_air_temperature",
        suggested_display_precision=1,
        native_unit_of_measurement=UnitOfTemperature.FAHRENHEIT,
        device_class=SensorDeviceClass.TEMPERATURE,
        icon="mdi:thermometer",
    ),
    SensorEntityDescription(
        key="solar_collector_temperature",
        translation_key="solar_collector_temperature",
        suggested_display_precision=1,
        native_unit_of_measurement=UnitOfTemperature.FAHRENHEIT,
        device_class=SensorDeviceClass.TEMPERATURE,
        icon="mdi:solar-panel",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: CompoolConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Compool sensors."""

    compool_domain_data = config_entry.runtime_data
    coordinator = compool_domain_data.coordinator

    device_name = "Pool Controller"

    entities: list[CompoolSensor] = []

    for description in COMPOOL_SENSORS:
        entities.append(
            CompoolSensor(
                coordinator=coordinator,
                description=description,
                device_name=device_name,
            )
        )

    async_add_entities(entities)


class CompoolSensor(CompoolEntity, SensorEntity):
    """Representation of a Compool pool controller sensor."""

    @property
    def native_value(self) -> StateType:
        """Return the state of the sensor."""
        if not self.coordinator.data:
            return None

        sensor_key = self.entity_description.key
        status = self.coordinator.data

        if sensor_key == "pool_controller_firmware":
            return status.get(KEY_FIRMWARE)
        elif sensor_key == "pool_controller_time":
            return status.get(KEY_TIME)
        elif sensor_key == "pool_active_heat_source":
            return status.get(KEY_ACTIVE_HEAT_SOURCE)
        elif sensor_key == "pool_water_temperature":
            return status.get(KEY_POOL_WATER_TEMP)
        elif sensor_key == "spa_water_temperature":
            return status.get(KEY_SPA_WATER_TEMP)
        elif sensor_key == "spa_solar_temperature":
            return status.get(KEY_SPA_SOLAR_TEMP)
        elif sensor_key == "pool_air_temperature":
            return status.get(KEY_POOL_AIR_TEMP)
        elif sensor_key == "solar_collector_temperature":
            return status.get(KEY_SOLAR_COLLECTOR_TEMP)

        return None

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
