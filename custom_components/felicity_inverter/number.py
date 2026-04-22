"""Number platform for writable Felicity inverter settings."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfElectricCurrent
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .client import FelicityInverterError
from .const import DOMAIN
from .coordinator import FelicityInverterDataCoordinator
from .entity import FelicityInverterEntity


@dataclass(frozen=True, kw_only=True)
class FelicityNumberDescription(NumberEntityDescription):
    field_name: str


NUMBER_DESCRIPTIONS = (
    FelicityNumberDescription(
        key="max_ac_charge_current",
        field_name="max_ac_charge_current",
        name="Max Grid Charge Current",
        native_min_value=0,
        native_max_value=100,
        native_step=1,
        device_class=NumberDeviceClass.CURRENT,
        entity_category=EntityCategory.CONFIG,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up writable number entities for the inverter."""
    coordinator: FelicityInverterDataCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        FelicityWritableNumber(coordinator, entry.entry_id, description) for description in NUMBER_DESCRIPTIONS
    )


class FelicityWritableNumber(FelicityInverterEntity, NumberEntity):
    """Expose a writable inverter setting as a number entity."""

    entity_description: FelicityNumberDescription

    def __init__(
        self,
        coordinator: FelicityInverterDataCoordinator,
        entry_id: str,
        description: FelicityNumberDescription,
    ) -> None:
        super().__init__(coordinator, entry_id, f"number_{description.field_name}")
        self.entity_description = description
        self._attr_has_entity_name = True

    @property
    def native_value(self) -> float:
        """Return the current register value."""
        register = self._register_data
        return float(register["value"])

    async def async_set_native_value(self, value: float) -> None:
        """Write a new register value."""
        try:
            await self.coordinator.async_set_max_ac_charge_current(int(value))
        except FelicityInverterError as err:
            raise HomeAssistantError(str(err)) from err

    @property
    def extra_state_attributes(self) -> dict[str, str | int | float | bool]:
        """Return diagnostic details about the backing register."""
        register = self._register_data
        return {
            "register_address": register["address_hex"],
            "register_raw": register["raw"],
            "register_signed": register["signed"],
            "register_note": register["note"],
        }

    @property
    def _register_data(self) -> dict:
        return self.coordinator.data["settings"]["registers_by_name"][self.entity_description.field_name]
