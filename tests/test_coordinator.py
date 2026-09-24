"""Test Compool coordinator helpers."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.compool.const import KEY_POOL_HEAT_SOURCE, KEY_SPA_HEAT_SOURCE
from custom_components.compool.coordinator import (
    CompoolStatusDataUpdateCoordinator,
    PendingWrite,
)
from homeassistant.core import HomeAssistant

from .const import MOCK_CONFIG, MOCK_POOL_STATUS, flush_reconcile, flush_writes


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
        patch.object(coordinator, "_set_heater_modes", return_value=True),
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


async def test_optimistic_temperature_matches_transmitted_value(
    hass: HomeAssistant,
) -> None:
    """Fractional Fahrenheit input reflects pycompool's integer command value."""
    coordinator = _make_coordinator(hass)
    coordinator.data = dict(MOCK_POOL_STATUS)

    await coordinator.async_set_pool_temperature(85.9, "f")

    assert coordinator.data["desired_pool_temp_f"] == 85.0
    await coordinator.async_shutdown()


async def test_rapid_writes_coalesce_to_final_value(hass: HomeAssistant) -> None:
    """Slider-style rapid writes collapse to a single send of the last value."""
    coordinator = _make_coordinator(hass)
    coordinator.data = dict(MOCK_POOL_STATUS)

    with (
        patch.object(coordinator, "async_request_refresh", new=AsyncMock()),
        patch.object(
            coordinator, "_set_pool_temperature", return_value=True
        ) as mock_set,
    ):
        await coordinator.async_set_pool_temperature(80, "f")
        await coordinator.async_set_pool_temperature(85, "f")
        await coordinator.async_set_pool_temperature(90, "f")
        mock_set.assert_not_called()  # nothing sent until the batch window ends

        await flush_writes(hass)
        mock_set.assert_called_once_with(90, "f")

    await coordinator.async_shutdown()


