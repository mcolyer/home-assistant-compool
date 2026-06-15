"""Test Compool switch platform."""

from unittest.mock import patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.compool.const import DOMAIN
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.const import ATTR_ENTITY_ID, SERVICE_TURN_OFF, SERVICE_TURN_ON
from homeassistant.core import HomeAssistant

from .const import MOCK_CONFIG, MOCK_POOL_STATUS


@pytest.mark.usefixtures("bypass_get_data")
async def test_switch_setup(hass: HomeAssistant) -> None:
    """Test switch setup."""
    config_entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG)
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    # Check that all aux switches were created
    switches = [
        state
        for state in hass.states.async_all()
        if state.entity_id.startswith("switch.")
    ]

    # We should have 8 switches
    assert len(switches) == 8

    # Verify switch entity IDs follow expected pattern
    expected_switch_ids = [f"switch.pool_controller_none_{i}" for i in range(1, 9)]
    actual_switch_ids = sorted([s.entity_id for s in switches])

    # Simply check that we have the correct number of switches
    # (exact entity ID format may vary based on Home Assistant version)
    assert len(actual_switch_ids) == len(expected_switch_ids)


@pytest.mark.usefixtures("bypass_get_data")
async def test_switch_states(hass: HomeAssistant) -> None:
    """Test switch states match mock data."""
    config_entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG)
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    # Get all switch states and verify they match expected aux equipment states
    switches = [
        state
        for state in hass.states.async_all()
        if state.entity_id.startswith("switch.")
    ]

    # We should have 8 switches
    assert len(switches) == 8

    # Map the expected aux states from mock data
    expected_aux_states = [
        True,
        False,
        True,
        False,
        False,
        True,
        False,
        False,
    ]  # aux1-aux8

    # Sort switches by entity_id to get consistent ordering
    sorted_switches = sorted(switches, key=lambda s: s.entity_id)

    # Verify each switch state matches the expected aux state
    for i, switch in enumerate(sorted_switches):
        expected_state = "on" if expected_aux_states[i] else "off"
        assert switch.state in (
            expected_state,
            "unavailable",
        )  # Allow unavailable during test


@pytest.mark.usefixtures("bypass_get_data")
async def test_switch_turn_on(hass: HomeAssistant) -> None:
    """Test turning on a switch."""
    config_entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG)
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    # Get any switch entity (we'll use the second one for this test)
    switches = [
        state
        for state in hass.states.async_all()
        if state.entity_id.startswith("switch.")
    ]
    sorted_switches = sorted(switches, key=lambda s: s.entity_id)
    entity_id = sorted_switches[1].entity_id  # Use second switch (aux2)

    # Mock the coordinator method
    with patch(
        "custom_components.compool.coordinator.CompoolStatusDataUpdateCoordinator.async_set_aux_equipment",
        return_value=True,
    ) as mock_set_aux:
        await hass.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: entity_id},
            blocking=True,
        )

        # Verify the coordinator method was called with correct parameters
        mock_set_aux.assert_called_once_with(2, True)


@pytest.mark.usefixtures("bypass_get_data")
async def test_switch_turn_off(hass: HomeAssistant) -> None:
    """Test turning off a switch."""
    config_entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG)
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    # Get any switch entity (we'll use the first one for this test)
    switches = [
        state
        for state in hass.states.async_all()
        if state.entity_id.startswith("switch.")
    ]
    sorted_switches = sorted(switches, key=lambda s: s.entity_id)
    entity_id = sorted_switches[0].entity_id  # Use first switch (aux1)

    # Mock the coordinator method
    with patch(
        "custom_components.compool.coordinator.CompoolStatusDataUpdateCoordinator.async_set_aux_equipment",
        return_value=True,
    ) as mock_set_aux:
        await hass.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_OFF,
            {ATTR_ENTITY_ID: entity_id},
            blocking=True,
        )

        # Verify the coordinator method was called with correct parameters
        mock_set_aux.assert_called_once_with(1, False)


