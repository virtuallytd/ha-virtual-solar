"""Sensor platform for Virtual Solar."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfPower
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event

from .const import (
    BATTERY_LEVEL_ENTITY_ID,
    CHARGE_RATE_ENTITY_ID,
    CONF_BATTERY_CAPACITY,
    CONF_HOUSE_CONSUMPTION_SENSOR,
    CONF_LUX_SENSOR,
    CONF_MAX_CHARGE_RATE,
    CONF_PANEL_COUNT,
    CONF_PANEL_WATTAGE,
    DEFAULT_MAX_CHARGE_RATE,
    PANEL_COUNT_ENTITY_ID,
    PANEL_WATTAGE_ENTITY_ID,
    STATE_CHARGING,
    STATE_DISCHARGING,
    STATE_EMPTY,
    STATE_FULL,
)
from .util import device_info, estimate_output, read_panel_config, safe_float


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Virtual Solar sensors from a config entry."""
    config: dict[str, Any] = {**entry.data, **entry.options}
    async_add_entities(
        [
            SolarOutputSensor(entry, config),
            BatteryPercentageSensor(entry, config),
            BatteryChargeRateSensor(entry, config),
            BatteryTimeToFullSensor(entry, config),
            BatteryStatusSensor(entry, config),
        ]
    )


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _read(hass: HomeAssistant, entity_id: str) -> float | None:
    state = hass.states.get(entity_id)
    return safe_float(state.state) if state else None


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
        self._fallback_wattage = float(config[CONF_PANEL_WATTAGE])
        self._fallback_count = float(config[CONF_PANEL_COUNT])
        self._attr_unique_id = f"{entry.entry_id}_estimated_output"
        self._attr_device_info = device_info(entry)
        self._attr_native_value: float | None = None

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_track_state_change_event(
                self.hass,
                [self._lux_entity, PANEL_WATTAGE_ENTITY_ID, PANEL_COUNT_ENTITY_ID],
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
        lux = _read(self.hass, self._lux_entity)
        wattage, count = read_panel_config(
            self.hass, self._fallback_wattage, self._fallback_count
        )
        watts = estimate_output(lux, wattage, count)
        self._attr_native_value = None if watts is None else round(watts, 1)


class BatteryPercentageSensor(SensorEntity):
    """Battery percentage (level / capacity * 100)."""

    _attr_has_entity_name = True
    _attr_name = "Battery percentage"
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_should_poll = False
    _attr_suggested_display_precision = 1

    def __init__(self, entry: ConfigEntry, config: dict[str, Any]) -> None:
        self._entry = entry
        self._capacity = float(config[CONF_BATTERY_CAPACITY])
        self._attr_unique_id = f"{entry.entry_id}_battery_percentage"
        self._attr_device_info = device_info(entry)
        self._attr_native_value: float | None = None
        self._attr_icon = "mdi:battery"

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_track_state_change_event(
                self.hass, [BATTERY_LEVEL_ENTITY_ID], self._handle_change
            )
        )
        self._recalculate()

    @callback
    def _handle_change(self, _event: Event[EventStateChangedData]) -> None:
        self._recalculate()
        self.async_write_ha_state()

    @callback
    def _recalculate(self) -> None:
        level = _read(self.hass, BATTERY_LEVEL_ENTITY_ID)
        if level is None or self._capacity <= 0:
            self._attr_native_value = None
            return
        pct = (level / self._capacity) * 100.0
        self._attr_native_value = round(pct, 1)
        self._attr_icon = _battery_icon(pct)


def _battery_icon(pct: float) -> str:
    if pct >= 90:
        return "mdi:battery"
    if pct >= 70:
        return "mdi:battery-80"
    if pct >= 50:
        return "mdi:battery-60"
    if pct >= 30:
        return "mdi:battery-40"
    if pct >= 10:
        return "mdi:battery-20"
    return "mdi:battery-outline"


