"""Test the Compool config flow."""

from unittest.mock import patch

import pytest

from custom_components.compool.config_flow import CannotConnect
from custom_components.compool.const import DOMAIN
from homeassistant import config_entries
from homeassistant.core import HomeAssistant

from .const import MOCK_CONFIG


@pytest.fixture(name="bypass_setup", autouse=True)
def bypass_setup_fixture():
    """Prevent setup."""
    with patch(
        "custom_components.compool.async_setup_entry",
        return_value=True,
    ):
        yield


async def test_form(hass: HomeAssistant) -> None:
    """Test we get the form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == "form"
    assert result["errors"] == {}

    with (
        patch(
            "custom_components.compool.config_flow.validate_input",
            return_value={"title": "Pool Controller 192.168.1.100:8899"},
        ),
        patch(
            "custom_components.compool.async_setup_entry",
            return_value=True,
        ),
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            MOCK_CONFIG,
        )
        await hass.async_block_till_done()

    assert result2["type"] == "create_entry"
    assert result2["title"] == "Pool Controller 192.168.1.100:8899"
    assert result2["data"] == MOCK_CONFIG


async def test_form_cannot_connect(hass: HomeAssistant) -> None:
    """Test we handle cannot connect error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "custom_components.compool.config_flow.validate_input",
        side_effect=CannotConnect,
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            MOCK_CONFIG,
        )

    assert result2["type"] == "form"
    assert result2["errors"] == {"base": "cannot_connect"}