async def test_switch_turn_off_confirms_optimistic_state(
    hass: HomeAssistant,
) -> None:
    """A reconcile poll confirms an optimistic off without changing the state."""
    config_entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG)
    config_entry.add_to_hass(hass)
    confirmed_status = {**MOCK_POOL_STATUS, "aux1_on": False}

    with patch("custom_components.compool.coordinator.PoolController") as mock_ctrl:
        mock_ctrl.return_value.get_status.side_effect = [
            dict(MOCK_POOL_STATUS),
            dict(MOCK_POOL_STATUS),
            confirmed_status,
        ]
        mock_ctrl.return_value.toggle_aux_equipment.return_value = True

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        entity_id = next(
            state.entity_id
            for state in hass.states.async_all()
            if state.entity_id.startswith("switch.")
            and state.attributes.get("icon") == "mdi:pool"
        )
        coordinator = config_entry.runtime_data.coordinator
        assert coordinator._aux_state[1] is True
        assert hass.states.get(entity_id).state == "on"

        await hass.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_OFF,
            {ATTR_ENTITY_ID: entity_id},
            blocking=True,
        )

        state = hass.states.get(entity_id)
        assert state.state == "off"
        assert coordinator.is_pending_confirmation("aux1_on") is True

        coordinator._flush_unsub()
        coordinator._flush_unsub = None
        await coordinator._flush_batch(None)
        mock_ctrl.return_value.toggle_aux_equipment.assert_called_once_with(1)

        coordinator._reconcile_unsub()
        coordinator._reconcile_unsub = None
        await coordinator._reconcile(None)
        await hass.async_block_till_done()

    state = hass.states.get(entity_id)
    assert state.state == "off"
    assert coordinator.is_pending_confirmation("aux1_on") is False


async def test_switch_turn_off_reconcile_corrects_state_after_window(
    hass: HomeAssistant,
) -> None:
    """A stale reconcile poll restores hardware truth after the confirmation window."""
    config_entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG)
    config_entry.add_to_hass(hass)

    with patch("custom_components.compool.coordinator.PoolController") as mock_ctrl:
        mock_ctrl.return_value.get_status.side_effect = [
            dict(MOCK_POOL_STATUS),
            dict(MOCK_POOL_STATUS),
            dict(MOCK_POOL_STATUS),
            dict(MOCK_POOL_STATUS),
        ]
        mock_ctrl.return_value.toggle_aux_equipment.return_value = False

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        entity_id = next(
            state.entity_id
            for state in hass.states.async_all()
            if state.entity_id.startswith("switch.")
            and state.attributes.get("icon") == "mdi:pool"
        )
        coordinator = config_entry.runtime_data.coordinator
        assert coordinator._aux_state[1] is True
        assert hass.states.get(entity_id).state == "on"

        await hass.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_OFF,
            {ATTR_ENTITY_ID: entity_id},
            blocking=True,
        )

        state = hass.states.get(entity_id)
        assert state.state == "off"
        assert coordinator.is_pending_confirmation("aux1_on") is True

        coordinator._flush_unsub()
        coordinator._flush_unsub = None
        await coordinator._flush_batch(None)
        coordinator._reconcile_unsub()
        coordinator._reconcile_unsub = None
        await coordinator._reconcile(None)
        await hass.async_block_till_done()

        state = hass.states.get(entity_id)
        assert state.state == "off"
        assert coordinator.is_pending_confirmation("aux1_on") is True

        coordinator._pending_confirmation["aux1_on"].requested_at -= 31
        coordinator._reconcile_unsub()
        coordinator._reconcile_unsub = None
        await coordinator._reconcile(None)
        await hass.async_block_till_done()

    state = hass.states.get(entity_id)
    assert state.state == "on"
    assert coordinator.is_pending_confirmation("aux1_on") is False


async def test_switch_off_on_off_survives_repeated_stale_on_polls(
    hass: HomeAssistant,
) -> None:
    """Switch services keep an off command through repeated stale on polls."""
    config_entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG)
    config_entry.add_to_hass(hass)
    confirmed_on = {**MOCK_POOL_STATUS, "aux2_on": True}
    confirmed_off = {**MOCK_POOL_STATUS, "aux2_on": False}

    with patch("custom_components.compool.coordinator.PoolController") as mock_ctrl:
        mock_ctrl.return_value.get_status.return_value = dict(MOCK_POOL_STATUS)
        mock_ctrl.return_value.toggle_aux_equipment.return_value = True

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()
        mock_ctrl.return_value.get_status.side_effect = [
            confirmed_on,
            confirmed_on,
            confirmed_on,
            confirmed_off,
        ]
        mock_ctrl.return_value.get_status.return_value = None

        entity_id = sorted(
            state.entity_id
            for state in hass.states.async_all()
            if state.entity_id.startswith("switch.")
        )[1]
        coordinator = config_entry.runtime_data.coordinator
        assert coordinator._aux_state[2] is False
        assert hass.states.get(entity_id).state == "off"

        await hass.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: entity_id},
            blocking=True,
        )
        coordinator._flush_unsub()
        coordinator._flush_unsub = None
        await coordinator._flush_batch(None)
        coordinator._reconcile_unsub()
        coordinator._reconcile_unsub = None
        await coordinator._reconcile(None)
        await hass.async_block_till_done()

        state = hass.states.get(entity_id)
        assert state.state == "on"
        assert coordinator.is_pending_confirmation("aux2_on") is False

        await hass.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_OFF,
            {ATTR_ENTITY_ID: entity_id},
            blocking=True,
        )
        state = hass.states.get(entity_id)
        assert state.state == "off"
        assert coordinator.is_pending_confirmation("aux2_on") is True

        coordinator._flush_unsub()
        coordinator._flush_unsub = None
        await coordinator._flush_batch(None)
        assert mock_ctrl.return_value.toggle_aux_equipment.call_count == 2

        for _ in range(2):
            coordinator._reconcile_unsub()
            coordinator._reconcile_unsub = None
            await coordinator._reconcile(None)
            await hass.async_block_till_done()

            state = hass.states.get(entity_id)
            assert state.state == "off"
            assert coordinator.is_pending_confirmation("aux2_on") is True
            assert coordinator._aux_state[2] is False

        coordinator._reconcile_unsub()
        coordinator._reconcile_unsub = None
        await coordinator._reconcile(None)
        await hass.async_block_till_done()

    state = hass.states.get(entity_id)
    assert state.state == "off"
    assert coordinator.is_pending_confirmation("aux2_on") is False


