"""Shared helpers for the Virtual Solar integration."""

from __future__ import annotations

import logging
import pathlib
from typing import Any

import yaml
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity import DeviceInfo

from .const import (
    BATTERY_CAPACITY_ENTITY_ID,
    CONF_BATTERY_CAPACITY,
    CONF_SYSTEM_EFFICIENCY,
    DEFAULT_BATTERY_CAPACITY,
    DEFAULT_SYSTEM_EFFICIENCY,
    DOMAIN,
    LUX_PER_WM2,
    PANEL_COUNT_ENTITY_ID,
    PANEL_WATTAGE_ENTITY_ID,
    STC_IRRADIANCE,
    SYSTEM_EFFICIENCY_ENTITY_ID,
)

_LOGGER = logging.getLogger(__name__)
_PROFILES_PATH = pathlib.Path(__file__).parent / "profiles.yaml"
_PROFILES_CACHE: list[dict[str, Any]] | None = None


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
    lux: float | None,
    panel_wattage: float,
    panel_count: float,
    efficiency: float = 1.0,
) -> float | None:
    """Estimated panel output in watts after applying system efficiency."""
    if lux is None:
        return None
    raw = (lux / LUX_PER_WM2) * (panel_wattage * panel_count / STC_IRRADIANCE)
    return raw * efficiency


def read_panel_config(
    hass: HomeAssistant, fallback_wattage: float, fallback_count: float
) -> tuple[float, float]:
    """Return (panel_wattage, panel_count) from the number entities."""
    wattage_state = hass.states.get(PANEL_WATTAGE_ENTITY_ID)
    count_state = hass.states.get(PANEL_COUNT_ENTITY_ID)
    wattage = safe_float(wattage_state.state) if wattage_state else None
    count = safe_float(count_state.state) if count_state else None
    return (
        wattage if wattage is not None else fallback_wattage,
        count if count is not None else fallback_count,
    )


def read_capacity(hass: HomeAssistant, fallback: float) -> float:
    state = hass.states.get(BATTERY_CAPACITY_ENTITY_ID)
    cap = safe_float(state.state) if state else None
    return cap if cap is not None else fallback


def read_system_efficiency(hass: HomeAssistant, fallback_pct: float) -> float:
    """Return system efficiency as a 0-1 multiplier (entity is stored as %)."""
    state = hass.states.get(SYSTEM_EFFICIENCY_ENTITY_ID)
    pct = safe_float(state.state) if state else None
    if pct is None:
        pct = fallback_pct
    return pct / 100.0


def _load_profiles_sync() -> list[dict[str, Any]]:
    try:
        text = _PROFILES_PATH.read_text(encoding="utf-8")
        data = yaml.safe_load(text) or []
        if not isinstance(data, list):
            _LOGGER.warning("profiles.yaml is not a list, ignoring")
            return []
        return data
    except FileNotFoundError:
        return []
    except yaml.YAMLError as exc:
        _LOGGER.warning("Failed to parse profiles.yaml: %s", exc)
        return []


async def async_load_profiles(hass: HomeAssistant) -> list[dict[str, Any]]:
    """Load profiles off the event loop, cached for the process lifetime."""
    global _PROFILES_CACHE
    if _PROFILES_CACHE is None:
        _PROFILES_CACHE = await hass.async_add_executor_job(_load_profiles_sync)
    return _PROFILES_CACHE


def apply_profile_defaults(
    profile: dict[str, Any] | None, base: dict[str, Any]
) -> dict[str, Any]:
    """Return `base` with any missing keys filled in from `profile`."""
    if not profile:
        return base
    merged = {**base}
    mapping = {
        "battery_capacity_kwh": CONF_BATTERY_CAPACITY,
        "system_efficiency_pct": CONF_SYSTEM_EFFICIENCY,
    }
    for src, dst in mapping.items():
        if dst not in merged and src in profile:
            merged[dst] = profile[src]
    # Direct (same key name) mappings
    for key in (
        "panel_wattage",
        "panel_count",
        "max_charge_rate",
        "max_discharge_rate",
    ):
        # profile uses *_w suffix on rate fields
        src = {
            "max_charge_rate": "max_charge_rate_w",
            "max_discharge_rate": "max_discharge_rate_w",
        }.get(key, key)
        if key not in merged and src in profile:
            merged[key] = profile[src]
    return merged
