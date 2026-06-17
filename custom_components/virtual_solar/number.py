"""Number platform for Virtual Solar.

Owns user-tweakable values that drive the simulation:

  * `number.virtual_solar_panel_count`        -- how many panels
  * `number.virtual_solar_panel_wattage`      -- rated wattage per panel
  * `number.virtual_solar_battery_capacity`   -- total storage (kWh)
  * `number.virtual_solar_battery_level`      -- current stored energy (kWh)
  * `number.virtual_solar_system_efficiency`  -- inverter/wiring losses (%)
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
from homeassistant.core import (
    Event,
    EventStateChangedData,
    HomeAssistant,
    callback,
)
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_interval,
)
from homeassistant.helpers.restore_state import RestoreEntity

from .const import (
    BATTERY_CAPACITY_ENTITY_ID,
    CONF_BATTERY_CAPACITY,
    CONF_HOUSE_CONSUMPTION_SENSOR,
    CONF_LUX_SENSOR,
    CONF_MAX_CHARGE_RATE,
    CONF_MAX_DISCHARGE_RATE,
    CONF_PANEL_COUNT,
    CONF_PANEL_WATTAGE,
    CONF_SYSTEM_EFFICIENCY,
    DEFAULT_MAX_CHARGE_RATE,
    DEFAULT_MAX_DISCHARGE_RATE,
    DEFAULT_SYSTEM_EFFICIENCY,
    TICK_INTERVAL_SECONDS,
)
from .util import (
    device_info,
    estimate_output,
    read_capacity,
    read_panel_config,
    read_system_efficiency,
    safe_float,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Virtual Solar number entities."""
    config: dict[str, Any] = {**entry.data, **entry.options}
    async_add_entities(
        [
            PanelWattage(entry, config),
            PanelCount(entry, config),
            BatteryCapacity(entry, config),
            SystemEfficiency(entry, config),
            VirtualBatteryLevel(entry, config),
        ]
    )


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


class _RestoreNumber(NumberEntity, RestoreEntity):
    """Number entity that restores its last value after restart.

    The initial value passed in `__init__` only applies on first setup
    (before the entity has ever recorded a state). On every subsequent
    load (including reloads triggered by the options flow),
    `async_get_last_state` returns the last user-set value and wins.
    """

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_mode = NumberMode.BOX

    def __init__(self, entry: ConfigEntry, initial_value: float) -> None:
        self._entry = entry
        self._attr_device_info = device_info(entry)
        self._attr_native_value: float = float(initial_value)

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state and last_state.state not in (None, "unknown", "unavailable"):
            restored = safe_float(last_state.state)
            if restored is not None:
                self._attr_native_value = _clamp(
                    restored,
                    self.native_min_value,
                    self.native_max_value,
                )

    async def async_set_native_value(self, value: float) -> None:
        self._attr_native_value = round(
            _clamp(value, self.native_min_value, self.native_max_value), 4
        )
        self.async_write_ha_state()


class PanelWattage(_RestoreNumber):
    _attr_name = "Panel wattage"
    _attr_icon = "mdi:solar-panel"
    _attr_native_unit_of_measurement = "W"
    _attr_native_min_value = 100
    _attr_native_max_value = 800
    _attr_native_step = 10

    def __init__(self, entry: ConfigEntry, config: dict[str, Any]) -> None:
        super().__init__(entry, float(config[CONF_PANEL_WATTAGE]))
        self._attr_unique_id = f"{entry.entry_id}_panel_wattage"


class PanelCount(_RestoreNumber):
    _attr_name = "Panel count"
    _attr_icon = "mdi:solar-panel-large"
    _attr_native_min_value = 1
    _attr_native_max_value = 60
    _attr_native_step = 1

    def __init__(self, entry: ConfigEntry, config: dict[str, Any]) -> None:
        super().__init__(entry, float(config[CONF_PANEL_COUNT]))
        self._attr_unique_id = f"{entry.entry_id}_panel_count"