async def test_distinct_fields_flush_in_one_batch(hass: HomeAssistant) -> None:
    """Independent fields queued in one window all flush together in one batch."""
    coordinator = _make_coordinator(hass)
    coordinator.data = dict(MOCK_POOL_STATUS)
    coordinator._aux_state = {1: True}  # currently on, so "off" must send

    with (
        patch.object(coordinator, "async_request_refresh", new=AsyncMock()),
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


async def test_heater_modes_share_one_atomic_write(hass: HomeAssistant) -> None:
    """Pool and spa changes are composed into one protocol-field write."""
    coordinator = _make_coordinator(hass)
    coordinator.data = coordinator._normalize_heat_sources(dict(MOCK_POOL_STATUS))

    with patch.object(coordinator, "_set_heater_modes", return_value=True) as mock_set:
        await coordinator.async_set_heater_mode("solar-only", "pool")
        await coordinator.async_set_heater_mode("heater", "spa")
        await flush_writes(hass)

    mock_set.assert_called_once_with("solar-only", "heater")
    await coordinator.async_shutdown()


async def test_heater_packet_preserves_delay_bits(hass: HomeAssistant) -> None:
    """The atomic heater write preserves only the observed delay flags."""
    coordinator = _make_coordinator(hass)
    coordinator._heat_source_byte = 0xEA
    controller = MagicMock()
    controller.connection.send_packet.return_value = True

    with patch.object(coordinator, "_new_controller", return_value=controller):
        assert coordinator._set_heater_modes("heater", "solar-priority") is True

    packet = controller.connection.send_packet.call_args.args[0]
    assert packet[10] == 0x9A
    assert packet[14] == 1 << 4


def test_temperature_confirmation_uses_protocol_precision() -> None:
    """Representable quarter-degree values confirm integer Fahrenheit requests."""
    assert CompoolStatusDataUpdateCoordinator._values_match(
        "desired_pool_temp_f", 85.1, 85.0
    )
    assert not CompoolStatusDataUpdateCoordinator._values_match(
        "desired_pool_temp_f", 86.0, 85.0
    )


async def test_later_change_does_not_reset_batch_timer(hass: HomeAssistant) -> None:
    """One-shot batch: a change after the first does not push the flush out."""
    coordinator = _make_coordinator(hass)
    coordinator.data = dict(MOCK_POOL_STATUS)

    with (
        patch.object(coordinator, "async_request_refresh", new=AsyncMock()),
        patch.object(coordinator, "_set_pool_temperature", return_value=True),
        patch.object(coordinator, "_set_spa_temperature", return_value=True),
    ):
        await coordinator.async_set_pool_temperature(85, "f")
        first_timer = coordinator._flush_unsub
        assert first_timer is not None

        # A later change joins the same batch without re-arming the timer.
        await coordinator.async_set_spa_temperature(99, "f")
        assert coordinator._flush_unsub is first_timer

    await coordinator.async_shutdown()


async def test_batch_reconciles_after_delay(hass: HomeAssistant) -> None:
    """The flush reconciles via a delayed re-poll, not an immediate (stale) one."""
    coordinator = _make_coordinator(hass)
    coordinator.data = dict(MOCK_POOL_STATUS)

    with (
        patch.object(coordinator, "async_refresh", new=AsyncMock()) as mock_refresh,
        patch.object(coordinator, "_set_pool_temperature", return_value=True),
    ):
        await coordinator.async_set_pool_temperature(90, "f")
        await flush_writes(hass)

        # Sent, but not reconciled yet: an immediate poll would read a stale
        # heartbeat and snap the value back, so the optimistic value stands.
        mock_refresh.assert_not_called()
        assert coordinator.data["desired_pool_temp_f"] == 90.0

        # Once the heartbeat has had time to catch up, a single re-poll runs.
        await flush_reconcile(hass)
        mock_refresh.assert_awaited_once()

    await coordinator.async_shutdown()


async def test_aux_off_optimistic_survives_flush(hass: HomeAssistant) -> None:
    """Turning an aux off keeps the optimistic 'off' after the toggle is sent.

    Reproduces the reported bug: the hardware toggled off but a stale immediate
    poll snapped the switch back to on. With no post-flush re-poll, the
    optimistic off (and the tracked aux state) stay off.
    """
    coordinator = _make_coordinator(hass)
    coordinator.data = dict(MOCK_POOL_STATUS)  # aux1_on starts True
    coordinator._aux_state = {1: True}

    with (
        patch.object(coordinator, "async_request_refresh", new=AsyncMock()),
        patch("custom_components.compool.coordinator.PoolController") as mock_ctrl,
    ):
        mock_ctrl.return_value.toggle_aux_equipment.return_value = True

        await coordinator.async_set_aux_equipment(1, False)
        assert coordinator.data["aux1_on"] is False  # optimistic off

        await flush_writes(hass)
        mock_ctrl.return_value.toggle_aux_equipment.assert_called_once_with(1)
        # Optimistic off stands and the tracked baseline agrees - no snap-back.
        assert coordinator.data["aux1_on"] is False
        assert coordinator._aux_state[1] is True
        assert coordinator._aux_unresolved[1].expected is False

    await coordinator.async_shutdown()


async def test_reconcile_overrides_optimistic_after_confirmation_window(
    hass: HomeAssistant,
) -> None:
    """A stale reconcile poll resets a wrong optimistic value after 30 seconds."""
    coordinator = _make_coordinator(hass)
    coordinator.data = dict(MOCK_POOL_STATUS)  # aux1_on starts True
    coordinator._aux_state = {1: True}

    # Hardware never actually changed (e.g. the write was not acknowledged).
    real_status = dict(MOCK_POOL_STATUS)

    with (
        patch.object(coordinator, "_set_aux_equipment", return_value=False),
        patch.object(
            coordinator, "_get_pool_status_with_retry", return_value=real_status
        ),
    ):
        await coordinator.async_set_aux_equipment(1, False)
        assert coordinator.data["aux1_on"] is False  # optimistic off

        await flush_writes(hass)
        await flush_reconcile(hass)

        # One stale heartbeat is ignored so the UI does not snap back before the
        # controller has had a fair chance to report the new state.
        assert coordinator.data["aux1_on"] is False
        assert coordinator.is_pending_confirmation("aux1_on") is True

        coordinator._pending_confirmation["aux1_on"].requested_at -= 31
        await flush_reconcile(hass)

        # The controller still reports aux1 on after the confirmation window,
        # so accept hardware truth.
        assert coordinator.data["aux1_on"] is True
        assert coordinator.is_pending_confirmation("aux1_on") is False

    await coordinator.async_shutdown()


async def test_confirmation_window_starts_after_successful_write(
    hass: HomeAssistant,
) -> None:
    """A slow queued write does not spend the stale-read guard before it is sent."""
    coordinator = _make_coordinator(hass)
    coordinator.data = dict(MOCK_POOL_STATUS)  # aux1_on starts True
    coordinator._aux_state = {1: True}

    with (
        patch.object(coordinator, "_set_aux_equipment", return_value=True),
        patch.object(
            coordinator,
            "_get_pool_status_with_retry",
            return_value=dict(MOCK_POOL_STATUS),
        ),
    ):
        await coordinator.async_set_aux_equipment(1, False)
        coordinator._pending_confirmation["aux1_on"].requested_at -= 31

        await flush_writes(hass)
        assert coordinator.is_pending_confirmation("aux1_on") is True

        await flush_reconcile(hass)

        assert coordinator.data["aux1_on"] is False
        assert coordinator.is_pending_confirmation("aux1_on") is True

    await coordinator.async_shutdown()


async def test_aux_off_survives_repeated_stale_on_polls(
    hass: HomeAssistant,
) -> None:
    """An off command remains optimistic while stale on polls are within window."""
    coordinator = _make_coordinator(hass)
    off_status = {**MOCK_POOL_STATUS, "aux1_on": False}
    on_status = {**MOCK_POOL_STATUS, "aux1_on": True}
    coordinator.data = dict(off_status)
    coordinator._aux_state = {1: False}

    with (
        patch.object(coordinator, "_set_aux_equipment", return_value=True),
        patch.object(
            coordinator,
            "_get_pool_status_with_retry",
            side_effect=[on_status, on_status, on_status, off_status],
        ),
    ):
        await coordinator.async_set_aux_equipment(1, True)
        assert coordinator.data["aux1_on"] is True

        confirmed_on = await coordinator._async_update_data()
        assert confirmed_on["aux1_on"] is True
        assert coordinator.is_pending_confirmation("aux1_on") is False
        assert coordinator._aux_state[1] is True

        await coordinator.async_set_aux_equipment(1, False)
        assert coordinator.data["aux1_on"] is False

        first_stale = await coordinator._async_update_data()
        assert first_stale["aux1_on"] is False
        assert coordinator.is_pending_confirmation("aux1_on") is True
        assert coordinator._aux_state[1] is True

        second_stale = await coordinator._async_update_data()
        assert second_stale["aux1_on"] is False
        assert coordinator.is_pending_confirmation("aux1_on") is True
        assert coordinator._aux_state[1] is True

        confirmed_off = await coordinator._async_update_data()
        assert confirmed_off["aux1_on"] is False
        assert coordinator.is_pending_confirmation("aux1_on") is False
        assert coordinator._aux_state[1] is False

    await coordinator.async_shutdown()


async def test_failed_write_keeps_optimistic_value(hass: HomeAssistant) -> None:
    """A failed send still leaves the optimistic value for the next poll to fix."""
    coordinator = _make_coordinator(hass)
    coordinator.data = dict(MOCK_POOL_STATUS)

    with (
        patch.object(coordinator, "async_request_refresh", new=AsyncMock()),
        patch.object(
            coordinator, "_set_pool_temperature", return_value=False
        ) as mock_set,
    ):
        await coordinator.async_set_pool_temperature(90, "f")
        assert coordinator.data["desired_pool_temp_f"] == 90.0  # optimistic

        await flush_writes(hass)
        mock_set.assert_called_once_with(90, "f")  # send was attempted

        # Optimistic value persists; the reconcile poll will fix it.
        assert coordinator.data["desired_pool_temp_f"] == 90.0

    await coordinator.async_shutdown()


async def test_aux_off_sends_single_toggle(hass: HomeAssistant) -> None:
    """Turning a currently-on aux off sends exactly one unconditional toggle."""
    coordinator = _make_coordinator(hass)
    coordinator._aux_state = {1: True}  # last poll: aux1 on

    with patch(
        "custom_components.compool.coordinator.PoolController"
    ) as mock_controller:
        instance = mock_controller.return_value
        instance.toggle_aux_equipment.return_value = True

        assert coordinator._set_aux_equipment(1, False) is True

        instance.toggle_aux_equipment.assert_called_once_with(1)
        # Observed state does not advance until a heartbeat confirms the toggle.
        assert coordinator._aux_state[1] is True
        assert coordinator._aux_unresolved[1].expected is False


async def test_aux_no_change_sends_nothing(hass: HomeAssistant) -> None:
    """Requesting the state an aux is already in sends no command."""
    coordinator = _make_coordinator(hass)
    coordinator._aux_state = {1: False}  # last poll: aux1 already off

    with patch(
        "custom_components.compool.coordinator.PoolController"
    ) as mock_controller:
        assert coordinator._set_aux_equipment(1, False) is True
        mock_controller.assert_not_called()  # no connection, no toggle


async def test_poll_captures_aux_state(hass: HomeAssistant) -> None:
    """Each successful poll records hardware-truth aux states as the baseline."""
    coordinator = _make_coordinator(hass)

    coordinator._capture_aux_state(dict(MOCK_POOL_STATUS))

    assert coordinator._aux_state[1] is True
    assert coordinator._aux_state[2] is False


async def test_poll_clears_pending_confirmation(hass: HomeAssistant) -> None:
    """A successful poll confirms keys that were updated optimistically."""
    coordinator = _make_coordinator(hass)
    coordinator.data = dict(MOCK_POOL_STATUS)

    with (
        patch.object(coordinator, "_set_aux_equipment", return_value=True),
        patch.object(
            coordinator,
            "_get_pool_status_with_retry",
            return_value={**MOCK_POOL_STATUS, "aux1_on": False},
        ),
    ):
        await coordinator.async_set_aux_equipment(1, False)
        assert coordinator.is_pending_confirmation("aux1_on") is True

        await coordinator._async_update_data()

    assert coordinator.is_pending_confirmation("aux1_on") is False

    await coordinator.async_shutdown()


async def test_stale_poll_preserves_optimistic_on(hass: HomeAssistant) -> None:
    """An off-to-on command is not undone by one stale off heartbeat."""
    coordinator = _make_coordinator(hass)
    off_status = {**MOCK_POOL_STATUS, "aux1_on": False}
    on_status = {**MOCK_POOL_STATUS, "aux1_on": True}
    coordinator.data = dict(off_status)
    coordinator._aux_state = {1: False}

    with (
        patch.object(coordinator, "_set_aux_equipment", return_value=True),
        patch.object(
            coordinator,
            "_get_pool_status_with_retry",
            side_effect=[off_status, on_status],
        ),
    ):
        await coordinator.async_set_aux_equipment(1, True)
        assert coordinator.data["aux1_on"] is True

        stale = await coordinator._async_update_data()
        assert stale["aux1_on"] is True
        assert coordinator._aux_state[1] is False
        assert coordinator.is_pending_confirmation("aux1_on") is True

        confirmed = await coordinator._async_update_data()
        assert confirmed["aux1_on"] is True
        assert coordinator.is_pending_confirmation("aux1_on") is False

    await coordinator.async_shutdown()


async def test_write_waits_for_bus_lock(hass: HomeAssistant) -> None:
    """A queued batch cannot reach the bus while the lock is held by a poll."""
    coordinator = _make_coordinator(hass)
    coordinator.data = dict(MOCK_POOL_STATUS)

    with (
        patch.object(coordinator, "async_request_refresh", new=AsyncMock()),
        patch.object(
            coordinator, "_set_pool_temperature", return_value=True
        ) as mock_set,
    ):
        # Hold the bus as a concurrent poll would, then start a flush directly.
        await coordinator._io_lock.acquire()
        coordinator._pending_writes["pool_temp"] = PendingWrite(
            lambda: coordinator._set_pool_temperature(85, "f"),
            {"desired_pool_temp_f": 1},
        )
        task = asyncio.ensure_future(coordinator._flush_batch(None))
        await asyncio.sleep(0)  # let the flush reach the lock and block

        assert not task.done()
        mock_set.assert_not_called()

        coordinator._io_lock.release()
        await task
        mock_set.assert_called_once_with(85, "f")

    await coordinator.async_shutdown()


async def test_waiting_batch_keeps_latest_value(hass: HomeAssistant) -> None:
    """Queued values remain replaceable until the worker acquires the bus."""
    coordinator = _make_coordinator(hass)
    coordinator.data = dict(MOCK_POOL_STATUS)

    with patch.object(
        coordinator, "_set_pool_temperature", return_value=True
    ) as mock_set:
        await coordinator.async_set_pool_temperature(80, "f")
        await coordinator._io_lock.acquire()
        coordinator._flush_unsub()
        task = asyncio.create_task(coordinator._flush_batch(None))
        await asyncio.sleep(0)

        await coordinator.async_set_pool_temperature(90, "f")
        coordinator._io_lock.release()
        await task

    mock_set.assert_called_once_with(90, "f")
    await coordinator.async_shutdown()


async def test_shutdown_cancels_pending_writes(hass: HomeAssistant) -> None:
    """A pending batched write is dropped on unload."""
    coordinator = _make_coordinator(hass)
    coordinator.data = dict(MOCK_POOL_STATUS)

    with patch.object(
        coordinator, "_set_pool_temperature", return_value=True
    ) as mock_set:
        await coordinator.async_set_pool_temperature(85, "f")
        await coordinator.async_shutdown()

        await flush_writes(hass)
        mock_set.assert_not_called()


@pytest.mark.parametrize(("aux_num", "initial"), [(1, True), (2, False)])
async def test_aux_does_not_retry_unconfirmed_toggle(
    hass: HomeAssistant, aux_num: int, initial: bool
) -> None:
    """An acknowledged but unconfirmed toggle is not repeated from a stale poll."""
    coordinator = _make_coordinator(hass)
    key = f"aux{aux_num}_on"
    status = {**MOCK_POOL_STATUS, key: initial}
    coordinator.data = dict(status)
    coordinator._capture_aux_state(status)

    with patch("custom_components.compool.coordinator.PoolController") as mock_ctrl:
        mock_ctrl.return_value.get_status.return_value = dict(status)
        mock_ctrl.return_value.toggle_aux_equipment.side_effect = [True, True]
        await coordinator.async_set_aux_equipment(aux_num, not initial)
        await flush_writes(hass)
        await flush_reconcile(hass)

        assert coordinator.data[key] is not initial
        assert coordinator._aux_state[aux_num] is initial
        await coordinator.async_set_aux_equipment(aux_num, not initial)
        await flush_writes(hass)
        assert mock_ctrl.return_value.toggle_aux_equipment.call_count == 1

    await coordinator.async_shutdown()


def _unacknowledged_toggle_setup(
    hass: HomeAssistant, aux_num: int, initial: bool
) -> CompoolStatusDataUpdateCoordinator:
    """Create a coordinator whose aux circuit is reported in ``initial`` state."""
    coordinator = _make_coordinator(hass)
    status = {**MOCK_POOL_STATUS, f"aux{aux_num}_on": initial}
    coordinator.data = dict(status)
    coordinator._capture_aux_state(status)
    return coordinator


@pytest.mark.parametrize(("aux_num", "initial"), [(1, True), (2, False)])
async def test_unacknowledged_toggle_resends_after_reconcile(
    hass: HomeAssistant, aux_num: int, initial: bool
) -> None:
    """An unacknowledged toggle still unapplied at the reconcile poll is re-sent."""
    coordinator = _unacknowledged_toggle_setup(hass, aux_num, initial)

    with patch("custom_components.compool.coordinator.PoolController") as mock_ctrl:
        mock_ctrl.return_value.get_status.return_value = dict(coordinator.data)
        mock_ctrl.return_value.toggle_aux_equipment.side_effect = [False, True]
        await coordinator.async_set_aux_equipment(aux_num, not initial)
        await flush_writes(hass)
        await flush_reconcile(hass)
        await flush_writes(hass)
        assert mock_ctrl.return_value.toggle_aux_equipment.call_count == 2

    await coordinator.async_shutdown()


async def test_unacknowledged_toggle_not_resent_by_other_polls(
    hass: HomeAssistant,
) -> None:
    """Only the post-write reconcile poll resolves an unacknowledged toggle."""
    coordinator = _unacknowledged_toggle_setup(hass, 1, True)

    with patch("custom_components.compool.coordinator.PoolController") as mock_ctrl:
        mock_ctrl.return_value.get_status.return_value = dict(coordinator.data)
        mock_ctrl.return_value.toggle_aux_equipment.return_value = False
        await coordinator.async_set_aux_equipment(1, False)
        await flush_writes(hass)
        await coordinator.async_refresh()
        await flush_writes(hass)
        assert mock_ctrl.return_value.toggle_aux_equipment.call_count == 1

    await coordinator.async_shutdown()


async def test_unacknowledged_toggle_fast_resend_happens_once(
    hass: HomeAssistant,
) -> None:
    """A toggle that keeps failing is re-sent early once, not in a tight loop."""
    coordinator = _unacknowledged_toggle_setup(hass, 1, True)

    with patch("custom_components.compool.coordinator.PoolController") as mock_ctrl:
        mock_ctrl.return_value.get_status.return_value = dict(coordinator.data)
        mock_ctrl.return_value.toggle_aux_equipment.return_value = False
        await coordinator.async_set_aux_equipment(1, False)
        for _ in range(3):
            await flush_writes(hass)
            await flush_reconcile(hass)
        assert mock_ctrl.return_value.toggle_aux_equipment.call_count == 2

    await coordinator.async_shutdown()


async def test_aux_poll_before_flush_does_not_skip_write(hass: HomeAssistant) -> None:
    """A poll during batching cannot turn a queued off command into a no-op."""
    coordinator = _make_coordinator(hass)
    coordinator.data = dict(MOCK_POOL_STATUS)
    coordinator._capture_aux_state(MOCK_POOL_STATUS)

    with patch("custom_components.compool.coordinator.PoolController") as mock_ctrl:
        mock_ctrl.return_value.get_status.return_value = dict(MOCK_POOL_STATUS)
        mock_ctrl.return_value.toggle_aux_equipment.return_value = True
        await coordinator.async_set_aux_equipment(1, False)
        await coordinator.async_refresh()
        assert coordinator.data["aux1_on"] is False
        await flush_writes(hass)
        mock_ctrl.return_value.toggle_aux_equipment.assert_called_once_with(1)

    await coordinator.async_shutdown()
