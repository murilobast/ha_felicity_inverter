"""Raw Modbus RTU client for the Felicity inverter serial port."""

from __future__ import annotations

import os
import select
import termios
import time
from dataclasses import asdict, dataclass
from typing import Any

from .const import DEFAULT_TIMEOUT, MODES, SERIAL_BAUD_RATE
from .register_map import (
    FIELD_ENUMS,
    SETTINGS_BLOCK_COUNT,
    SETTINGS_BLOCK_START,
    SETTINGS_REGISTERS,
    SIGNED_REGISTERS,
    STATUS_BLOCK_COUNT,
    STATUS_BLOCK_START,
    STATUS_REGISTERS,
)

SLAVE_ADDRESS = 0x01
OUTPUT_PRIORITY_REGISTER = 0x212A
CHARGE_PRIORITY_REGISTER = 0x212C
MAX_AC_CHARGE_CURRENT_REGISTER = 0x2130

BAUD_MAP = {
    1200: termios.B1200,
    2400: termios.B2400,
    4800: termios.B4800,
    9600: termios.B9600,
    19200: termios.B19200,
    38400: termios.B38400,
}


class FelicityInverterError(Exception):
    """Base exception for the inverter client."""


@dataclass(frozen=True)
class DecodedRegister:
    address: int
    address_hex: str
    name: str
    raw: int
    value: float | int
    unit: str
    note: str
    mapped: bool
    signed: bool
    label: str | None = None


def crc16(data: bytes) -> int:
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc


def to_signed_16(raw: int) -> int:
    return raw if raw < 0x8000 else raw - 0x10000


def build_read_request(start_address: int, count: int) -> bytes:
    frame = bytes(
        [
            SLAVE_ADDRESS,
            0x03,
            (start_address >> 8) & 0xFF,
            start_address & 0xFF,
            (count >> 8) & 0xFF,
            count & 0xFF,
        ]
    )
    crc = crc16(frame)
    return frame + bytes([crc & 0xFF, (crc >> 8) & 0xFF])


def build_write_request(address: int, value: int) -> bytes:
    frame = bytes(
        [
            SLAVE_ADDRESS,
            0x06,
            (address >> 8) & 0xFF,
            address & 0xFF,
            (value >> 8) & 0xFF,
            value & 0xFF,
        ]
    )
    crc = crc16(frame)
    return frame + bytes([crc & 0xFF, (crc >> 8) & 0xFF])


def recv_exactly(fd: int, size: int, timeout: float) -> bytes:
    buffer = bytearray()
    deadline = time.monotonic() + timeout

    while len(buffer) < size:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise FelicityInverterError("Timed out waiting for inverter response")

        readable, _, _ = select.select([fd], [], [], remaining)
        if not readable:
            raise FelicityInverterError("Timed out waiting for inverter response")

        chunk = os.read(fd, size - len(buffer))
        if not chunk:
            raise FelicityInverterError("Serial device closed while reading response")
        buffer.extend(chunk)

    return bytes(buffer)


