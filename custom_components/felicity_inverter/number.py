"""Number platform for writable Felicity inverter settings."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.number import NumberDeviceClass, NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfElectricCurrent, UnitOfElectricPotential
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .client import FelicityInverterError
from .const import DOMAIN
from .coordinator import FelicityInverterDataCoordinator
from .entity import FelicityInverterEntity


@dataclass(frozen=True)
class FelicityNumberSpec:
    field_name: str
    name: str
    native_min_value: float
    native_max_value: float
    native_step: float
    device_class: NumberDeviceClass | None = None
    entity_category: EntityCategory | None = None
    native_unit_of_measurement: str | None = None
    mode: NumberMode = NumberMode.BOX


NUMBER_SPECS = (
    FelicityNumberSpec(
        field_name="discharge_cutoff_voltage",
        name="Discharge Cutoff Voltage",
        native_min_value=40.0,
        native_max_value=60.0,
        native_step=0.1,
        device_class=NumberDeviceClass.VOLTAGE,
        entity_category=EntityCategory.CONFIG,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
    ),
    FelicityNumberSpec(
        field_name="bulk_charge_voltage",
        name="Bulk Charge Voltage",
        native_min_value=40.0,
        native_max_value=60.0,
        native_step=0.1,
        device_class=NumberDeviceClass.VOLTAGE,
        entity_category=EntityCategory.CONFIG,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
    ),
    FelicityNumberSpec(
        field_name="float_charge_voltage",
        name="Float Charge Voltage",
        native_min_value=40.0,
        native_max_value=60.0,
        native_step=0.1,
        device_class=NumberDeviceClass.VOLTAGE,
        entity_category=EntityCategory.CONFIG,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
    ),
    FelicityNumberSpec(
        field_name="max_charge_current",
        name="Max Charge Current",
        native_min_value=0,
        native_max_value=100,
        native_step=1,
        device_class=NumberDeviceClass.CURRENT,
        entity_category=EntityCategory.CONFIG,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
    ),
    FelicityNumberSpec(
        field_name="max_ac_charge_current",
        name="Max Grid Charge Current",
        native_min_value=0,
        native_max_value=100,
        native_step=1,
        device_class=NumberDeviceClass.CURRENT,
        entity_category=EntityCategory.CONFIG,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
    ),
    FelicityNumberSpec(
        field_name="back_to_grid_voltage",
        name="Back To Grid Voltage",
        native_min_value=40.0,
        native_max_value=60.0,
        native_step=0.1,
        device_class=NumberDeviceClass.VOLTAGE,
        entity_category=EntityCategory.CONFIG,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
    ),
    FelicityNumberSpec(
        field_name="back_to_battery_voltage",
        name="Back To Battery Voltage",
        native_min_value=40.0,
        native_max_value=60.0,
        native_step=0.1,
        device_class=NumberDeviceClass.VOLTAGE,
        entity_category=EntityCategory.CONFIG,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up writable number entities for the inverter."""
    coordinator: FelicityInverterDataCoordinator = hass.data[DOMAIN][entry.entry_id]
    if not coordinator.has_inverter:
        return
    async_add_entities(FelicityWritableNumber(coordinator, entry.entry_id, spec) for spec in NUMBER_SPECS)


class FelicityWritableNumber(FelicityInverterEntity, NumberEntity):
    """Expose a writable inverter setting as a number entity."""

    def __init__(
        self,
        coordinator: FelicityInverterDataCoordinator,
        entry_id: str,
        spec: FelicityNumberSpec,
    ) -> None:
        super().__init__(coordinator, entry_id, f"number_{spec.field_name}")
        self._spec = spec
        self._attr_has_entity_name = True
        self._attr_name = spec.name
        self._attr_native_min_value = spec.native_min_value
        self._attr_native_max_value = spec.native_max_value
        self._attr_native_step = spec.native_step
        self._attr_device_class = spec.device_class
        self._attr_entity_category = spec.entity_category
        self._attr_native_unit_of_measurement = spec.native_unit_of_measurement
        self._attr_mode = spec.mode

    @property
    def native_value(self) -> float:
        """Return the current register value."""
        register = self._register_data
        return float(register["value"])

    async def async_set_native_value(self, value: float) -> None:
        """Write a new register value."""
        try:
            await self.coordinator.async_write_setting(self._spec.field_name, value)
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
        return self.coordinator.data["settings"]["registers_by_name"][self._spec.field_name]