class BatteryChargeRateSensor(SensorEntity):
    """Net W flowing into (positive) or out of (negative) the battery.

    Equals `clamp(solar - house, -max_rate, +max_rate)`. Reads live from
    the lux, house, and panel entities, so it reacts instantly.
    """

    _attr_has_entity_name = True
    _attr_name = "Battery charge rate"
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_should_poll = False
    _attr_suggested_display_precision = 1

    def __init__(self, entry: ConfigEntry, config: dict[str, Any]) -> None:
        self._entry = entry
        self._lux_entity: str = config[CONF_LUX_SENSOR]
        self._house_entity: str = config[CONF_HOUSE_CONSUMPTION_SENSOR]
        self._fallback_wattage = float(config[CONF_PANEL_WATTAGE])
        self._fallback_count = float(config[CONF_PANEL_COUNT])
        self._max_rate = float(
            config.get(CONF_MAX_CHARGE_RATE, DEFAULT_MAX_CHARGE_RATE)
        )
        self._attr_unique_id = f"{entry.entry_id}_battery_charge_rate"
        self._attr_device_info = device_info(entry)
        self._attr_native_value: float | None = None
        self._attr_icon = "mdi:battery-arrow-up"

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_track_state_change_event(
                self.hass,
                [
                    self._lux_entity,
                    self._house_entity,
                    PANEL_WATTAGE_ENTITY_ID,
                    PANEL_COUNT_ENTITY_ID,
                ],
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
        lux = _read(self.hass, self._lux_entity)
        house = _read(self.hass, self._house_entity)
        wattage, count = read_panel_config(
            self.hass, self._fallback_wattage, self._fallback_count
        )
        solar = estimate_output(lux, wattage, count)
        if solar is None or house is None:
            self._attr_native_value = None
            return
        net_w = _clamp(solar - house, -self._max_rate, self._max_rate)
        self._attr_native_value = round(net_w, 1)
        self._attr_icon = (
            "mdi:battery-arrow-up" if net_w >= 0 else "mdi:battery-arrow-down"
        )


class BatteryTimeToFullSensor(SensorEntity):
    """Human-readable time remaining until the battery is full.

    Returns strings like `2h 15m`, `Full`, or `No solar input` so it can
    be displayed verbatim in entity cards.
    """

    _attr_has_entity_name = True
    _attr_name = "Battery time to full"
    _attr_should_poll = False
    _attr_icon = "mdi:clock-outline"

    def __init__(self, entry: ConfigEntry, config: dict[str, Any]) -> None:
        self._entry = entry
        self._capacity = float(config[CONF_BATTERY_CAPACITY])
        self._attr_unique_id = f"{entry.entry_id}_battery_time_to_full"
        self._attr_device_info = device_info(entry)
        self._attr_native_value: str | None = None

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_track_state_change_event(
                self.hass,
                [BATTERY_LEVEL_ENTITY_ID, CHARGE_RATE_ENTITY_ID],
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
        level = _read(self.hass, BATTERY_LEVEL_ENTITY_ID)
        rate_w = _read(self.hass, CHARGE_RATE_ENTITY_ID)
        if level is None:
            self._attr_native_value = None
            return
        remaining_kwh = self._capacity - level
        if remaining_kwh <= 0:
            self._attr_native_value = "Full"
            return
        if rate_w is None or rate_w < 1:
            self._attr_native_value = "No solar input"
            return
        hours = remaining_kwh / (rate_w / 1000.0)
        h = int(hours)
        m = int((hours - h) * 60)
        self._attr_native_value = f"{h}h {m}m"


class BatteryStatusSensor(SensorEntity):
    """Virtual battery status: Charging / Discharging / Full / Empty.

    Action (Charging/Discharging) wins over condition (Full/Empty):
    a 0% battery being charged shows `Charging`, not `Empty`.
    """

    _attr_has_entity_name = True
    _attr_name = "Battery status"
    _attr_should_poll = False

    def __init__(self, entry: ConfigEntry, config: dict[str, Any]) -> None:
        self._entry = entry
        self._lux_entity: str = config[CONF_LUX_SENSOR]
        self._house_entity: str = config[CONF_HOUSE_CONSUMPTION_SENSOR]
        self._fallback_wattage = float(config[CONF_PANEL_WATTAGE])
        self._fallback_count = float(config[CONF_PANEL_COUNT])
        self._capacity = float(config[CONF_BATTERY_CAPACITY])
        self._attr_unique_id = f"{entry.entry_id}_battery_status"
        self._attr_device_info = device_info(entry)
        self._attr_native_value: str | None = None
        self._attr_icon = "mdi:battery"

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_track_state_change_event(
                self.hass,
                [
                    self._lux_entity,
                    self._house_entity,
                    BATTERY_LEVEL_ENTITY_ID,
                    PANEL_WATTAGE_ENTITY_ID,
                    PANEL_COUNT_ENTITY_ID,
                ],
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
        lux = _read(self.hass, self._lux_entity)
        house = _read(self.hass, self._house_entity)
        level = _read(self.hass, BATTERY_LEVEL_ENTITY_ID)
        wattage, count = read_panel_config(
            self.hass, self._fallback_wattage, self._fallback_count
        )
        solar = estimate_output(lux, wattage, count)
        pct = (
            (level / self._capacity * 100.0)
            if (level is not None and self._capacity > 0)
            else None
        )
        charging = solar is not None and house is not None and solar > house

        if charging:
            if pct is not None and pct >= 99:
                state, icon = STATE_FULL, "mdi:battery-check"
            else:
                state, icon = STATE_CHARGING, "mdi:battery-charging"
        else:
            if pct is not None and pct < 5:
                state, icon = STATE_EMPTY, "mdi:battery-alert"
            else:
                state, icon = STATE_DISCHARGING, "mdi:battery-minus"

        self._attr_native_value = state
        self._attr_icon = icon
