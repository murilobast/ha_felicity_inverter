"""The Felicity inverter integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .client import FelicityInverterClient
from .const import (
    CONF_DEVICE_TYPE,
    CONF_DEVICE,
    CONF_SCAN_INTERVAL,
    CONF_WIFI_BATTERY_HOST,
    CONF_WIFI_BATTERY_PORT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_WIFI_BATTERY_PORT,
    DEVICE_TYPE_BATTERY,
    DEVICE_TYPE_INVERTER,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import FelicityInverterDataCoordinator
from .wifi_battery import FelicityWifiBatteryClient


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the integration from YAML."""
    return True


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate older config entries to the device-type model."""
    if entry.version >= 2:
        return True

    data = {**entry.data}
    data.setdefault(CONF_DEVICE_TYPE, DEVICE_TYPE_INVERTER)
    new_unique_id = entry.unique_id
    if data[CONF_DEVICE_TYPE] == DEVICE_TYPE_INVERTER and CONF_DEVICE in data:
        new_unique_id = f"{DEVICE_TYPE_INVERTER}:{data[CONF_DEVICE]}"
    hass.config_entries.async_update_entry(entry, data=data, unique_id=new_unique_id, version=2)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Felicity inverter from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    device_type = entry.data.get(CONF_DEVICE_TYPE, DEVICE_TYPE_INVERTER)
    client = None
    wifi_battery_client = None
    if device_type == DEVICE_TYPE_INVERTER:
        client = FelicityInverterClient(
            device=entry.data[CONF_DEVICE],
        )
    else:
        wifi_battery_host = entry.options.get(
            CONF_WIFI_BATTERY_HOST,
            entry.data.get(CONF_WIFI_BATTERY_HOST, ""),
        ).strip()
        wifi_battery_client = FelicityWifiBatteryClient(
            host=wifi_battery_host,
            port=int(
                entry.options.get(
                    CONF_WIFI_BATTERY_PORT,
                    entry.data.get(CONF_WIFI_BATTERY_PORT, DEFAULT_WIFI_BATTERY_PORT),
                )
            ),
        )
    coordinator = FelicityInverterDataCoordinator(
        hass=hass,
        client=client,
        wifi_battery_client=wifi_battery_client,
        device_type=device_type,
        scan_interval=entry.options.get(
            CONF_SCAN_INTERVAL,
            entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        ),
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator
    entry.runtime_data = coordinator
    if CONF_NAME in entry.data:
        coordinator.data["connection"]["name"] = entry.data[CONF_NAME]
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the config entry when its options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
