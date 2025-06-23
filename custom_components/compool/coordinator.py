"""The Compool integration."""

from __future__ import annotations

from dataclasses import dataclass
import time
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
        self._device = f"socket://{host}:{port}"
        self._consecutive_failures = 0
        self._last_failure_time = 0

    def _is_connection_timeout_error(self, exception: Exception) -> bool:
        """Check if the exception is a connection timeout error."""
        error_msg = str(exception).lower()
        return any(
            keyword in error_msg
            for keyword in [
                "timed out",
                "timeout",
                "connection refused",
                "could not open port",
            ]
        )

    def _raise_no_status_error(self) -> None:
        """Raise UpdateFailed for no status data."""
        raise UpdateFailed("No status data received from pool controller")

    def _enhance_status_data(self, status: dict[str, Any]) -> None:
        """Add computed fields to status data."""
        # Compute active heat source based on current heating activity
        # According to pycompool docs, we can determine active heat source from heater_on and solar_on
        if status.get("heater_on") and status.get("solar_on"):
            active_heat_source = "heater+solar"
        elif status.get("heater_on"):
            active_heat_source = "heater"
        elif status.get("solar_on"):
            active_heat_source = "solar"
        else:
            active_heat_source = "off"

        status["active_heat_source"] = active_heat_source

    def _get_pool_status_with_retry(self) -> dict[str, Any]:
        """Get pool controller status with retry logic for connection failures."""
        max_retries = 5
        base_delay = 3  # seconds

        for attempt in range(max_retries + 1):
            try:
                controller = PoolController(self._device, 9600)
                status = controller.get_status()
                # Controller automatically disconnects after get_status

                # Reset failure tracking on success
                self._consecutive_failures = 0
                self._last_failure_time = 0

                if not status:
                    self._raise_no_status_error()
                else:
                    # Enhance status with computed fields
                    self._enhance_status_data(status)
                    return status

            except Exception as ex:
                if attempt < max_retries and self._is_connection_timeout_error(ex):
                    delay = base_delay * (2**attempt)  # Exponential backoff
                    _LOGGER.warning(
                        "Connection attempt %d/%d failed: %s. Retrying in %d seconds...",
                        attempt + 1,
                        max_retries + 1,
                        ex,
                        delay,
                    )
                    time.sleep(delay)
                    continue

                # Track consecutive failures for connection timeout errors
                if self._is_connection_timeout_error(ex):
                    self._consecutive_failures += 1
                    self._last_failure_time = time.time()

                    # Log different messages based on failure count
                    if self._consecutive_failures <= 3:
                        _LOGGER.warning(
                            "Connection timeout (%d/%d): %s - will retry on next update",
                            self._consecutive_failures,
                            3,
                            ex,
                        )
                    else:
                        _LOGGER.error(
                            "Persistent connection failures (%d consecutive): %s",
                            self._consecutive_failures,
                            ex,
                        )
                else:
                    _LOGGER.error("Error getting pool controller status: %s", ex)

                # Re-raise the exception to let the coordinator handle it
                raise UpdateFailed(
                    f"Failed to get pool controller status: {ex}"
                ) from ex

    async def _async_update_data(self) -> dict[str, Any]:
        """Update pool controller status."""
        return await self.hass.async_add_executor_job(self._get_pool_status_with_retry)

    def _format_temperature_string(self, temperature: float, unit: str) -> str:
        """Format temperature and unit for pycompool API."""
        if unit.lower() == "c":
            return f"{temperature}c"
        else:
            return f"{int(temperature)}f"

    def _set_pool_temperature(self, temperature: float, unit: str) -> bool:
        """Set pool temperature using pycompool."""
        try:
            controller = PoolController(self._device, 9600)
            temp_str = self._format_temperature_string(temperature, unit)
            return controller.set_pool_temperature(temp_str)
        except Exception as ex:
            _LOGGER.error("Error setting pool temperature: %s", ex)
            return False

    def _set_spa_temperature(self, temperature: float, unit: str) -> bool:
        """Set spa temperature using pycompool."""
        try:
            controller = PoolController(self._device, 9600)
            temp_str = self._format_temperature_string(temperature, unit)
            return controller.set_spa_temperature(temp_str)
        except Exception as ex:
            _LOGGER.error("Error setting spa temperature: %s", ex)
            return False

    def _set_heater_mode(self, mode: str, target: str) -> bool:
        """Set heater mode using pycompool."""
        try:
            controller = PoolController(self._device, 9600)
            return controller.set_heater_mode(mode, target)
        except Exception as ex:
            _LOGGER.error("Error setting heater mode: %s", ex)
            return False

    async def async_set_pool_temperature(
        self, temperature: float, unit: str = "f"
    ) -> bool:
        """Set pool temperature."""
        return await self.hass.async_add_executor_job(
            self._set_pool_temperature, temperature, unit
        )

    async def async_set_spa_temperature(
        self, temperature: float, unit: str = "f"
    ) -> bool:
        """Set spa temperature."""
        return await self.hass.async_add_executor_job(
            self._set_spa_temperature, temperature, unit
        )

    async def async_set_heater_mode(self, mode: str, target: str) -> bool:
        """Set heater mode."""
        return await self.hass.async_add_executor_job(
            self._set_heater_mode, mode, target
        )
