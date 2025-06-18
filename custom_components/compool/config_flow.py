"""Config flow for compool integration."""

from __future__ import annotations

import logging
from typing import Any

from pycompool import PoolController
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .const import DEFAULT_PORT, DOMAIN

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
    }
)


def _raise_no_status_connect_error() -> None:
    """Raise CannotConnect for no status data."""
    raise CannotConnect("No status data received from pool controller")


def _validate_input(hass: HomeAssistant, data: dict[str, Any]) -> PoolController:
    """Validate in the executor."""
    host = data[CONF_HOST]
    port = data[CONF_PORT]

    # Create RS485 over TCP connection string
    device = f"socket://{host}:{port}"
    _LOGGER.debug("Testing connection to %s", device)

    try:
        controller = PoolController(device, 9600)
        # Test connection by getting status
        status = controller.get_status()
        _LOGGER.debug("Received status: %s", status)

        if not status:
            _raise_no_status_connect_error()
        else:
            return controller
    except Exception as err:
        _LOGGER.error("Failed to connect to pool controller at %s: %s", device, err)
        raise CannotConnect(f"Connection failed: {err}") from err


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from DATA_SCHEMA with values provided by the user.
    """
    try:
        await hass.async_add_executor_job(_validate_input, hass, data)
        # Controller will auto-disconnect after get_status
    except Exception as err:
        _LOGGER.exception("Unexpected error during validation")
        raise CannotConnect from err

    # Return info that you want to store in the config entry.
    return {"title": f"Pool Controller {data[CONF_HOST]}:{data[CONF_PORT]}"}


class CompoolConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for compool."""

    VERSION = 1

    def __init__(self) -> None:
        """Init compool config flow."""
        self._reauth_unique_id: str | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            await self.async_set_unique_id(
                f"{user_input[CONF_HOST]}:{user_input[CONF_PORT]}"
            )
            self._abort_if_unique_id_configured()

            try:
                info = await validate_input(self.hass, user_input)
                return self.async_create_entry(title=info["title"], data=user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""