class BatteryCapacity(_RestoreNumber):
    """Total battery capacity in kWh. Live-editable from the dashboard."""

    _attr_name = "Battery capacity"
    _attr_icon = "mdi:battery-high"
    _attr_native_unit_of_measurement = "kWh"
    _attr_native_min_value = 0.1
    _attr_native_max_value = 100
    _attr_native_step = 0.01

    def __init__(self, entry: ConfigEntry, config: dict[str, Any]) -> None:
        super().__init__(entry, float(config[CONF_BATTERY_CAPACITY]))
        self._attr_unique_id = f"{entry.entry_id}_battery_capacity"


class SystemEfficiency(_RestoreNumber):
    """Combined inverter / wiring / thermal losses (%)."""

    _attr_name = "System efficiency"
    _attr_icon = "mdi:gauge"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_native_min_value = 50
    _attr_native_max_value = 100
    _attr_native_step = 1

    def __init__(self, entry: ConfigEntry, config: dict[str, Any]) -> None:
        super().__init__(
            entry,
            float(config.get(CONF_SYSTEM_EFFICIENCY, DEFAULT_SYSTEM_EFFICIENCY)),
        )
        self._attr_unique_id = f"{entry.entry_id}_system_efficiency"


class VirtualBatteryLevel(_RestoreNumber):
    """Current stored energy. Ticks every minute, persists across restarts.

    `native_max_value` is dynamic and tracks the BatteryCapacity entity,
    so resizing the battery resizes this slider too.
    """

    _attr_name = "Battery level"
    _attr_icon = "mdi:battery"
    _attr_native_unit_of_measurement = "kWh"
    _attr_native_step = 0.001
    _attr_native_min_value = 0

    def __init__(self, entry: ConfigEntry, config: dict[str, Any]) -> None:
        super().__init__(entry, 0.0)
        self._lux_entity: str = config[CONF_LUX_SENSOR]
        self._house_entity: str = config[CONF_HOUSE_CONSUMPTION_SENSOR]
        self._fallback_wattage = float(config[CONF_PANEL_WATTAGE])
        self._fallback_count = float(config[CONF_PANEL_COUNT])
        self._fallback_capacity = float(config[CONF_BATTERY_CAPACITY])
        self._fallback_efficiency_pct = float(
            config.get(CONF_SYSTEM_EFFICIENCY, DEFAULT_SYSTEM_EFFICIENCY)
        )
        self._max_charge_rate = float(
            config.get(CONF_MAX_CHARGE_RATE, DEFAULT_MAX_CHARGE_RATE)
        )
        self._max_discharge_rate = float(
            config.get(CONF_MAX_DISCHARGE_RATE, DEFAULT_MAX_DISCHARGE_RATE)
        )
        self._attr_unique_id = f"{entry.entry_id}_battery_level"

    @property
    def native_max_value(self) -> float:
        return read_capacity(self.hass, self._fallback_capacity)

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(
            async_track_time_interval(
                self.hass, self._tick, timedelta(seconds=TICK_INTERVAL_SECONDS)
            )
        )
        self.async_on_remove(
            async_track_state_change_event(
                self.hass,
                [BATTERY_CAPACITY_ENTITY_ID],
                self._on_capacity_change,
            )
        )

    @callback
    def _on_capacity_change(self, _event: Event[EventStateChangedData]) -> None:
        cap = read_capacity(self.hass, self._fallback_capacity)
        if self._attr_native_value > cap:
            self._attr_native_value = round(cap, 4)
        self.async_write_ha_state()

    @callback
    def _tick(self, _now: datetime) -> None:
        lux_state = self.hass.states.get(self._lux_entity)
        house_state = self.hass.states.get(self._house_entity)
        lux = safe_float(lux_state.state) if lux_state else None
        house = safe_float(house_state.state) if house_state else None
        wattage, count = read_panel_config(
            self.hass, self._fallback_wattage, self._fallback_count
        )
        efficiency = read_system_efficiency(self.hass, self._fallback_efficiency_pct)
        solar = estimate_output(lux, wattage, count, efficiency)
        if solar is None or house is None:
            return

        capacity = read_capacity(self.hass, self._fallback_capacity)
        net_w = _clamp(
            solar - house, -self._max_discharge_rate, self._max_charge_rate
        )
        delta_kwh = net_w * (TICK_INTERVAL_SECONDS / 3600.0) / 1000.0
        self._attr_native_value = round(
            _clamp(self._attr_native_value + delta_kwh, 0.0, capacity), 4
        )
        self.async_write_ha_state()
