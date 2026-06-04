"""Test Compool coordinator helpers."""

import asyncio
from functools import partial
from unittest.mock import patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.compool.const import KEY_POOL_HEAT_SOURCE, KEY_SPA_HEAT_SOURCE
from custom_components.compool.coordinator import CompoolStatusDataUpdateCoordinator
from homeassistant.core import HomeAssistant

from .const import MOCK_CONFIG, MOCK_POOL_STATUS, flush_writes


def _make_coordinator(hass: HomeAssistant) -> CompoolStatusDataUpdateCoordinator:
    """Create a coordinator instance without performing any I/O."""
    config_entry = MockConfigEntry(domain="compool", data=MOCK_CONFIG)
    config_entry.add_to_hass(hass)
    return CompoolStatusDataUpdateCoordinator(
        hass, config_entry, MOCK_CONFIG["host"], MOCK_CONFIG["port"]
    )


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (0, "off"),
        (1, "heater"),
        (2, "solar-priority"),
        (3, "solar-only"),
        (4, None),  # out-of-range int
        (None, None),  # missing value
    ],
)
async def test_normalize_heat_sources_int_codes(
    hass: HomeAssistant, raw, expected
) -> None:
    """Integer heat-source codes map to mode strings; bad values become None."""
    coordinator = _make_coordinator(hass)

    status = coordinator._normalize_heat_sources(
        {KEY_POOL_HEAT_SOURCE: raw, KEY_SPA_HEAT_SOURCE: raw}
    )

    assert status[KEY_POOL_HEAT_SOURCE] == expected
    assert status[KEY_SPA_HEAT_SOURCE] == expected


async def test_normalize_heat_sources_string_passthrough(hass: HomeAssistant) -> None:
    """Already-normalized string modes pass through unchanged."""
    coordinator = _make_coordinator(hass)

    status = coordinator._normalize_heat_sources(
        {KEY_POOL_HEAT_SOURCE: "heater", KEY_SPA_HEAT_SOURCE: "solar-only"}
    )

    assert status[KEY_POOL_HEAT_SOURCE] == "heater"
    assert status[KEY_SPA_HEAT_SOURCE] == "solar-only"


async def test_optimistic_updates_apply_immediately(hass: HomeAssistant) -> None:
    """Each setter reflects its change in coordinator.data before any flush."""
    coordinator = _make_coordinator(hass)
    coordinator.data = dict(MOCK_POOL_STATUS)

    with (
        patch.object(coordinator, "_set_pool_temperature", return_value=True),
        patch.object(coordinator, "_set_spa_temperature", return_value=True),
        patch.object(coordinator, "_set_heater_mode", return_value=True),
        patch.object(coordinator, "_set_aux_equipment", return_value=True),
    ):
        await coordinator.async_set_pool_temperature(85, "f")
        await coordinator.async_set_spa_temperature(99, "f")
        await coordinator.async_set_heater_mode("solar-only", "spa")
        await coordinator.async_set_aux_equipment(3, False)

    assert coordinator.data["desired_pool_temp_f"] == 85.0
    assert coordinator.data["desired_spa_temp_f"] == 99.0
    assert coordinator.data[KEY_SPA_HEAT_SOURCE] == "solar-only"
    assert coordinator.data[KEY_POOL_HEAT_SOURCE] == 1  # pool mode untouched
    assert coordinator.data["aux3_on"] is False

    await coordinator.async_shutdown()


async def test_optimistic_celsius_converts_to_fahrenheit(hass: HomeAssistant) -> None:
    """A Celsius setpoint is stored optimistically in Fahrenheit for the entity."""
    coordinator = _make_coordinator(hass)
    coordinator.data = dict(MOCK_POOL_STATUS)

    with patch.object(coordinator, "_set_pool_temperature", return_value=True):
        await coordinator.async_set_pool_temperature(30, "c")

    assert coordinator.data["desired_pool_temp_f"] == 86.0  # 30°C -> 86°F

    await coordinator.async_shutdown()


