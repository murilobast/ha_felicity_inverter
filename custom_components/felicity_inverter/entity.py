"""Shared entity base for the Felicity inverter integration."""

from __future__ import annotations

from os.path import basename

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import FelicityInverterDataCoordinator


class FelicityInverterEntity(CoordinatorEntity[FelicityInverterDataCoordinator]):
    """Common entity behavior for Felicity inverter entities."""

    def __init__(self, coordinator: FelicityInverterDataCoordinator, entry_id: str, unique_base: str) -> None:
        super().__init__(coordinator)
        self._entry_id = entry_id
        self._unique_base = unique_base
        self._attr_unique_id = f"{entry_id}_{unique_base}"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info for the configured device."""
        connection = self.coordinator.data["connection"]
        if self.coordinator.device_type == "battery":
            host = connection.get("host") or self.coordinator.wifi_battery_host or "battery"
            port = connection.get("port") or self.coordinator.wifi_battery_port or 53970
            subtype = connection.get("subtype")
            name = connection.get("name") or f"Local Felicity Battery {host}"
            return DeviceInfo(
                identifiers={(DOMAIN, f"battery:{host}:{port}")},
                manufacturer="Felicity Solar",
                model=f"FLA WiFi Battery {subtype}" if subtype else "FLA WiFi Battery",
                name=name,
                serial_number=connection.get("device_sn"),
            )

        device = connection["device"]
        name = connection.get("name") or f"Local Felicity Inverter {basename(device)}"
        return DeviceInfo(
            identifiers={(DOMAIN, device)},
            manufacturer="Felicity Solar",
            model="RS232 Inverter",
            name=name,
        )
