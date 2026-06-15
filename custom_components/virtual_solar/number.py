"""Number platform for Virtual Solar.

Owns three user-tweakable values that drive the simulation:

  * `number.virtual_solar_battery_level`  -- current stored energy (kWh)
  * `number.virtual_solar_panel_count`    -- how many panels
  * `number.virtual_solar_panel_wattage`  -- rated wattage per panel
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.restore_state import RestoreEntity

from .const import (
    CONF_BATTERY_CAPACITY,
    CONF_HOUSE_CONSUMPTION_SENSOR,
    CONF_LUX_SENSOR,
    CONF_MAX_CHARGE_RATE,
    CONF_PANEL_COUNT,
    CONF_PANEL_WATTAGE,
    DEFAULT_MAX_CHARGE_RATE,
    TICK_INTERVAL_SECONDS,
)
from .util import (
    device_info,
    estimate_output,
    read_panel_config,
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
    Treat the config flow's panel/battery defaults as initial seeds
    only; the live slider is authoritative once touched.
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
                    self._attr_native_min_value,
                    self._attr_native_max_value,
                )

    async def async_set_native_value(self, value: float) -> None:
        self._attr_native_value = round(
            _clamp(value, self._attr_native_min_value, self._attr_native_max_value), 4
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
    _attr_native_max_value = 20
    _attr_native_step = 1

    def __init__(self, entry: ConfigEntry, config: dict[str, Any]) -> None:
        super().__init__(entry, float(config[CONF_PANEL_COUNT]))
        self._attr_unique_id = f"{entry.entry_id}_panel_count"


class VirtualBatteryLevel(_RestoreNumber):
    """Current stored energy. Ticks every minute, persists across restarts."""

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
        self._capacity = float(config[CONF_BATTERY_CAPACITY])
        self._max_rate = float(
            config.get(CONF_MAX_CHARGE_RATE, DEFAULT_MAX_CHARGE_RATE)
        )
        self._attr_native_max_value = self._capacity
        self._attr_unique_id = f"{entry.entry_id}_battery_level"

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(
            async_track_time_interval(
                self.hass, self._tick, timedelta(seconds=TICK_INTERVAL_SECONDS)
            )
        )

    @callback
    def _tick(self, _now: datetime) -> None:
        lux_state = self.hass.states.get(self._lux_entity)
        house_state = self.hass.states.get(self._house_entity)
        lux = safe_float(lux_state.state) if lux_state else None
        house = safe_float(house_state.state) if house_state else None
        wattage, count = read_panel_config(
            self.hass, self._fallback_wattage, self._fallback_count
        )
        solar = estimate_output(lux, wattage, count)
        if solar is None or house is None:
            return

        net_w = _clamp(solar - house, -self._max_rate, self._max_rate)
        delta_kwh = net_w * (TICK_INTERVAL_SECONDS / 3600.0) / 1000.0
        self._attr_native_value = round(
            _clamp(self._attr_native_value + delta_kwh, 0.0, self._capacity), 4
        )
        self.async_write_ha_state()