class FelicityInverterClient:
    """Client for reading and writing inverter registers over the local serial port."""

    def __init__(
        self,
        device: str,
        baud_rate: int = SERIAL_BAUD_RATE,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        self.device = device
        self.baud_rate = baud_rate
        self.timeout = timeout

    def read_all(self) -> dict[str, Any]:
        with self._open_serial() as serial_fd:
            status = self._read_block(
                serial_fd, STATUS_BLOCK_START, STATUS_BLOCK_COUNT, STATUS_REGISTERS, "status"
            )
            settings = self._read_block(
                serial_fd, SETTINGS_BLOCK_START, SETTINGS_BLOCK_COUNT, SETTINGS_REGISTERS, "settings"
            )
        return self._payload(status, settings)

    def set_mode(self, mode: str) -> dict[str, Any]:
        if mode not in MODES:
            raise FelicityInverterError(f"Unsupported mode: {mode}")

        output_value, charge_value = MODES[mode]

        with self._open_serial() as serial_fd:
            self._write_single_register(serial_fd, OUTPUT_PRIORITY_REGISTER, output_value)
            self._write_single_register(serial_fd, CHARGE_PRIORITY_REGISTER, charge_value)
            time.sleep(2.0)
            status = self._read_block(
                serial_fd, STATUS_BLOCK_START, STATUS_BLOCK_COUNT, STATUS_REGISTERS, "status"
            )
            settings = self._read_block(
                serial_fd, SETTINGS_BLOCK_START, SETTINGS_BLOCK_COUNT, SETTINGS_REGISTERS, "settings"
            )

        return self._payload(status, settings)

    def set_max_ac_charge_current(self, amps: int) -> dict[str, Any]:
        if amps < 0:
            raise FelicityInverterError("max_ac_charge_current must be non-negative")

        return self.write_setting("max_ac_charge_current", amps)

    def write_setting(self, field_name: str, value: int | float) -> dict[str, Any]:
        address, encoded = self._encode_setting_value(field_name, value)

        with self._open_serial() as serial_fd:
            self._write_single_register(serial_fd, address, encoded)
            time.sleep(1.0)
            status = self._read_block(
                serial_fd, STATUS_BLOCK_START, STATUS_BLOCK_COUNT, STATUS_REGISTERS, "status"
            )
            settings = self._read_block(
                serial_fd, SETTINGS_BLOCK_START, SETTINGS_BLOCK_COUNT, SETTINGS_REGISTERS, "settings"
            )

        return self._payload(status, settings)

    def _encode_setting_value(self, field_name: str, value: int | float) -> tuple[int, int]:
        for address, (name, scale, _unit, _note) in SETTINGS_REGISTERS.items():
            if name != field_name:
                continue

            if scale == 1:
                encoded = int(round(float(value)))
            else:
                encoded = int(round(float(value) / float(scale)))

            if encoded < 0 or encoded > 0xFFFF:
                raise FelicityInverterError(f"Value out of range for {field_name}: {value}")

            return address, encoded

        raise FelicityInverterError(f"Unknown writable setting: {field_name}")

    def _payload(self, status: dict[str, Any], settings: dict[str, Any]) -> dict[str, Any]:
        return {
            "connection": {
                "device": self.device,
                "baud_rate": self.baud_rate,
                "slave_address": SLAVE_ADDRESS,
            },
            "status": status,
            "settings": settings,
        }

    class _SerialConnection:
        """Context manager for a configured serial file descriptor."""

        def __init__(self, device: str, baud_rate: int) -> None:
            self.device = device
            self.baud_rate = baud_rate
            self.fd: int | None = None

        def __enter__(self) -> int:
            try:
                fd = os.open(self.device, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
            except OSError as err:
                raise FelicityInverterError(f"Unable to open serial device {self.device}: {err}") from err

            try:
                attrs = termios.tcgetattr(fd)
                attrs[0] = 0
                attrs[1] = 0
                attrs[2] = termios.CS8 | termios.CREAD | termios.CLOCAL
                attrs[3] = 0

                baud = BAUD_MAP[self.baud_rate]
                attrs[4] = baud
                attrs[5] = baud
                attrs[6][termios.VMIN] = 0
                attrs[6][termios.VTIME] = 0

                termios.tcsetattr(fd, termios.TCSANOW, attrs)
                termios.tcflush(fd, termios.TCIOFLUSH)
            except Exception:
                os.close(fd)
                raise

            self.fd = fd
            return fd

        def __exit__(self, exc_type, exc, tb) -> None:
            if self.fd is not None:
                os.close(self.fd)
                self.fd = None

    def _open_serial(self) -> _SerialConnection:
        if self.baud_rate not in BAUD_MAP:
            raise FelicityInverterError(f"Unsupported baud rate: {self.baud_rate}")
        return self._SerialConnection(self.device, self.baud_rate)

    def _read_block(
        self,
        serial_fd: int,
        start_address: int,
        count: int,
        metadata_by_address: dict[int, tuple[str, float | int, str, str]],
        block_name: str,
    ) -> dict[str, Any]:
        words = self._read_holding_registers(serial_fd, start_address, count)
        registers = self._decode_block(start_address, words, metadata_by_address)
        return {
            "block": block_name,
            "start_address": f"0x{start_address:04X}",
            "count": count,
            "fields": self._build_field_map(registers),
            "registers": [asdict(register) for register in registers],
            "registers_by_name": {register.name: asdict(register) for register in registers if register.mapped},
        }

    def _read_holding_registers(self, serial_fd: int, start_address: int, count: int) -> list[int]:
        response = self._send_request(serial_fd, build_read_request(start_address, count))
        byte_count = response[2]
        expected = count * 2
        if byte_count != expected:
            raise FelicityInverterError(f"Unexpected byte count: got {byte_count}, expected {expected}")
        data = response[3 : 3 + byte_count]
        return [(data[index] << 8) | data[index + 1] for index in range(0, len(data), 2)]

    def _write_single_register(self, serial_fd: int, address: int, value: int) -> None:
        response = self._send_request(serial_fd, build_write_request(address, value))
        echoed_address = (response[2] << 8) | response[3]
        echoed_value = (response[4] << 8) | response[5]
        if echoed_address != address or echoed_value != value:
            raise FelicityInverterError(
                f"Write echo mismatch for 0x{address:04X}: address=0x{echoed_address:04X} value={echoed_value}"
            )

    def _send_request(self, serial_fd: int, frame: bytes) -> bytes:
        termios.tcflush(serial_fd, termios.TCIFLUSH)
        os.write(serial_fd, frame)
        termios.tcdrain(serial_fd)

        header = recv_exactly(serial_fd, 3, self.timeout)
        slave, function_code, third = header

        if slave != SLAVE_ADDRESS:
            raise FelicityInverterError(f"Unexpected slave address in response: 0x{slave:02X}")

        if function_code & 0x80:
            rest = recv_exactly(serial_fd, 2, self.timeout)
            payload = header + rest
            self._validate_crc(payload)
            raise FelicityInverterError(
                f"Modbus exception: fn=0x{function_code:02X} code=0x{rest[0]:02X}"
            )

        if function_code == 0x06:
            payload = header + recv_exactly(serial_fd, 5, self.timeout)
            self._validate_crc(payload)
            return payload

        if function_code != 0x03:
            raise FelicityInverterError(f"Unsupported function code in response: 0x{function_code:02X}")

        payload = header + recv_exactly(serial_fd, third + 2, self.timeout)
        self._validate_crc(payload)
        return payload

    def _validate_crc(self, frame: bytes) -> None:
        expected = crc16(frame[:-2])
        actual = frame[-2] | (frame[-1] << 8)
        if actual != expected:
            raise FelicityInverterError(f"CRC mismatch: got 0x{actual:04X}, expected 0x{expected:04X}")

    def _decode_block(
        self,
        start_address: int,
        words: list[int],
        metadata_by_address: dict[int, tuple[str, float | int, str, str]],
    ) -> list[DecodedRegister]:
        return [
            self._decode_register(start_address + offset, raw_value, metadata_by_address.get(start_address + offset))
            for offset, raw_value in enumerate(words)
        ]

    def _decode_register(
        self,
        address: int,
        raw_value: int,
        metadata: tuple[str, float | int, str, str] | None,
    ) -> DecodedRegister:
        signed = address in SIGNED_REGISTERS
        interpreted = to_signed_16(raw_value) if signed else raw_value

        if metadata is None:
            return DecodedRegister(
                address=address,
                address_hex=f"0x{address:04X}",
                name=f"reg_0x{address:04X}",
                raw=raw_value,
                value=interpreted,
                unit="",
                note="unmapped register",
                mapped=False,
                signed=signed,
            )

        name, scale, unit, note = metadata
        value = interpreted * scale
        if isinstance(value, float) and value.is_integer():
            value = int(value)

        enum_map = FIELD_ENUMS.get(name)
        label = enum_map.get(interpreted) if enum_map else None

        return DecodedRegister(
            address=address,
            address_hex=f"0x{address:04X}",
            name=name,
            raw=raw_value,
            value=value,
            unit=unit,
            note=note,
            mapped=True,
            signed=signed,
            label=label,
        )

    @staticmethod
    def _build_field_map(registers: list[DecodedRegister]) -> dict[str, Any]:
        fields: dict[str, Any] = {}
        for register in registers:
            fields[register.name] = register.value
            if register.label is not None:
                fields[f"{register.name}_label"] = register.label
        return fields
