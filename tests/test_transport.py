"""Tests for the bounded Compool serial transport."""

from __future__ import annotations

from collections import deque
from unittest.mock import MagicMock, patch

from pycompool.protocol import calculate_checksum

from custom_components.compool.transport import ReliableSerialConnection


def _ack_packet(*, valid_checksum: bool = True, version: int = 0x00) -> bytes:
    """Build a positive Compool acknowledgment packet."""
    payload = bytes((0xFF, 0xAA, 0x01, version, 0x01, 0x01, 0x82))
    checksum = calculate_checksum(payload)
    if not valid_checksum:
        checksum += 1
    return payload + checksum.to_bytes(2, "big")


def test_ack_requires_valid_checksum() -> None:
    """A structurally valid ACK with a bad checksum is rejected."""
    assert ReliableSerialConnection._is_valid_ack(_ack_packet())
    assert not ReliableSerialConnection._is_valid_ack(_ack_packet(valid_checksum=False))


def test_ack_accepts_any_firmware_version() -> None:
    """The version byte reflects controller firmware and is not validated."""
    # Captured verbatim from a controller on firmware 27 (0x1b).
    captured = bytes.fromhex("ff aa 01 1b 01 01 82 02 49")
    assert ReliableSerialConnection._is_valid_ack(captured)
    assert ReliableSerialConnection._is_valid_ack(_ack_packet(version=0x1B))
    assert not ReliableSerialConnection._is_valid_ack(
        _ack_packet(version=0x1B, valid_checksum=False)
    )


def test_ack_rejects_other_destinations_and_non_ok_types() -> None:
    """Only OK acknowledgments addressed to this client are accepted."""
    other_destination = bytes((0xFF, 0xAA, 0x0F, 0x1B, 0x01, 0x01, 0x82))
    non_ok_type = bytes((0xFF, 0xAA, 0x01, 0x1B, 0x01, 0x01, 0x00))
    for payload in (other_destination, non_ok_type):
        packet = payload + calculate_checksum(payload).to_bytes(2, "big")
        assert not ReliableSerialConnection._is_valid_ack(packet)


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
