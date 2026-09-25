"""Tests for the bounded Compool serial transport."""

from __future__ import annotations

from collections import deque
from contextlib import nullcontext
import time
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


def _heartbeat_packet() -> bytes:
    """Build a 24-byte controller heartbeat."""
    payload = bytes((0xFF, 0xAA, 0x0F, 0x1B, 0x02, 0x10)) + bytes(16)
    return payload + calculate_checksum(payload).to_bytes(2, "big")


def _recording_transport(
    reads: list[bytes],
) -> tuple[ReliableSerialConnection, MagicMock, list[str]]:
    """Create a transport whose connection logs reads and writes in order."""
    events: list[str] = []
    responses = deque(reads)
    connection = MagicMock()

    def read(_size: int) -> bytes:
        events.append("read")
        return responses.popleft() if responses else b""

    connection.read.side_effect = read
    connection.write.side_effect = lambda _data: events.append("write")
    transport = ReliableSerialConnection("socket://127.0.0.1:8899", 9600)
    transport.open = MagicMock(return_value=nullcontext(connection))
    return transport, connection, events


def test_send_waits_for_heartbeat_before_writing() -> None:
    """Without a recent heartbeat, the command is sent right after the next one."""
    transport, _connection, events = _recording_transport(
        [_heartbeat_packet(), _ack_packet()]
    )

    assert transport.send_packet(b"command")
    assert events.index("write") == 1


def test_send_right_after_heartbeat_does_not_wait() -> None:
    """A command following a fresh heartbeat is sent immediately."""
    transport, _connection, events = _recording_transport([_ack_packet()])
    transport._heartbeat_seen_at = time.monotonic()

    assert transport.send_packet(b"command")
    assert events[0] == "write"


def test_heartbeat_from_status_read_allows_immediate_send() -> None:
    """A heartbeat seen by a preceding status read lets the command go at once."""
    transport, _connection, events = _recording_transport(
        [_heartbeat_packet(), _ack_packet()]
    )

    assert next(transport.read_packets(timeout=1.0)) == _heartbeat_packet()
    assert transport.send_packet(b"command")
    assert events[:2] == ["read", "write"]


def test_send_proceeds_when_no_heartbeat_arrives() -> None:
    """A silent bus delays the command by at most the heartbeat wait."""
    transport, connection, _events = _recording_transport([])

    with patch(
        "custom_components.compool.transport.time.monotonic",
        side_effect=(10.0, 13.1, 13.1, 13.2, 20.0),
    ):
        assert not transport.send_packet(b"command")

    connection.write.assert_called_once_with(b"command")


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
