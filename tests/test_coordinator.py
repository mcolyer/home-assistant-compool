"""Test Compool coordinator helpers."""

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.compool.const import KEY_POOL_HEAT_SOURCE, KEY_SPA_HEAT_SOURCE
from custom_components.compool.coordinator import CompoolStatusDataUpdateCoordinator
from homeassistant.core import HomeAssistant

from .const import MOCK_CONFIG


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
