"""Local TCP client for Felicity WiFi battery telemetry."""

from __future__ import annotations

import json
import socket
from typing import Any

from .client import FelicityInverterError
from .const import DEFAULT_TIMEOUT, DEFAULT_WIFI_BATTERY_PORT, WIFI_BATTERY_COMMAND

INVALID_VALUES = {None, 65535, 32767, -32768}


def _flatten(values: Any) -> list[Any]:
    flattened: list[Any] = []
    if isinstance(values, list):
        for item in values:
            flattened.extend(_flatten(item))
    else:
        flattened.append(values)
    return flattened


def _valid_numbers(values: Any) -> list[int | float]:
    valid: list[int | float] = []
    for item in _flatten(values):
        if isinstance(item, (int, float)) and item not in INVALID_VALUES:
            valid.append(item)
    return valid


def _first_number(values: Any, scale: float = 1.0) -> float | None:
    numbers = _valid_numbers(values)
    if not numbers:
        return None
    return float(numbers[0]) * scale


def _scaled_min(values: Any, scale: float = 1.0) -> float | None:
    numbers = _valid_numbers(values)
    if not numbers:
        return None
    return float(min(numbers)) * scale


def _scaled_max(values: Any, scale: float = 1.0) -> float | None:
    numbers = _valid_numbers(values)
    if not numbers:
        return None
    return float(max(numbers)) * scale


def _round_or_none(value: float | None, precision: int = 3) -> float | None:
    if value is None:
        return None
    return round(value, precision)


class FelicityWifiBatteryClient:
    """Client for the Felicity battery built-in WiFi endpoint."""

    def __init__(
        self,
        host: str,
        port: int = DEFAULT_WIFI_BATTERY_PORT,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout

    def read_all(self) -> dict[str, Any]:
        """Fetch and normalize the battery telemetry JSON."""
        raw = self._query()
        return self._normalize_payload(raw)

    def _query(self) -> dict[str, Any]:
        try:
            with socket.create_connection((self.host, self.port), timeout=self.timeout) as sock:
                sock.settimeout(self.timeout)
                sock.sendall(f"{WIFI_BATTERY_COMMAND}\n".encode("utf-8"))

                chunks: list[bytes] = []
                while True:
                    try:
                        data = sock.recv(4096)
                    except socket.timeout:
                        break
                    if not data:
                        break
                    chunks.append(data)
        except OSError as err:
            raise FelicityInverterError(
                f"Unable to connect to Felicity WiFi battery at {self.host}:{self.port}: {err}"
            ) from err

        payload = b"".join(chunks).decode("utf-8", errors="ignore").strip()
        if not payload:
            raise FelicityInverterError(
                f"Empty response from Felicity WiFi battery at {self.host}:{self.port}"
            )

        try:
            return json.loads(payload)
        except json.JSONDecodeError as err:
            raise FelicityInverterError(
                f"Invalid JSON from Felicity WiFi battery at {self.host}:{self.port}: {err}"
            ) from err

    def _normalize_payload(self, raw: dict[str, Any]) -> dict[str, Any]:
        voltage = _first_number(raw.get("Batt"), scale=0.001)
        current = _first_number(raw.get("Batt"), scale=1.0)
        if current is not None:
            batt_values = _valid_numbers(raw.get("Batt"))
            if len(batt_values) > 1:
                current = float(batt_values[1])

        soc = _first_number(raw.get("Batsoc"), scale=0.01)
        if soc is None:
            soc = _first_number(raw.get("BatsocList"), scale=0.01)

        temp_values = _valid_numbers(raw.get("BtemList")) or _valid_numbers(raw.get("BTemp"))
        temperature_min = _round_or_none(_scaled_min(temp_values, scale=0.1), 1)
        temperature_max = _round_or_none(_scaled_max(temp_values, scale=0.1), 1)

        cell_voltages_mv = _valid_numbers(raw.get("BatcelList"))
        cell_voltage_min = _round_or_none(_scaled_min(cell_voltages_mv, scale=0.001), 3)
        cell_voltage_max = _round_or_none(_scaled_max(cell_voltages_mv, scale=0.001), 3)
        cell_voltage_delta = None
        if cell_voltage_min is not None and cell_voltage_max is not None:
            cell_voltage_delta = round(cell_voltage_max - cell_voltage_min, 3)

        cell_extremes = raw.get("BMaxMin", [])
        max_cell_index = None
        min_cell_index = None
        if isinstance(cell_extremes, list) and len(cell_extremes) > 1 and isinstance(cell_extremes[1], list):
            indices = cell_extremes[1]
            if len(indices) > 0 and isinstance(indices[0], int):
                max_cell_index = indices[0]
            if len(indices) > 1 and isinstance(indices[1], int):
                min_cell_index = indices[1]

        power = None
        if voltage is not None and current is not None:
            power = round(voltage * current, 0)

        batt_list = raw.get("BattList", [])
        parallel_modules = 0
        if isinstance(batt_list, list) and batt_list and isinstance(batt_list[0], list):
            parallel_modules = len(_valid_numbers(batt_list[0]))

        fields = {
            "soc": _round_or_none(soc, 1),
            "voltage": _round_or_none(voltage, 2),
            "current": _round_or_none(current, 1),
            "power": power,
            "temperature_min": temperature_min,
            "temperature_max": temperature_max,
            "cell_voltage_min": cell_voltage_min,
            "cell_voltage_max": cell_voltage_max,
            "cell_voltage_delta": cell_voltage_delta,
            "cell_count": len(cell_voltages_mv),
            "max_cell_index": max_cell_index,
            "min_cell_index": min_cell_index,
            "state_code": raw.get("Bstate"),
            "fault_code": raw.get("Bfault"),
            "warn_code": raw.get("Bwarn"),
            "estate_code": raw.get("Estate"),
            "parallel_modules": parallel_modules,
        }

        return {
            "connection": {
                "host": self.host,
                "port": self.port,
                "wifi_sn": raw.get("wifiSN"),
                "device_sn": raw.get("DevSN"),
                "type": raw.get("Type"),
                "subtype": raw.get("SubType"),
            },
            "fields": fields,
            "raw": raw,
        }
