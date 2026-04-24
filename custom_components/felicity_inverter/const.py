"""Constants for the Felicity inverter integration."""

from __future__ import annotations

from homeassistant.const import Platform

DOMAIN = "felicity_inverter"
DEFAULT_NAME = "Local Felicity Inverter"
DEFAULT_BATTERY_NAME = "Local Felicity Battery"
DEFAULT_SCAN_INTERVAL = 30
DEFAULT_TIMEOUT = 2.0
DEFAULT_WIFI_BATTERY_PORT = 53970
SERIAL_BAUD_RATE = 2400
SERIAL_DEVICE_GLOB = "/dev/ttyUSB*"
WIFI_BATTERY_COMMAND = "wifilocalMonitor:get dev real infor"

CONF_DEVICE = "device"
CONF_DEVICE_TYPE = "device_type"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_WIFI_BATTERY_HOST = "wifi_battery_host"
CONF_WIFI_BATTERY_PORT = "wifi_battery_port"

DEVICE_TYPE_INVERTER = "inverter"
DEVICE_TYPE_BATTERY = "battery"

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.SELECT, Platform.NUMBER]

MODES: dict[str, tuple[int, int]] = {
    "grid_charge": (0, 2),
    "grid_only": (0, 0),
    "battery": (2, 3),
}

MODE_BY_REGISTER_PAIR = {value: key for key, value in MODES.items()}
