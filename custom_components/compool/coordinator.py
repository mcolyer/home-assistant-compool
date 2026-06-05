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
    RECONCILE_DELAY_SECONDS,
    STATUS_SCAN_INTERVAL,
    WRITE_BATCH_INTERVAL_SECONDS,
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
        # Batched writes: changes accumulate in the queue (latest value per
        # field wins) and the whole batch is flushed once, a single collect
        # window after the first queued change.
        self._pending_writes: dict[str, Callable[[], bool]] = {}
        self._flush_unsub: CALLBACK_TYPE | None = None
        # Pending delayed reconcile poll scheduled after a batch is sent.
        self._reconcile_unsub: CALLBACK_TYPE | None = None
        # Last hardware-truth aux states from the most recent poll, used to
        # decide whether an aux toggle is needed (see _set_aux_equipment).
        self._aux_state: dict[int, bool] = {}
        # Data keys that were updated optimistically and have not yet been
        # observed in a successful controller poll.
        self._pending_confirmation: set[str] = set()

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
            status = await self.hass.async_add_executor_job(
                self._get_pool_status_with_retry
            )
        self._capture_aux_state(status)
        self._clear_confirmed_keys(status)
        return status

    def _capture_aux_state(self, status: dict[str, Any]) -> None:
        """Record the hardware-truth aux states reported by a poll.

        This baseline is independent of the in-place optimistic mutation of
        ``self.data`` and drives the toggle decision in _set_aux_equipment.
        """
        for aux_num in range(1, 9):
            value = status.get(f"aux{aux_num}_on")
            if isinstance(value, bool):
                self._aux_state[aux_num] = value

    def _clear_confirmed_keys(self, status: dict[str, Any]) -> None:
        """Clear optimistic confirmation markers for keys present in a poll."""
        self._pending_confirmation.difference_update(status)

    def is_pending_confirmation(self, key: str) -> bool:
        """Return whether a status key is waiting for controller confirmation."""
        return key in self._pending_confirmation

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

        Calling async_set_updated_data also pushes the periodic poll out, so a
        near-term heartbeat (still showing the old value) can't snap the UI
        back. The optimistic value is reconciled by the delayed reconcile poll
        scheduled after the write completes (see _schedule_reconcile).
        """
        if self.data is None:
            return
        self._pending_confirmation.update(updates)
        self.data.update(updates)
        self.async_set_updated_data(self.data)

    @callback
    def _schedule_write(
        self,
        field: str,
        send: Callable[[], bool],
        optimistic: dict[str, Any],
    ) -> None:
        """Optimistically update the UI and queue the hardware write.

        Changes accumulate in a single batch (the latest value per field wins).
        The first queued change arms one flush timer; later changes within the
        collect window join the same batch without pushing the timer out, so the
        whole batch is sent to the controller at once.
        """
        self._apply_optimistic(optimistic)
        self._pending_writes[field] = send
        if self._flush_unsub is None:
            self._flush_unsub = async_call_later(
                self.hass, WRITE_BATCH_INTERVAL_SECONDS, self._flush_batch
            )

    async def _flush_batch(self, _now: Any) -> None:
        """Send the whole queued batch to the controller, then reconcile.

        Every queued write is sent sequentially under a single bus-lock hold so
        the half-duplex RS485 bus is never contended. Afterwards a single
        delayed reconcile poll is scheduled (see _schedule_reconcile) to replace
        the optimistic state with the real heartbeat once it has caught up.
        """
        self._flush_unsub = None
        batch = self._pending_writes
        self._pending_writes = {}
        if not batch:
            return
        async with self._io_lock:
            for field, send in batch.items():
                success = await self.hass.async_add_executor_job(send)
                if not success:
                    _LOGGER.error("Compool write for %s failed", field)
        self._schedule_reconcile()

    @callback
    def _schedule_reconcile(self) -> None:
        """Re-poll once, a few seconds out, to reconcile the optimistic state.

        The controller only reflects a just-sent command on a later heartbeat,
        so we wait past that lag before reading - an immediate poll would return
        the pre-change state and snap the UI back. The latest reconcile wins.
        """
        if self._reconcile_unsub is not None:
            self._reconcile_unsub()
        self._reconcile_unsub = async_call_later(
            self.hass, RECONCILE_DELAY_SECONDS, self._reconcile
        )

    async def _reconcile(self, _now: Any) -> None:
        """Poll the controller to overwrite optimistic state with real status."""
        self._reconcile_unsub = None
        await self.async_request_refresh()

    async def async_shutdown(self) -> None:
        """Cancel any pending batched write and reconcile poll on unload."""
        if self._flush_unsub is not None:
            self._flush_unsub()
            self._flush_unsub = None
        if self._reconcile_unsub is not None:
            self._reconcile_unsub()
            self._reconcile_unsub = None
        self._pending_writes.clear()
        self._pending_confirmation.clear()
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
        """Drive an aux circuit to the requested state.

        The hardware only supports *toggling* a circuit. pycompool's
        set_aux_equipment guards the toggle with its own fresh heartbeat read,
        which lags the real state and silently drops the toggle (notably for
        "off", where a stale "already off" read matches the request). Instead we
        decide here against the last polled state (self._aux_state) and send an
        unconditional toggle only when it differs, so the command never depends
        on a single lagging heartbeat read.
        """
        current = self._aux_state.get(aux_num)
        if current == state:
            # Already in the requested state per the last poll; nothing to do.
            return True
        try:
            controller = PoolController(self._device, 9600)
            success = controller.toggle_aux_equipment(aux_num)
        except Exception as ex:
            _LOGGER.error("Error setting aux%d equipment: %s", aux_num, ex)
            return False
        if success:
            # Reflect the toggle so a later change in the same window is correct.
            self._aux_state[aux_num] = state
        return success

    async def async_set_aux_equipment(self, aux_num: int, state: bool) -> None:
        """Set auxiliary equipment state."""
        self._schedule_write(
            f"aux{aux_num}",
            partial(self._set_aux_equipment, aux_num, state),
            {f"aux{aux_num}_on": state},
        )
