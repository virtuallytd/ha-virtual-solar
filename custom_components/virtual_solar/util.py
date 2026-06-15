"""Shared helpers for the Virtual Solar integration."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity import DeviceInfo

from homeassistant.core import HomeAssistant

from .const import (
    DOMAIN,
    LUX_PER_WM2,
    PANEL_COUNT_ENTITY_ID,
    PANEL_WATTAGE_ENTITY_ID,
    STC_IRRADIANCE,
)


def safe_float(value: Any) -> float | None:
    if value in (None, "unknown", "unavailable", ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def device_info(entry: ConfigEntry) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name="Virtual Solar",
        manufacturer="virtuallytd",
        model="Virtual Solar",
        entry_type=DeviceEntryType.SERVICE,
        configuration_url="https://github.com/virtuallytd/ha-virtual-solar",
    )


def estimate_output(
    lux: float | None, panel_wattage: float, panel_count: float
) -> float | None:
    if lux is None:
        return None
    return (lux / LUX_PER_WM2) * (panel_wattage * panel_count / STC_IRRADIANCE)


def read_panel_config(
    hass: HomeAssistant, fallback_wattage: float, fallback_count: float
) -> tuple[float, float]:
    """Return (panel_wattage, panel_count) from the number entities.

    Falls back to the supplied defaults whenever the corresponding entity
    state isn't available yet (happens briefly during platform setup).
    """
    wattage_state = hass.states.get(PANEL_WATTAGE_ENTITY_ID)
    count_state = hass.states.get(PANEL_COUNT_ENTITY_ID)
    wattage = safe_float(wattage_state.state) if wattage_state else None
    count = safe_float(count_state.state) if count_state else None
    return (
        wattage if wattage is not None else fallback_wattage,
        count if count is not None else fallback_count,
    )
