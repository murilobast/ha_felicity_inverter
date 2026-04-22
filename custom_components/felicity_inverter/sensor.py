"""Sensor platform for the Felicity inverter integration."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfPower,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import FelicityInverterDataCoordinator
from .entity import FelicityInverterEntity
from .register_map import SETTINGS_REGISTERS, STATUS_REGISTERS


@dataclass(frozen=True)
class FelicitySensorDescription:
    block: str
    address: int
    field_name: str
    unit: str
    note: str
    entity_category: EntityCategory | None = None
    device_class: SensorDeviceClass | None = None
    state_class: SensorStateClass | None = None
    suggested_display_precision: int | None = None


STATUS_SENSOR_META = {
    "battery_voltage": (SensorDeviceClass.VOLTAGE, SensorStateClass.MEASUREMENT, 2),
    "battery_current": (SensorDeviceClass.CURRENT, SensorStateClass.MEASUREMENT, 0),
    "battery_power": (SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, 0),
    "output_voltage": (SensorDeviceClass.VOLTAGE, SensorStateClass.MEASUREMENT, 1),
    "grid_voltage": (SensorDeviceClass.VOLTAGE, SensorStateClass.MEASUREMENT, 1),
    "load_watts": (SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, 0),
    "load_percentage": (None, SensorStateClass.MEASUREMENT, 0),
    "pv_voltage": (SensorDeviceClass.VOLTAGE, SensorStateClass.MEASUREMENT, 1),
    "pv_power": (SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, 0),
}

SETTINGS_SENSOR_META = {
    "discharge_cutoff_voltage": (SensorDeviceClass.VOLTAGE, None, 1),
    "bulk_charge_voltage": (SensorDeviceClass.VOLTAGE, None, 1),
    "float_charge_voltage": (SensorDeviceClass.VOLTAGE, None, 1),
    "max_charge_current": (SensorDeviceClass.CURRENT, None, 0),
    "max_ac_charge_current": (SensorDeviceClass.CURRENT, None, 0),
    "back_to_grid_voltage": (SensorDeviceClass.VOLTAGE, None, 1),
    "back_to_battery_voltage": (SensorDeviceClass.VOLTAGE, None, 1),
}

UNIT_MAP = {
    "%": PERCENTAGE,
    "A": UnitOfElectricCurrent.AMPERE,
    "V": UnitOfElectricPotential.VOLT,
    "W": UnitOfPower.WATT,
}


def _friendly_name(field_name: str) -> str:
    return field_name.replace("_", " ").replace("Pv", "PV").title().replace("Pv", "PV")


def _build_descriptions() -> list[FelicitySensorDescription]:
    descriptions: list[FelicitySensorDescription] = []

    for address, (field_name, _, unit, note) in sorted(STATUS_REGISTERS.items()):
        device_class, state_class, precision = STATUS_SENSOR_META.get(field_name, (None, None, None))
        descriptions.append(
            FelicitySensorDescription(
                block="status",
                address=address,
                field_name=field_name,
                unit=unit,
                note=note,
                device_class=device_class,
                state_class=state_class,
                suggested_display_precision=precision,
            )
        )

    for address, (field_name, _, unit, note) in sorted(SETTINGS_REGISTERS.items()):
        device_class, state_class, precision = SETTINGS_SENSOR_META.get(field_name, (None, None, None))
        descriptions.append(
            FelicitySensorDescription(
                block="settings",
                address=address,
                field_name=field_name,
                unit=unit,
                note=note,
                entity_category=EntityCategory.CONFIG,
                device_class=device_class,
                state_class=state_class,
                suggested_display_precision=precision,
            )
        )

    return descriptions


SENSOR_DESCRIPTIONS = _build_descriptions()


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Felicity inverter sensors."""
    coordinator: FelicityInverterDataCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        FelicityRegisterSensor(coordinator, entry.entry_id, description) for description in SENSOR_DESCRIPTIONS
    )


class FelicityRegisterSensor(FelicityInverterEntity, SensorEntity):
    """Expose a mapped register as a Home Assistant sensor."""

    entity_description: FelicitySensorDescription

    def __init__(
        self,
        coordinator: FelicityInverterDataCoordinator,
        entry_id: str,
        description: FelicitySensorDescription,
    ) -> None:
        super().__init__(coordinator, entry_id, f"{description.block}_{description.field_name}")
        self.entity_description = description
        self._attr_has_entity_name = True
        self._attr_name = _friendly_name(description.field_name)
        self._attr_native_unit_of_measurement = UNIT_MAP.get(description.unit)
        self._attr_device_class = description.device_class
        self._attr_state_class = description.state_class
        self._attr_entity_category = description.entity_category
        self._attr_suggested_display_precision = description.suggested_display_precision

    @property
    def native_value(self):
        """Return the current sensor value."""
        register = self._register_data
        return register["label"] if register.get("label") is not None else register["value"]

    @property
    def extra_state_attributes(self) -> dict[str, str | int | float | bool]:
        """Return additional diagnostics for the register."""
        register = self._register_data
        return {
            "register_address": register["address_hex"],
            "register_raw": register["raw"],
            "register_signed": register["signed"],
            "register_note": register["note"],
        }

    @property
    def _register_data(self) -> dict:
        return self.coordinator.data[self.entity_description.block]["registers_by_name"][self.entity_description.field_name]
