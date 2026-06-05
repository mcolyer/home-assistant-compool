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
    OPTIMISTIC_CONFIRMATION_WINDOW_SECONDS,
    RECONCILE_DELAY_SECONDS,
    STATUS_SCAN_INTERVAL,
    WRITE_BATCH_INTERVAL_SECONDS,
)


@dataclass
class CompoolRuntimeData:
    """Runtime data for the Compool config entry."""

    coordinator: CompoolStatusDataUpdateCoordinator


@dataclass
class PendingConfirmation:
    """Optimistic value waiting for a controller heartbeat to confirm it."""

    expected: Any
    requested_at: float
    stale_reconcile_count: int = 0


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
        # Data keys that were updated optimistically and the expected value
        # that has not yet been observed in a successful controller poll.
        self._pending_confirmation: dict[str, PendingConfirmation] = {}

    def _aux_status_snapshot(self, status: dict[str, Any]) -> dict[str, Any]:
        """Return only aux status bits for focused debug logging."""
        return {
            f"aux{aux_num}_on": status.get(f"aux{aux_num}_on")
            for aux_num in range(1, 9)
        }

    def _pending_confirmation_snapshot(self) -> dict[str, dict[str, Any]]:
        """Return pending confirmations with current age for debug logging."""
        now = time.monotonic()
        return {
            key: {
                "expected": confirmation.expected,
                "age": round(now - confirmation.requested_at, 3),
                "stale_reconcile_count": confirmation.stale_reconcile_count,
            }
            for key, confirmation in self._pending_confirmation.items()
        }

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
            poll_started = time.monotonic()
            try:
                _LOGGER.debug(
                    "Compool bus poll start: attempt=%d/%d device=%s",
                    attempt + 1,
                    max_retries + 1,
                    self._device,
                )
                controller = PoolController(self._device, 9600)
                status = controller.get_status()
                # Controller automatically disconnects after get_status
                poll_duration = time.monotonic() - poll_started

                # Reset failure tracking on success
                self._consecutive_failures = 0
                self._last_failure_time = 0

                if not status:
                    _LOGGER.debug(
                        "Compool bus poll returned no status: attempt=%d duration=%.3fs",
                        attempt + 1,
                        poll_duration,
                    )
                    self._raise_no_status_error()
                else:
                    _LOGGER.debug(
                        "Compool bus poll complete: attempt=%d duration=%.3fs "
                        "status_keys=%d aux=%s pending=%s",
                        attempt + 1,
                        poll_duration,
                        len(status),
                        self._aux_status_snapshot(status),
                        self._pending_confirmation_snapshot(),
                    )
                    return self._normalize_heat_sources(status)

            except Exception as ex:
                poll_duration = time.monotonic() - poll_started
                _LOGGER.debug(
                    "Compool bus poll failed: attempt=%d/%d duration=%.3fs error=%r",
                    attempt + 1,
                    max_retries + 1,
                    poll_duration,
                    ex,
                )
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
        lock_wait_started = time.monotonic()
        async with self._io_lock:
            lock_wait_duration = time.monotonic() - lock_wait_started
            _LOGGER.debug(
                "Compool bus poll acquired lock: wait=%.3fs pending_writes=%s",
                lock_wait_duration,
                list(self._pending_writes),
            )
            status = await self.hass.async_add_executor_job(
                self._get_pool_status_with_retry
            )
        status = self._reconcile_pending_status(status)
        self._capture_aux_state(status)
        _LOGGER.debug(
            "Compool coordinator poll applied: aux=%s aux_state=%s pending=%s",
            self._aux_status_snapshot(status),
            self._aux_state,
            self._pending_confirmation_snapshot(),
        )
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

    def _reconcile_pending_status(self, status: dict[str, Any]) -> dict[str, Any]:
        """Preserve optimistic values during a bounded confirmation window."""
        if not self._pending_confirmation:
            _LOGGER.debug(
                "Compool reconcile skipped: no pending confirmations aux=%s",
                self._aux_status_snapshot(status),
            )
            return status

        reconciled_status = dict(status)
        pending_confirmation: dict[str, PendingConfirmation] = {}
        should_repoll = False
        now = time.monotonic()
        _LOGGER.debug(
            "Compool reconcile start: aux=%s pending=%s window=%.0fs",
            self._aux_status_snapshot(status),
            self._pending_confirmation_snapshot(),
            OPTIMISTIC_CONFIRMATION_WINDOW_SECONDS,
        )

        for key, confirmation in self._pending_confirmation.items():
            age = now - confirmation.requested_at
            if key not in reconciled_status:
                if age <= OPTIMISTIC_CONFIRMATION_WINDOW_SECONDS:
                    _LOGGER.debug(
                        "Compool reconcile preserves optimistic missing key: "
                        "key=%s expected=%r age=%.3fs stale_polls=%d",
                        key,
                        confirmation.expected,
                        age,
                        confirmation.stale_reconcile_count,
                    )
                    pending_confirmation[key] = confirmation
                    should_repoll = True
                else:
                    _LOGGER.warning(
                        "Compool optimistic value for %s was not reported within "
                        "%.0f seconds; expected %r, stale polls: %d",
                        key,
                        OPTIMISTIC_CONFIRMATION_WINDOW_SECONDS,
                        confirmation.expected,
                        confirmation.stale_reconcile_count,
                    )
                continue
            reported = reconciled_status[key]
            if reported == confirmation.expected:
                _LOGGER.debug(
                    "Compool reconcile confirmed optimistic value: key=%s "
                    "expected=%r age=%.3fs stale_polls=%d",
                    key,
                    confirmation.expected,
                    age,
                    confirmation.stale_reconcile_count,
                )
                continue

            stale_count = confirmation.stale_reconcile_count + 1
            if age <= OPTIMISTIC_CONFIRMATION_WINDOW_SECONDS:
                _LOGGER.debug(
                    "Compool reconcile preserves optimistic stale value: key=%s "
                    "expected=%r reported=%r age=%.3fs stale_polls=%d",
                    key,
                    confirmation.expected,
                    reported,
                    age,
                    stale_count,
                )
                confirmation.stale_reconcile_count = stale_count
                reconciled_status[key] = confirmation.expected
                pending_confirmation[key] = confirmation
                should_repoll = True
                continue

            _LOGGER.warning(
                "Compool optimistic value for %s was not confirmed within %.0f "
                "seconds; expected %r, reported %r, stale polls: %d",
                key,
                OPTIMISTIC_CONFIRMATION_WINDOW_SECONDS,
                confirmation.expected,
                reported,
                stale_count,
            )

        self._pending_confirmation = pending_confirmation
        if should_repoll:
            self._schedule_reconcile()
        _LOGGER.debug(
            "Compool reconcile complete: aux=%s pending=%s should_repoll=%s",
            self._aux_status_snapshot(reconciled_status),
            self._pending_confirmation_snapshot(),
            should_repoll,
        )
        return reconciled_status

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
        prior_values = {key: self.data.get(key) for key in updates}
        for key, value in updates.items():
            self._pending_confirmation[key] = PendingConfirmation(
                expected=value, requested_at=time.monotonic()
            )
        _LOGGER.debug(
            "Compool optimistic update applied: updates=%s prior=%s pending=%s",
            updates,
            prior_values,
            self._pending_confirmation_snapshot(),
        )
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
        timer_was_armed = self._flush_unsub is not None
        _LOGGER.debug(
            "Compool write queued: field=%s optimistic=%s queued_fields=%s "
            "flush_timer_already_armed=%s",
            field,
            optimistic,
            list(self._pending_writes),
            timer_was_armed,
        )
        if self._flush_unsub is None:
            self._flush_unsub = async_call_later(
                self.hass, WRITE_BATCH_INTERVAL_SECONDS, self._flush_batch
            )
            _LOGGER.debug(
                "Compool write flush scheduled: delay=%.3fs queued_fields=%s",
                WRITE_BATCH_INTERVAL_SECONDS,
                list(self._pending_writes),
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
            _LOGGER.debug("Compool write flush skipped: empty batch")
            return
        batch_started = time.monotonic()
        _LOGGER.debug(
            "Compool write flush start: fields=%s count=%d pending=%s",
            list(batch),
            len(batch),
            self._pending_confirmation_snapshot(),
        )
        lock_wait_started = time.monotonic()
        async with self._io_lock:
            _LOGGER.debug(
                "Compool write flush acquired lock: wait=%.3fs fields=%s",
                time.monotonic() - lock_wait_started,
                list(batch),
            )
            for field, send in batch.items():
                write_started = time.monotonic()
                _LOGGER.debug("Compool bus write start: field=%s", field)
                success = await self.hass.async_add_executor_job(send)
                _LOGGER.debug(
                    "Compool bus write complete: field=%s success=%s duration=%.3fs",
                    field,
                    success,
                    time.monotonic() - write_started,
                )
                if not success:
                    _LOGGER.error("Compool write for %s failed", field)
        _LOGGER.debug(
            "Compool write flush complete: fields=%s total_duration=%.3fs",
            list(batch),
            time.monotonic() - batch_started,
        )
        self._schedule_reconcile()

    @callback
    def _schedule_reconcile(self) -> None:
        """Re-poll once, a few seconds out, to reconcile the optimistic state.

        The controller only reflects a just-sent command on a later heartbeat,
        so we wait past that lag before reading - an immediate poll would return
        the pre-change state and snap the UI back. The latest reconcile wins.
        """
        if self._reconcile_unsub is not None:
            _LOGGER.debug("Compool reconcile rescheduled: cancelling prior timer")
            self._reconcile_unsub()
        self._reconcile_unsub = async_call_later(
            self.hass, RECONCILE_DELAY_SECONDS, self._reconcile
        )
        _LOGGER.debug(
            "Compool reconcile scheduled: delay=%.3fs pending=%s",
            RECONCILE_DELAY_SECONDS,
            self._pending_confirmation_snapshot(),
        )

    async def _reconcile(self, _now: Any) -> None:
        """Poll the controller to overwrite optimistic state with real status."""
        self._reconcile_unsub = None
        _LOGGER.debug(
            "Compool reconcile timer fired: pending=%s",
            self._pending_confirmation_snapshot(),
        )
        await self.async_refresh()

    async def async_shutdown(self) -> None:
        """Cancel any pending batched write and reconcile poll on unload."""
        if self._flush_unsub is not None:
            self._flush_unsub()
            self._flush_unsub = None
        if self._reconcile_unsub is not None:
            self._reconcile_unsub()
            self._reconcile_unsub = None
        _LOGGER.debug(
            "Compool coordinator shutdown: dropping pending_writes=%s pending=%s",
            list(self._pending_writes),
            self._pending_confirmation_snapshot(),
        )
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
            _LOGGER.debug(
                "Compool aux write skipped: aux=%d desired=%s aux_state=%s reason=already_matching",
                aux_num,
                state,
                current,
            )
            return True
        try:
            _LOGGER.debug(
                "Compool aux toggle start: aux=%d desired=%s aux_state=%s",
                aux_num,
                state,
                current,
            )
            toggle_started = time.monotonic()
            controller = PoolController(self._device, 9600)
            success = controller.toggle_aux_equipment(aux_num)
            _LOGGER.debug(
                "Compool aux toggle complete: aux=%d desired=%s success=%s duration=%.3fs",
                aux_num,
                state,
                success,
                time.monotonic() - toggle_started,
            )
        except Exception as ex:
            _LOGGER.error("Error setting aux%d equipment: %s", aux_num, ex)
            return False
        if success:
            # Reflect the toggle so a later change in the same window is correct.
            self._aux_state[aux_num] = state
            _LOGGER.debug(
                "Compool aux state advanced after toggle: aux=%d aux_state=%s",
                aux_num,
                self._aux_state,
            )
        return success

    async def async_set_aux_equipment(self, aux_num: int, state: bool) -> None:
        """Set auxiliary equipment state."""
        _LOGGER.debug(
            "Compool aux request received: aux=%d desired=%s current_data=%r aux_state=%r",
            aux_num,
            state,
            self.data.get(f"aux{aux_num}_on") if self.data else None,
            self._aux_state.get(aux_num),
        )
        self._schedule_write(
            f"aux{aux_num}",
            partial(self._set_aux_equipment, aux_num, state),
            {f"aux{aux_num}_on": state},
        )
