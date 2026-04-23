"""Coordinator for Felicity inverter data polling."""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .client import FelicityInverterClient, FelicityInverterError
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

LOGGER = logging.getLogger(__name__)


class FelicityInverterDataCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Fetch and cache Felicity inverter data."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: FelicityInverterClient,
        scan_interval: int = DEFAULT_SCAN_INTERVAL,
    ) -> None:
        super().__init__(
            hass,
            LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )
        self.client = client
        self._lock = asyncio.Lock()

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            async with self._lock:
                return await self.hass.async_add_executor_job(self.client.read_all)
        except FelicityInverterError as err:
            raise UpdateFailed(str(err)) from err

    async def async_set_mode(self, mode: str) -> None:
        async with self._lock:
            data = await self.hass.async_add_executor_job(self.client.set_mode, mode)
        self.async_set_updated_data(data)

    async def async_set_max_ac_charge_current(self, amps: int) -> None:
        async with self._lock:
            data = await self.hass.async_add_executor_job(self.client.set_max_ac_charge_current, amps)
        self.async_set_updated_data(data)

    async def async_write_setting(self, field_name: str, value: int | float) -> None:
        async with self._lock:
            data = await self.hass.async_add_executor_job(self.client.write_setting, field_name, value)
        self.async_set_updated_data(data)