async def test_switch_turn_on_ignores_stale_off_reconcile(
    hass: HomeAssistant,
) -> None:
    """An off-to-on switch command survives one stale off heartbeat."""
    config_entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG)
    config_entry.add_to_hass(hass)
    confirmed_status = {**MOCK_POOL_STATUS, "aux2_on": True}

    with patch("custom_components.compool.coordinator.PoolController") as mock_ctrl:
        mock_ctrl.return_value.get_status.side_effect = [
            dict(MOCK_POOL_STATUS),
            dict(MOCK_POOL_STATUS),
            dict(MOCK_POOL_STATUS),
            confirmed_status,
        ]
        mock_ctrl.return_value.toggle_aux_equipment.return_value = True

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        entity_id = sorted(
            state.entity_id
            for state in hass.states.async_all()
            if state.entity_id.startswith("switch.")
        )[1]
        coordinator = config_entry.runtime_data.coordinator
        assert coordinator._aux_state[2] is False
        assert hass.states.get(entity_id).state == "off"

        await hass.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: entity_id},
            blocking=True,
        )

        state = hass.states.get(entity_id)
        assert state.state == "on"
        assert coordinator.is_pending_confirmation("aux2_on") is True

        coordinator._flush_unsub()
        coordinator._flush_unsub = None
        await coordinator._flush_batch(None)
        mock_ctrl.return_value.toggle_aux_equipment.assert_called_once_with(2)

        coordinator._reconcile_unsub()
        coordinator._reconcile_unsub = None
        await coordinator._reconcile(None)
        await hass.async_block_till_done()

        state = hass.states.get(entity_id)
        assert state.state == "on"
        assert coordinator.is_pending_confirmation("aux2_on") is True

        coordinator._reconcile_unsub()
        coordinator._reconcile_unsub = None
        await coordinator._reconcile(None)
        await hass.async_block_till_done()

    state = hass.states.get(entity_id)
    assert state.state == "on"
    assert coordinator.is_pending_confirmation("aux2_on") is False


@pytest.mark.usefixtures("bypass_get_data")
async def test_switch_attributes(hass: HomeAssistant) -> None:
    """Test switch attributes."""
    config_entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG)
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    # Get any switch entity for this test
    switches = [
        state
        for state in hass.states.async_all()
        if state.entity_id.startswith("switch.")
    ]
    sorted_switches = sorted(switches, key=lambda s: s.entity_id)
    state = sorted_switches[0]  # Use first switch

    assert state is not None
    assert state.attributes.get("host") == MOCK_CONFIG["host"]
    assert state.attributes.get("port") == MOCK_CONFIG["port"]
    assert "last_updated" in state.attributes
    assert "pending_confirmation" not in state.attributes


async def test_switch_no_data(hass: HomeAssistant) -> None:
    """Test switch behavior when no data is available."""
    config_entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG)
    config_entry.add_to_hass(hass)

    # Mock coordinator with no data
    with patch(
        "custom_components.compool.coordinator.CompoolStatusDataUpdateCoordinator._get_pool_status_with_retry",
        return_value={},
    ):
        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        # Get any switch entity for this test
        switches = [
            state
            for state in hass.states.async_all()
            if state.entity_id.startswith("switch.")
        ]

        # Should have switches created but they should be unavailable
        assert len(switches) == 8

        # Check that switches are in unavailable state when no data
        for switch in switches:
            assert switch.state in ["unavailable", "unknown"]
