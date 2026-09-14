"""Tests for the bounded Compool serial transport."""

from __future__ import annotations

from collections import deque
from unittest.mock import MagicMock, patch

from pycompool.protocol import calculate_checksum

from custom_components.compool.transport import ReliableSerialConnection


def _ack_packet(*, valid_checksum: bool = True) -> bytes:
    """Build a positive Compool acknowledgment packet."""
    payload = bytes((0xFF, 0xAA, 0x01, 0x00, 0x01, 0x01, 0x82))
    checksum = calculate_checksum(payload)
    if not valid_checksum:
        checksum += 1
    return payload + checksum.to_bytes(2, "big")


def test_ack_requires_valid_checksum() -> None:
    """A structurally valid ACK with a bad checksum is rejected."""
    assert ReliableSerialConnection._is_valid_ack(_ack_packet())
    assert not ReliableSerialConnection._is_valid_ack(_ack_packet(valid_checksum=False))


def test_ack_parser_skips_malformed_packet() -> None:
    """Malformed traffic cannot masquerade as a command acknowledgment."""
    connection = MagicMock()
    responses = deque((_ack_packet(valid_checksum=False), _ack_packet()))
    connection.read.side_effect = lambda _size: responses.popleft()

    transport = ReliableSerialConnection("socket://127.0.0.1:8899", 9600)

    assert transport._wait_for_ack(connection, 0.1)
    assert connection.read.call_count == 2


def test_ack_deadline_survives_continuous_invalid_traffic() -> None:
    """Unrelated serial traffic cannot extend the overall ACK deadline."""
    connection = MagicMock()
    connection.read.return_value = b"unrelated traffic"
    transport = ReliableSerialConnection("socket://127.0.0.1:8899", 9600)

    with patch(
        "custom_components.compool.transport.time.monotonic",
        side_effect=(10.0, 10.01, 10.11),
    ):
        assert not transport._wait_for_ack(connection, 0.1)

    connection.read.assert_called_once_with(32)
