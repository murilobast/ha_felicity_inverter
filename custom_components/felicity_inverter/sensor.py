"""Sensor platform for the Felicity inverter integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfTemperature,
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
class FelicitySensorSpec:
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


@dataclass(frozen=True)
class FelicityWifiBatterySensorSpec:
    field_name: str
    name: str
    unit: str | None = None
    device_class: SensorDeviceClass | None = None
    state_class: SensorStateClass | None = None
    suggested_display_precision: int | None = None
    entity_category: EntityCategory | None = None


WIFI_BATTERY_SENSOR_SPECS = (
    FelicityWifiBatterySensorSpec(
        field_name="soc",
        name="SOC",
        unit=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),
    FelicityWifiBatterySensorSpec(
        field_name="voltage",
        name="Voltage",
        unit=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
    ),
    FelicityWifiBatterySensorSpec(
        field_name="current",
        name="Current",
        unit=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),
    FelicityWifiBatterySensorSpec(
        field_name="power",
        name="Power",
        unit=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
    ),
    FelicityWifiBatterySensorSpec(
        field_name="temperature_min",
        name="Temperature Min",
        unit=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),
    FelicityWifiBatterySensorSpec(
        field_name="temperature_max",
        name="Temperature Max",
        unit=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),
    FelicityWifiBatterySensorSpec(
        field_name="cell_voltage_min",
        name="Cell Voltage Min",
        unit=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=3,
    ),
    FelicityWifiBatterySensorSpec(
        field_name="cell_voltage_max",
        name="Cell Voltage Max",
        unit=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=3,
    ),
    FelicityWifiBatterySensorSpec(
        field_name="cell_voltage_delta",
        name="Cell Voltage Delta",
        unit=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=3,
    ),
    FelicityWifiBatterySensorSpec(
        field_name="cell_count",
        name="Cell Count",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
    ),
    FelicityWifiBatterySensorSpec(
        field_name="parallel_modules",
        name="Parallel Modules",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
    ),
    FelicityWifiBatterySensorSpec(
        field_name="state_code",
        name="State Code",
        entity_category=EntityCategory.DIAGNOSTIC,
        suggested_display_precision=0,
    ),
    FelicityWifiBatterySensorSpec(
        field_name="warn_code",
        name="Warning Code",
        entity_category=EntityCategory.DIAGNOSTIC,
        suggested_display_precision=0,
    ),
    FelicityWifiBatterySensorSpec(
        field_name="fault_code",
        name="Fault Code",
        entity_category=EntityCategory.DIAGNOSTIC,
        suggested_display_precision=0,
    ),
    FelicityWifiBatterySensorSpec(
        field_name="estate_code",
        name="Estate Code",
        entity_category=EntityCategory.DIAGNOSTIC,
        suggested_display_precision=0,
    ),
)


def _friendly_name(field_name: str) -> str:
    return field_name.replace("_", " ").replace("Pv", "PV").title().replace("Pv", "PV")


def _build_specs() -> list[FelicitySensorSpec]:
    specs: list[FelicitySensorSpec] = []

    for address, (field_name, _, unit, note) in sorted(STATUS_REGISTERS.items()):
        device_class, state_class, precision = STATUS_SENSOR_META.get(field_name, (None, None, None))
        specs.append(
            FelicitySensorSpec(
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
        specs.append(
            FelicitySensorSpec(
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

    return specs


SENSOR_SPECS = _build_specs()


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Felicity inverter sensors."""
    coordinator: FelicityInverterDataCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SensorEntity] = []
    if coordinator.has_inverter:
        entities.extend(FelicityRegisterSensor(coordinator, entry.entry_id, spec) for spec in SENSOR_SPECS)
    if coordinator.device_type == "battery":
        entities.extend(
            FelicityWifiBatterySensor(coordinator, entry.entry_id, spec) for spec in WIFI_BATTERY_SENSOR_SPECS
        )
    async_add_entities(entities)


class FelicityRegisterSensor(FelicityInverterEntity, SensorEntity):
    """Expose a mapped register as a Home Assistant sensor."""

    def __init__(
        self,
        coordinator: FelicityInverterDataCoordinator,
        entry_id: str,
        spec: FelicitySensorSpec,
    ) -> None:
        super().__init__(coordinator, entry_id, f"{spec.block}_{spec.field_name}")
        self._spec = spec
        self._attr_has_entity_name = True
        self._attr_name = _friendly_name(spec.field_name)
        self._attr_native_unit_of_measurement = UNIT_MAP.get(spec.unit)
        self._attr_device_class = spec.device_class
        self._attr_state_class = spec.state_class
        self._attr_entity_category = spec.entity_category
        self._attr_suggested_display_precision = spec.suggested_display_precision

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
        return self.coordinator.data[self._spec.block]["registers_by_name"][self._spec.field_name]


class FelicityWifiBatterySensor(FelicityInverterEntity, SensorEntity):
    """Expose WiFi battery telemetry as Home Assistant sensors."""

    def __init__(
        self,
        coordinator: FelicityInverterDataCoordinator,
        entry_id: str,
        spec: FelicityWifiBatterySensorSpec,
    ) -> None:
        super().__init__(coordinator, entry_id, f"wifi_battery_{spec.field_name}")
        self._spec = spec
        self._attr_has_entity_name = True
        self._attr_name = spec.name
        self._attr_native_unit_of_measurement = spec.unit
        self._attr_device_class = spec.device_class
        self._attr_state_class = spec.state_class
        self._attr_entity_category = spec.entity_category
        self._attr_suggested_display_precision = spec.suggested_display_precision

    @property
    def available(self) -> bool:
        return super().available and self.coordinator.data.get("wifi_battery") is not None

    @property
    def native_value(self):
        return self._wifi_battery_data["fields"].get(self._spec.field_name)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        fields = self._wifi_battery_data["fields"]
        connection = self._wifi_battery_data["connection"]
        return {
            "wifi_host": connection.get("host") or self.coordinator.wifi_battery_host,
            "wifi_port": connection.get("port") or self.coordinator.wifi_battery_port,
            "wifi_sn": connection.get("wifi_sn"),
            "device_sn": connection.get("device_sn"),
            "battery_type": connection.get("type"),
            "battery_subtype": connection.get("subtype"),
            "max_cell_index": fields.get("max_cell_index"),
            "min_cell_index": fields.get("min_cell_index"),
        }

    @property
    def _wifi_battery_data(self) -> dict[str, Any]:
        data = self.coordinator.data.get("wifi_battery")
        if data is None:
            return {"fields": {}, "connection": {}, "raw": {}}
        return data
