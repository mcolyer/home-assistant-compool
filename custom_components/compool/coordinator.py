"""The Compool integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pycompool import PoolController

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import _LOGGER, DOMAIN, STATUS_SCAN_INTERVAL


@dataclass
class CompoolRuntimeData:
    """Runtime data for the Compool config entry."""

    coordinator: CompoolStatusDataUpdateCoordinator


type CompoolConfigEntry = ConfigEntry[CompoolRuntimeData]


class CompoolStatusDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Data update coordinator for pool controller status."""

    config_entry: CompoolConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: CompoolConfigEntry,
        host: str,
        port: int,
    ) -> None:
        """Initialize the Coordinator."""
        super().__init__(
            hass,
            config_entry=config_entry,
            name=DOMAIN,
            logger=_LOGGER,
            update_interval=STATUS_SCAN_INTERVAL,
        )

        self.host = host
        self.port = port
        self._device = f"{host}:{port}"

    def _get_pool_status(self) -> dict[str, Any] | None:
        """Get pool controller status with brief connection."""
        try:
            controller = PoolController(self._device, 9600)
            status = controller.get_status()
            # Controller automatically disconnects after get_status
        except Exception as ex:
            _LOGGER.error(f"Error getting pool controller status: {ex}")
            return None
        else:
            return status

    def _raise_if_no_status(self, status: dict[str, Any] | None) -> None:
        """Raise UpdateFailed if status is None."""
        if status is None:
            raise UpdateFailed("Failed to get pool controller status")

    async def _async_update_data(self) -> dict[str, Any]:
        """Update pool controller status."""
        try:
            status = await self.hass.async_add_executor_job(self._get_pool_status)
            self._raise_if_no_status(status)
        except Exception as ex:
            raise UpdateFailed(
                f"Error communicating with pool controller: {ex}"
            ) from ex
        else:
            return status
