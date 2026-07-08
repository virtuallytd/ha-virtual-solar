"""Switch platform for Virtual Solar.

Exposes a single switch per config entry that gates whether the virtual
battery discharges when the house draws more than the panels produce.
Off = the battery holds its charge; the house is served entirely from
the grid. Charge behaviour (solar surplus filling the battery) is
unaffected by the switch.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .util import device_info


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Virtual Solar switch entities."""
    async_add_entities([DischargeEnabledSwitch(entry)])


class DischargeEnabledSwitch(SwitchEntity, RestoreEntity):
    """Controls whether the virtual battery discharges to cover house demand."""

    _attr_has_entity_name = True
    _attr_name = "Discharge enabled"
    _attr_icon = "mdi:battery-arrow-down-outline"
    _attr_should_poll = False

    def __init__(self, entry: ConfigEntry) -> None:
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_discharge_enabled"
        self._attr_device_info = device_info(entry)
        self._attr_is_on = True

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state is not None and last_state.state == "off":
            self._attr_is_on = False

    async def async_turn_on(self, **kwargs: Any) -> None:
        self._attr_is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        self._attr_is_on = False
        self.async_write_ha_state()
