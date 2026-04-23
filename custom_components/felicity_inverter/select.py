"""Select platform for inverter mode control."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .client import FelicityInverterError
from .const import DOMAIN, MODE_BY_REGISTER_PAIR, MODES
from .coordinator import FelicityInverterDataCoordinator
from .entity import FelicityInverterEntity
from .register_map import CHARGE_PRIORITY, OUTPUT_PRIORITY


@dataclass(frozen=True)
class FelicitySelectSpec:
    field_name: str
    name: str
    options_by_value: dict[int, str]
    entity_category: EntityCategory | None = None


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the inverter mode select."""
    coordinator: FelicityInverterDataCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            FelicityModeSelect(coordinator, entry.entry_id),
            FelicitySettingSelect(
                coordinator,
                entry.entry_id,
                FelicitySelectSpec(
                    field_name="output_source_priority",
                    name="Output Source Priority",
                    options_by_value=OUTPUT_PRIORITY,
                    entity_category=EntityCategory.CONFIG,
                ),
            ),
            FelicitySettingSelect(
                coordinator,
                entry.entry_id,
                FelicitySelectSpec(
                    field_name="charge_source_priority",
                    name="Charge Source Priority",
                    options_by_value=CHARGE_PRIORITY,
                    entity_category=EntityCategory.CONFIG,
                ),
            ),
        ]
    )


class FelicityModeSelect(FelicityInverterEntity, SelectEntity):
    """Select entity that controls the inverter mode presets."""

    def __init__(self, coordinator: FelicityInverterDataCoordinator, entry_id: str) -> None:
        super().__init__(coordinator, entry_id, "mode")
        self._attr_has_entity_name = True
        self._attr_name = "Preset Mode"
        self._attr_options = list(MODES)
        self._attr_icon = "mdi:transmission-tower"

    @property
    def current_option(self) -> str | None:
        """Return the currently active mode if it matches a known preset."""
        settings = self.coordinator.data["settings"]["fields"]
        pair = (
            settings.get("output_source_priority"),
            settings.get("charge_source_priority"),
        )
        return MODE_BY_REGISTER_PAIR.get(pair)

    async def async_select_option(self, option: str) -> None:
        """Apply the selected inverter mode."""
        if option not in MODES:
            raise HomeAssistantError(f"Unsupported mode: {option}")

        try:
            await self.coordinator.async_set_mode(option)
        except FelicityInverterError as err:
            raise HomeAssistantError(str(err)) from err

    @property
    def extra_state_attributes(self) -> dict[str, int | str | None]:
        """Expose the raw register pair and actual inverter working mode."""
        status = self.coordinator.data["status"]["fields"]
        settings = self.coordinator.data["settings"]["fields"]
        return {
            "output_source_priority": settings.get("output_source_priority"),
            "charge_source_priority": settings.get("charge_source_priority"),
            "working_mode": status.get("working_mode"),
            "working_mode_label": status.get("working_mode_label"),
        }


class FelicitySettingSelect(FelicityInverterEntity, SelectEntity):
    """Select entity for writable inverter enum settings."""

    def __init__(self, coordinator: FelicityInverterDataCoordinator, entry_id: str, spec: FelicitySelectSpec) -> None:
        super().__init__(coordinator, entry_id, f"select_{spec.field_name}")
        self._spec = spec
        self._value_by_option = {label: value for value, label in spec.options_by_value.items()}
        self._attr_has_entity_name = True
        self._attr_name = spec.name
        self._attr_options = list(spec.options_by_value.values())
        self._attr_entity_category = spec.entity_category

    @property
    def current_option(self) -> str | None:
        """Return the currently active enum label."""
        settings = self.coordinator.data["settings"]["fields"]
        raw_value = settings.get(self._spec.field_name)
        if not isinstance(raw_value, int):
            return None
        return self._spec.options_by_value.get(raw_value)

    async def async_select_option(self, option: str) -> None:
        """Write a new enum value."""
        if option not in self._value_by_option:
            raise HomeAssistantError(f"Unsupported option: {option}")

        try:
            await self.coordinator.async_write_setting(self._spec.field_name, self._value_by_option[option])
        except FelicityInverterError as err:
            raise HomeAssistantError(str(err)) from err

    @property
    def extra_state_attributes(self) -> dict[str, int | str | None]:
        """Return raw register details for the enum setting."""
        register = self.coordinator.data["settings"]["registers_by_name"][self._spec.field_name]
        return {
            "register_address": register["address_hex"],
            "register_raw": register["raw"],
            "register_note": register["note"],
        }
