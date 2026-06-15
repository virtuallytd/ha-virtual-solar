"""Number platform for Virtual Solar: the virtual battery level."""

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
from .util import device_info, estimate_output, safe_float


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the virtual battery level entity."""
    config: dict[str, Any] = {**entry.data, **entry.options}
    async_add_entities([VirtualBatteryLevel(entry, config)])


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


class VirtualBatteryLevel(NumberEntity, RestoreEntity):
    """The virtual battery's current stored energy.

    Ticks on a fixed interval, applying `(solar − house)` to the stored
    value, capped at the configured max charge/discharge rate and clamped
    to [0, capacity]. The value persists across HA restarts via
    RestoreEntity and is user-editable so it can be manually reset.
    """

    _attr_has_entity_name = True
    _attr_name = "Battery level"
    _attr_native_unit_of_measurement = "kWh"
    _attr_mode = NumberMode.BOX
    _attr_native_step = 0.001
    _attr_native_min_value = 0
    _attr_icon = "mdi:battery"
    _attr_should_poll = False

    def __init__(self, entry: ConfigEntry, config: dict[str, Any]) -> None:
        self._entry = entry
        self._lux_entity: str = config[CONF_LUX_SENSOR]
        self._house_entity: str = config[CONF_HOUSE_CONSUMPTION_SENSOR]
        self._panel_wattage = float(config[CONF_PANEL_WATTAGE])
        self._panel_count = float(config[CONF_PANEL_COUNT])
        self._capacity = float(config[CONF_BATTERY_CAPACITY])
        self._max_rate = float(
            config.get(CONF_MAX_CHARGE_RATE, DEFAULT_MAX_CHARGE_RATE)
        )
        self._attr_native_max_value = self._capacity
        self._attr_unique_id = f"{entry.entry_id}_battery_level"
        self._attr_device_info = device_info(entry)
        self._attr_native_value: float = 0.0

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state and last_state.state not in (None, "unknown", "unavailable"):
            restored = safe_float(last_state.state)
            if restored is not None:
                self._attr_native_value = _clamp(restored, 0.0, self._capacity)

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
        solar = estimate_output(lux, self._panel_wattage, self._panel_count)
        if solar is None or house is None:
            return

        net_w = _clamp(solar - house, -self._max_rate, self._max_rate)
        delta_kwh = net_w * (TICK_INTERVAL_SECONDS / 3600.0) / 1000.0
        self._attr_native_value = round(
            _clamp(self._attr_native_value + delta_kwh, 0.0, self._capacity), 4
        )
        self.async_write_ha_state()

    async def async_set_native_value(self, value: float) -> None:
        """User-initiated set (e.g. resetting to 0 or full from the UI)."""
        self._attr_native_value = round(_clamp(value, 0.0, self._capacity), 4)
        self.async_write_ha_state()
