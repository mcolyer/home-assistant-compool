"""Bounded, validated transport helpers for Compool."""

from __future__ import annotations

import time
from typing import Any

from pycompool.connection import ConnectionError, SerialConnection
from pycompool.protocol import (
    ACK_OPCODE,
    ACK_PREFIX,
    ACK_TYPE_OK,
    SYNC,
    calculate_checksum,
)


class ReliableSerialConnection(SerialConnection):
    """Serial connection with operation deadlines and validated ACK packets."""

    def _create_connection(self) -> Any:
        """Create a connection with bounded writes as well as bounded reads."""
        connection = super()._create_connection()
        connection.write_timeout = 2.0
        return connection

    def send_packet(self, packet_data: bytes, ack_timeout: float = 2.0) -> bool:
        """Send a packet after discarding responses from older transactions."""
        try:
            with self.open() as connection:
                connection.reset_input_buffer()
                connection.write(packet_data)
                connection.flush()
                return self._wait_for_ack(connection, ack_timeout)
        except Exception as ex:
            raise ConnectionError(f"Failed to send packet: {ex}") from ex

    def _wait_for_ack(self, connection: Any, timeout: float) -> bool:
        """Wait until an overall deadline for a complete, valid ACK packet."""
        deadline = time.monotonic() + timeout
        buffer = bytearray()

        while (remaining := deadline - time.monotonic()) > 0:
            connection.timeout = min(0.3, remaining)
            if chunk := connection.read(32):
                buffer.extend(chunk)

            while (index := buffer.find(ACK_PREFIX)) >= 0:
                if len(buffer) - index < 9:
                    break
                packet = bytes(buffer[index : index + 9])
                del buffer[: index + 9]
                if self._is_valid_ack(packet):
                    return True

            if len(buffer) > 64:
                del buffer[:-8]

        return False

    @staticmethod
    def _is_valid_ack(packet: bytes) -> bool:
        """Return whether a packet is a checksummed positive acknowledgment."""
        if len(packet) != 9 or packet[:7] != ACK_PREFIX + b"\x00\x01\x01\x82":
            return False
        expected_checksum = calculate_checksum(packet[:-2])
        actual_checksum = int.from_bytes(packet[-2:], "big")
        return (
            packet[4] == ACK_OPCODE
            and packet[6] == ACK_TYPE_OK
            and actual_checksum == expected_checksum
        )

    def read_packets(self, packet_size: int = 24, timeout: float = 1.0) -> Any:
        """Yield packets until one overall monotonic deadline expires."""
        deadline = time.monotonic() + timeout
        try:
            with self.open() as connection:
                buffer = bytearray()
                while (remaining := deadline - time.monotonic()) > 0:
                    connection.timeout = min(0.3, remaining)
                    if not (chunk := connection.read(packet_size)):
                        continue
                    buffer.extend(chunk)

                    while (sync_index := buffer.find(SYNC)) >= 0:
                        if sync_index:
                            del buffer[:sync_index]
                        if len(buffer) < packet_size:
                            break
                        yield bytes(buffer[:packet_size])
                        del buffer[:packet_size]

                    if len(buffer) > 1000:
                        del buffer[:-100]
        except Exception as ex:
            raise ConnectionError(f"Failed to read packets: {ex}") from ex
