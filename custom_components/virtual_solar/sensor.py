"""Sensor platform for Virtual Solar."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfPower
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event

from .const import (
    CONF_BATTERY_CAPACITY,
    CONF_BATTERY_LEVEL_SENSOR,
    CONF_HOUSE_CONSUMPTION_SENSOR,
    CONF_LUX_SENSOR,
    CONF_PANEL_COUNT,
    CONF_PANEL_WATTAGE,
    DOMAIN,
    LUX_PER_WM2,
    STATE_CHARGING,
    STATE_DISCHARGING,
    STATE_EMPTY,
    STATE_FULL,
    STC_IRRADIANCE,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Virtual Solar sensors from a config entry."""
    config: dict[str, Any] = {**entry.data, **entry.options}
    async_add_entities(
        [SolarOutputSensor(entry, config), BatteryStatusSensor(entry, config)]
    )


def _safe_float(value: Any) -> float | None:
    if value in (None, "unknown", "unavailable", ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _device_info(entry: ConfigEntry) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name="Virtual Solar",
        manufacturer="Virtual Solar",
        entry_type=DeviceEntryType.SERVICE,
    )


def _estimate_output(lux: float | None, panel_w: float, panel_count: float) -> float | None:
    if lux is None:
        return None
    return (lux / LUX_PER_WM2) * (panel_w * panel_count / STC_IRRADIANCE)


class SolarOutputSensor(SensorEntity):
    """Solar panel estimated output, derived from a lux reading."""

    _attr_has_entity_name = True
    _attr_name = "Estimated output"
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_icon = "mdi:solar-panel"
    _attr_should_poll = False
    _attr_suggested_display_precision = 1

    def __init__(self, entry: ConfigEntry, config: dict[str, Any]) -> None:
        self._entry = entry
        self._lux_entity: str = config[CONF_LUX_SENSOR]
        self._panel_wattage = float(config[CONF_PANEL_WATTAGE])
        self._panel_count = float(config[CONF_PANEL_COUNT])
        self._attr_unique_id = f"{entry.entry_id}_estimated_output"
        self._attr_device_info = _device_info(entry)
        self._attr_native_value: float | None = None

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_track_state_change_event(
                self.hass, [self._lux_entity], self._handle_change
            )
        )
        self._recalculate()

    @callback
    def _handle_change(self, _event: Event[EventStateChangedData]) -> None:
        self._recalculate()
        self.async_write_ha_state()

    @callback
    def _recalculate(self) -> None:
        state = self.hass.states.get(self._lux_entity)
        lux = _safe_float(state.state) if state else None
        watts = _estimate_output(lux, self._panel_wattage, self._panel_count)
        self._attr_native_value = None if watts is None else round(watts, 1)


class BatteryStatusSensor(SensorEntity):
    """Virtual battery status: Charging / Discharging / Full / Empty."""

    _attr_has_entity_name = True
    _attr_name = "Battery status"
    _attr_should_poll = False

    def __init__(self, entry: ConfigEntry, config: dict[str, Any]) -> None:
        self._entry = entry
        self._lux_entity: str = config[CONF_LUX_SENSOR]
        self._house_entity: str = config[CONF_HOUSE_CONSUMPTION_SENSOR]
        self._level_entity: str = config[CONF_BATTERY_LEVEL_SENSOR]
        self._panel_wattage = float(config[CONF_PANEL_WATTAGE])
        self._panel_count = float(config[CONF_PANEL_COUNT])
        self._capacity = float(config[CONF_BATTERY_CAPACITY])
        self._attr_unique_id = f"{entry.entry_id}_battery_status"
        self._attr_device_info = _device_info(entry)
        self._attr_native_value: str | None = None
        self._attr_icon = "mdi:battery"

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_track_state_change_event(
                self.hass,
                [self._lux_entity, self._house_entity, self._level_entity],
                self._handle_change,
            )
        )
        self._recalculate()

    @callback
    def _handle_change(self, _event: Event[EventStateChangedData]) -> None:
        self._recalculate()
        self.async_write_ha_state()

    @callback
    def _recalculate(self) -> None:
        lux = self._read(self._lux_entity)
        house = self._read(self._house_entity)
        level = self._read(self._level_entity)
        solar = _estimate_output(lux, self._panel_wattage, self._panel_count)

        pct = (level / self._capacity * 100.0) if (level is not None and self._capacity > 0) else None

        if pct is not None and pct < 5:
            state, icon = STATE_EMPTY, "mdi:battery-alert"
        elif pct is not None and pct >= 99:
            state, icon = STATE_FULL, "mdi:battery-check"
        elif solar is not None and house is not None and solar > house:
            state, icon = STATE_CHARGING, "mdi:battery-charging"
        else:
            state, icon = STATE_DISCHARGING, "mdi:battery-minus"

        self._attr_native_value = state
        self._attr_icon = icon

    def _read(self, entity_id: str) -> float | None:
        state = self.hass.states.get(entity_id)
        return _safe_float(state.state) if state else None
