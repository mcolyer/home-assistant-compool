"""The Compool integration."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from functools import partial
import time
from typing import Any

from pycompool import PoolController

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    _LOGGER,
    DOMAIN,
    HEATER_MODES,
    KEY_POOL_HEAT_SOURCE,
    KEY_SPA_HEAT_SOURCE,
    STATUS_SCAN_INTERVAL,
    WRITE_DEBOUNCE_SECONDS,
)


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

        # Serialize every transaction on the half-duplex RS485 bus: only one
        # poll or write may touch the controller at a time.
        self._io_lock = asyncio.Lock()
        # Per-field write debounce: the latest pending send wins, and its
        # in-flight timer is reset on each new change to the same field.
        self._pending_writes: dict[str, Callable[[], bool]] = {}
        self._debounce_unsub: dict[str, CALLBACK_TYPE] = {}

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

    def _normalize_heat_sources(self, status: dict[str, Any]) -> dict[str, Any]:
        """Convert pycompool integer heat-source codes (0-3) to mode strings.

        pycompool reports ``pool_heat_source``/``spa_heat_source`` as integers
        (0=off, 1=heater, 2=solar-priority, 3=solar-only), index-aligned with
        HEATER_MODES. Entities expect the string mode, so normalize in place.
        """
        for key in (KEY_POOL_HEAT_SOURCE, KEY_SPA_HEAT_SOURCE):
            raw = status.get(key)
            if isinstance(raw, int) and 0 <= raw < len(HEATER_MODES):
                status[key] = HEATER_MODES[raw]
            elif raw not in HEATER_MODES:
                # Already-normalized strings pass through; anything else is unexpected.
                _LOGGER.debug("Unexpected %s value from controller: %r", key, raw)
                status[key] = None
        return status

    def _get_pool_status_with_retry(self) -> dict[str, Any]:
        """Get pool controller status with retry logic for connection failures."""
        # Keep retries minimal: this runs while holding the bus lock (blocking
        # user commands), and the coordinator already re-polls every 30s.
        max_retries = 1
        base_delay = 1  # seconds

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
                    return self._normalize_heat_sources(status)

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
        async with self._io_lock:
            return await self.hass.async_add_executor_job(
                self._get_pool_status_with_retry
            )

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

    def _apply_optimistic(self, updates: dict[str, Any]) -> None:
        """Reflect a just-requested change in the UI before the next poll.

        Pushing the next poll out (via async_set_updated_data) also gives the
        controller's heartbeat time to catch up before we read it again, so a
        stale read can no longer snap the value back.
        """
        if self.data is None:
            return
        self.data.update(updates)
        self.async_set_updated_data(self.data)

    @callback
    def _schedule_write(
        self,
        field: str,
        send: Callable[[], bool],
        optimistic: dict[str, Any],
    ) -> None:
        """Optimistically update the UI and debounce the hardware write.

        Rapid changes to the same field (slider drags, double-clicks) collapse
        to a single send of the final value once the field goes quiet.
        """
        self._apply_optimistic(optimistic)
        self._pending_writes[field] = send
        if unsub := self._debounce_unsub.pop(field, None):
            unsub()
        self._debounce_unsub[field] = async_call_later(
            self.hass, WRITE_DEBOUNCE_SECONDS, partial(self._flush_write, field)
        )

    async def _flush_write(self, field: str, _now: Any) -> None:
        """Send the latest pending value for a field to the controller."""
        self._debounce_unsub.pop(field, None)
        send = self._pending_writes.pop(field, None)
        if send is None:
            return
        async with self._io_lock:
            success = await self.hass.async_add_executor_job(send)
        if not success:
            _LOGGER.error("Compool write for %s failed", field)

    async def async_shutdown(self) -> None:
        """Cancel any pending debounced writes on unload."""
        for unsub in self._debounce_unsub.values():
            unsub()
        self._debounce_unsub.clear()
        self._pending_writes.clear()
        await super().async_shutdown()

    async def async_set_pool_temperature(
        self, temperature: float, unit: str = "f"
    ) -> None:
        """Set pool temperature."""
        temp_f = temperature if unit.lower() == "f" else round(temperature * 9 / 5 + 32)
        self._schedule_write(
            "pool_temp",
            partial(self._set_pool_temperature, temperature, unit),
            {"desired_pool_temp_f": float(temp_f)},
        )

    async def async_set_spa_temperature(
        self, temperature: float, unit: str = "f"
    ) -> None:
        """Set spa temperature."""
        temp_f = temperature if unit.lower() == "f" else round(temperature * 9 / 5 + 32)
        self._schedule_write(
            "spa_temp",
            partial(self._set_spa_temperature, temperature, unit),
            {"desired_spa_temp_f": float(temp_f)},
        )

    async def async_set_heater_mode(self, mode: str, target: str) -> None:
        """Set heater mode."""
        key = KEY_POOL_HEAT_SOURCE if target == "pool" else KEY_SPA_HEAT_SOURCE
        self._schedule_write(
            f"heat_{target}",
            partial(self._set_heater_mode, mode, target),
            {key: mode},
        )

    def _set_aux_equipment(self, aux_num: int, state: bool) -> bool:
        """Set auxiliary equipment state using pycompool.

        Note: pycompool reads the controller's heartbeat and only sends a toggle
        when the current state differs from the requested one. Two intentional
        toggles of the same aux within one heartbeat window can therefore still
        desync. The per-field debounce in _schedule_write collapses rapid
        changes and removes the common case; a full fix would track desired
        state here and use toggle_aux_equipment instead.
        """
        try:
            controller = PoolController(self._device, 9600)
            return controller.set_aux_equipment(aux_num, state)
        except Exception as ex:
            _LOGGER.error("Error setting aux%d equipment: %s", aux_num, ex)
            return False

    async def async_set_aux_equipment(self, aux_num: int, state: bool) -> None:
        """Set auxiliary equipment state."""
        self._schedule_write(
            f"aux{aux_num}",
            partial(self._set_aux_equipment, aux_num, state),
            {f"aux{aux_num}_on": state},
        )
