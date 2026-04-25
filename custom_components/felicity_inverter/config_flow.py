"""Config flow for the Felicity inverter integration."""

from __future__ import annotations

import glob
import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers.selector import selector

from .client import FelicityInverterClient, FelicityInverterError
from .const import (
    CONF_DEVICE_TYPE,
    CONF_DEVICE,
    CONF_SCAN_INTERVAL,
    CONF_WIFI_BATTERY_HOST,
    CONF_WIFI_BATTERY_PORT,
    DEFAULT_BATTERY_NAME,
    DEFAULT_NAME,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_WIFI_BATTERY_PORT,
    DEVICE_TYPE_BATTERY,
    DEVICE_TYPE_INVERTER,
    DOMAIN,
    SERIAL_DEVICE_GLOB,
)
from .wifi_battery import FelicityWifiBatteryClient

LOGGER = logging.getLogger(__name__)


def discover_serial_devices() -> list[str]:
    """Return serial devices that look like inverter adapters."""
    return sorted(glob.glob(SERIAL_DEVICE_GLOB))


async def validate_input(hass, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""
    if data[CONF_DEVICE_TYPE] == DEVICE_TYPE_INVERTER:
        client = FelicityInverterClient(
            device=data[CONF_DEVICE],
        )
        try:
            payload = await hass.async_add_executor_job(client.read_all)
        except FelicityInverterError as err:
            raise CannotConnect from err
    else:
        battery_client = FelicityWifiBatteryClient(
            host=data[CONF_WIFI_BATTERY_HOST],
            port=int(data.get(CONF_WIFI_BATTERY_PORT, DEFAULT_WIFI_BATTERY_PORT)),
        )
        try:
            payload = await hass.async_add_executor_job(battery_client.read_all)
        except FelicityInverterError as err:
            raise CannotConnect from err

    return {
        "title": data[CONF_NAME],
        "payload": payload,
    }


class FelicityInverterConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Felicity inverter."""

    VERSION = 2

    def __init__(self) -> None:
        self._device_type: str | None = None

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Choose which kind of Felicity device to configure."""
        if user_input is not None:
            self._device_type = user_input[CONF_DEVICE_TYPE]
            if self._device_type == DEVICE_TYPE_INVERTER:
                return await self.async_step_inverter()
            return await self.async_step_battery()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_DEVICE_TYPE): selector(
                        {
                            "select": {
                                "options": [
                                    {"label": "Serial inverter", "value": DEVICE_TYPE_INVERTER},
                                    {"label": "WiFi battery", "value": DEVICE_TYPE_BATTERY},
                                ],
                                "mode": "list",
                            }
                        }
                    )
                }
            ),
        )

    async def async_step_inverter(self, user_input: dict[str, Any] | None = None):
        """Configure a serial inverter entry."""
        errors: dict[str, str] = {}
        devices = discover_serial_devices()

        if user_input is not None:
            user_input[CONF_DEVICE_TYPE] = DEVICE_TYPE_INVERTER
            unique_id = f"{DEVICE_TYPE_INVERTER}:{user_input[CONF_DEVICE]}"
            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()

            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:  # pragma: no cover - defensive guard for HA runtime
                LOGGER.exception("Unexpected exception while validating Felicity inverter config")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title=info["title"], data=user_input)

        data_schema: dict[Any, Any] = {
            vol.Required(CONF_NAME, default=DEFAULT_NAME): str,
            vol.Required(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): vol.All(
                int, vol.Range(min=5, max=3600)
            ),
        }

        if devices:
            data_schema[vol.Required(CONF_DEVICE, default=devices[0])] = selector(
                {
                    "select": {
                        "options": [{"label": device, "value": device} for device in devices],
                        "mode": "dropdown",
                    }
                }
            )
        else:
            data_schema[vol.Required(CONF_DEVICE)] = str

        return self.async_show_form(
            step_id="inverter",
            data_schema=vol.Schema(data_schema),
            description_placeholders={
                "device_count": str(len(devices)),
                "device_glob": SERIAL_DEVICE_GLOB,
            },
            errors=errors,
        )

    async def async_step_battery(self, user_input: dict[str, Any] | None = None):
        """Configure a WiFi battery entry."""
        errors: dict[str, str] = {}

        if user_input is not None:
            user_input[CONF_DEVICE_TYPE] = DEVICE_TYPE_BATTERY
            unique_id = f"{DEVICE_TYPE_BATTERY}:{user_input[CONF_WIFI_BATTERY_HOST]}"
            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()

            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:  # pragma: no cover - defensive guard for HA runtime
                LOGGER.exception("Unexpected exception while validating Felicity battery config")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="battery",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_NAME, default=DEFAULT_BATTERY_NAME): str,
                    vol.Required(CONF_WIFI_BATTERY_HOST): str,
                    vol.Required(CONF_WIFI_BATTERY_PORT, default=DEFAULT_WIFI_BATTERY_PORT): vol.All(
                        int, vol.Range(min=1, max=65535)
                    ),
                    vol.Required(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): vol.All(
                        int, vol.Range(min=5, max=3600)
                    ),
                }
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Return the options flow."""
        return FelicityInverterOptionsFlowHandler()


class FelicityInverterOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options for the Felicity inverter integration."""

    def __init__(self) -> None:
        """Initialize the options flow."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        """Manage the integration options."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        device_type = self.config_entry.data.get(CONF_DEVICE_TYPE, DEVICE_TYPE_INVERTER)
        if device_type == DEVICE_TYPE_BATTERY:
            return self.async_show_form(
                step_id="init",
                data_schema=vol.Schema(
                    {
                        vol.Required(
                            CONF_SCAN_INTERVAL,
                            default=self.config_entry.options.get(
                                CONF_SCAN_INTERVAL,
                                self.config_entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                            ),
                        ): vol.All(int, vol.Range(min=5, max=3600)),
                        vol.Required(
                            CONF_WIFI_BATTERY_HOST,
                            default=self.config_entry.options.get(
                                CONF_WIFI_BATTERY_HOST,
                                self.config_entry.data.get(CONF_WIFI_BATTERY_HOST, ""),
                            ),
                        ): str,
                        vol.Required(
                            CONF_WIFI_BATTERY_PORT,
                            default=self.config_entry.options.get(
                                CONF_WIFI_BATTERY_PORT,
                                self.config_entry.data.get(CONF_WIFI_BATTERY_PORT, DEFAULT_WIFI_BATTERY_PORT),
                            ),
                        ): vol.All(int, vol.Range(min=1, max=65535)),
                    }
                ),
            )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SCAN_INTERVAL,
                        default=self.config_entry.options.get(
                            CONF_SCAN_INTERVAL,
                            self.config_entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                        ),
                    ): vol.All(int, vol.Range(min=5, max=3600)),
                }
            ),
        )


class CannotConnect(Exception):
    """Error to indicate we cannot connect."""
