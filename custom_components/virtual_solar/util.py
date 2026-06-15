"""Shared helpers for the Virtual Solar integration."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN, LUX_PER_WM2, STC_IRRADIANCE


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
        manufacturer="Anthony Davis",
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