async def test_rapid_writes_coalesce_to_final_value(hass: HomeAssistant) -> None:
    """Slider-style rapid writes collapse to a single send of the last value."""
    coordinator = _make_coordinator(hass)
    coordinator.data = dict(MOCK_POOL_STATUS)

    with patch.object(
        coordinator, "_set_pool_temperature", return_value=True
    ) as mock_set:
        await coordinator.async_set_pool_temperature(80, "f")
        await coordinator.async_set_pool_temperature(85, "f")
        await coordinator.async_set_pool_temperature(90, "f")
        mock_set.assert_not_called()  # nothing sent until the field goes quiet

        await flush_writes(hass)
        mock_set.assert_called_once_with(90, "f")

    await coordinator.async_shutdown()


async def test_distinct_fields_each_flush(hass: HomeAssistant) -> None:
    """Independent fields are debounced separately and all get sent."""
    coordinator = _make_coordinator(hass)
    coordinator.data = dict(MOCK_POOL_STATUS)

    with (
        patch.object(
            coordinator, "_set_pool_temperature", return_value=True
        ) as mock_pool,
        patch.object(
            coordinator, "_set_spa_temperature", return_value=True
        ) as mock_spa,
        patch.object(coordinator, "_set_aux_equipment", return_value=True) as mock_aux,
    ):
        await coordinator.async_set_pool_temperature(85, "f")
        await coordinator.async_set_spa_temperature(99, "f")
        await coordinator.async_set_aux_equipment(1, False)

        await flush_writes(hass)
        mock_pool.assert_called_once_with(85, "f")
        mock_spa.assert_called_once_with(99, "f")
        mock_aux.assert_called_once_with(1, False)

    await coordinator.async_shutdown()


async def test_failed_write_keeps_optimistic_value(hass: HomeAssistant) -> None:
    """A failed send still leaves the optimistic value for the next poll to fix."""
    coordinator = _make_coordinator(hass)
    coordinator.data = dict(MOCK_POOL_STATUS)

    with patch.object(
        coordinator, "_set_pool_temperature", return_value=False
    ) as mock_set:
        await coordinator.async_set_pool_temperature(90, "f")
        assert coordinator.data["desired_pool_temp_f"] == 90.0  # optimistic

        await flush_writes(hass)
        mock_set.assert_called_once_with(90, "f")  # send was attempted

    # Optimistic value persists; the periodic poll will reconcile it.
    assert coordinator.data["desired_pool_temp_f"] == 90.0

    await coordinator.async_shutdown()


async def test_write_waits_for_bus_lock(hass: HomeAssistant) -> None:
    """A debounced write cannot reach the bus while the lock is held by a poll."""
    coordinator = _make_coordinator(hass)
    coordinator.data = dict(MOCK_POOL_STATUS)

    with patch.object(
        coordinator, "_set_pool_temperature", return_value=True
    ) as mock_set:
        # Hold the bus as a concurrent poll would, then start a flush directly.
        await coordinator._io_lock.acquire()
        coordinator._pending_writes["pool_temp"] = partial(
            coordinator._set_pool_temperature, 85, "f"
        )
        task = asyncio.ensure_future(coordinator._flush_write("pool_temp", None))
        await asyncio.sleep(0)  # let the flush reach the lock and block

        assert not task.done()
        mock_set.assert_not_called()

        coordinator._io_lock.release()
        await task
        mock_set.assert_called_once_with(85, "f")

    await coordinator.async_shutdown()


async def test_shutdown_cancels_pending_writes(hass: HomeAssistant) -> None:
    """Pending debounced writes are dropped on unload."""
    coordinator = _make_coordinator(hass)
    coordinator.data = dict(MOCK_POOL_STATUS)

    with patch.object(
        coordinator, "_set_pool_temperature", return_value=True
    ) as mock_set:
        await coordinator.async_set_pool_temperature(85, "f")
        await coordinator.async_shutdown()

        await flush_writes(hass)
        mock_set.assert_not_called()
