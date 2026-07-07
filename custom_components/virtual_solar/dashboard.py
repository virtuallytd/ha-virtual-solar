"""Build a Lovelace dashboard config from Virtual Solar config entries."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    BATTERY_CAPACITY_ENTITY_ID,
    BATTERY_LEVEL_ENTITY_ID,
    CHARGE_RATE_ENTITY_ID,
    CONF_BATTERY_CAPACITY,
    CONF_HOUSE_CONSUMPTION_SENSOR,
    CONF_LUX_SENSOR,
    CONF_PANEL_COUNT,
    CONF_PANEL_WATTAGE,
    GRID_EXPORT_ENTITY_ID,
    OUTPUT_ENTITY_ID,
    PANEL_COUNT_ENTITY_ID,
    PANEL_WATTAGE_ENTITY_ID,
    PERCENTAGE_ENTITY_ID,
    STATUS_ENTITY_ID,
    SYSTEM_EFFICIENCY_ENTITY_ID,
    TIME_TO_FULL_ENTITY_ID,
)
from .util import sibling_entity_id

# Fallback maps sibling keys to the entity_id used before multi-instance
# support existed. If the entity registry lookup fails (e.g. during a
# brief window at startup) we still emit a sensible YAML.
_FALLBACK: dict[str, str] = {
    "estimated_output": OUTPUT_ENTITY_ID,
    "battery_percentage": PERCENTAGE_ENTITY_ID,
    "battery_status": STATUS_ENTITY_ID,
    "battery_charge_rate": CHARGE_RATE_ENTITY_ID,
    "battery_time_to_full": TIME_TO_FULL_ENTITY_ID,
    "grid_export": GRID_EXPORT_ENTITY_ID,
    "battery_level": BATTERY_LEVEL_ENTITY_ID,
    "battery_capacity": BATTERY_CAPACITY_ENTITY_ID,
    "panel_count": PANEL_COUNT_ENTITY_ID,
    "panel_wattage": PANEL_WATTAGE_ENTITY_ID,
    "system_efficiency": SYSTEM_EFFICIENCY_ENTITY_ID,
}


def _e(hass: HomeAssistant, entry_id: str, key: str) -> str:
    """Resolve the entity_id for a sibling in the given entry."""
    return sibling_entity_id(hass, entry_id, key) or _FALLBACK[key]


def _build_view(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, Any]:
    """Return the view (title, cards) for a single config entry."""
    config: dict[str, Any] = {**entry.data, **entry.options}
    lux = config[CONF_LUX_SENSOR]
    house = config[CONF_HOUSE_CONSUMPTION_SENSOR]
    panel_wattage = float(config[CONF_PANEL_WATTAGE])
    panel_count = float(config[CONF_PANEL_COUNT])
    max_output = max(int(panel_wattage * panel_count), 100)
    eid = lambda key: _e(hass, entry.entry_id, key)

    return {
        "title": entry.title,
        "icon": "mdi:solar-panel",
        "cards": [
            {
                "type": "gauge",
                "entity": eid("estimated_output"),
                "name": "Estimated Solar Output",
                "min": 0,
                "max": max_output,
                "needle": True,
                "severity": {
                    "green": max(max_output // 4, 1),
                    "yellow": max(max_output // 10, 1),
                    "red": 0,
                },
            },
            {
                "type": "gauge",
                "entity": eid("battery_percentage"),
                "name": "Battery Level",
                "min": 0,
                "max": 100,
                "needle": True,
                "severity": {"green": 60, "yellow": 20, "red": 0},
            },
            {
                "type": "entity",
                "entity": eid("battery_status"),
                "name": "Battery Status",
            },
            {
                "type": "entities",
                "title": "Current Status",
                "entities": [
                    {
                        "entity": eid("estimated_output"),
                        "name": "Solar Output",
                        "icon": "mdi:solar-panel",
                    },
                    {
                        "entity": house,
                        "name": "House Consumption",
                        "icon": "mdi:home-lightning-bolt",
                    },
                    {
                        "entity": eid("battery_charge_rate"),
                        "name": "Net Battery Flow",
                    },
                    {
                        "entity": eid("grid_export"),
                        "name": "Grid Export",
                    },
                    {
                        "entity": lux,
                        "name": "Light Level",
                        "icon": "mdi:brightness-5",
                    },
                ],
            },
            {
                "type": "entities",
                "title": "Battery",
                "entities": [
                    {"entity": eid("battery_percentage"), "name": "Charge Level"},
                    {"entity": eid("battery_level"), "name": "Energy Stored"},
                    {
                        "entity": eid("battery_time_to_full"),
                        "name": "Time to Full",
                    },
                    {"entity": eid("battery_capacity"), "name": "Capacity"},
                ],
            },
            {
                "type": "entities",
                "title": "Simulation",
                "entities": [
                    {
                        "entity": eid("panel_wattage"),
                        "name": "Panel wattage (W)",
                        "icon": "mdi:solar-panel",
                    },
                    {
                        "entity": eid("panel_count"),
                        "name": "Number of panels",
                        "icon": "mdi:solar-panel-large",
                    },
                    {
                        "entity": eid("system_efficiency"),
                        "name": "System efficiency",
                        "icon": "mdi:gauge",
                    },
                ],
            },
            {
                "type": "history-graph",
                "title": "Solar Output (24h)",
                "hours_to_show": 24,
                "entities": [
                    {
                        "entity": eid("estimated_output"),
                        "name": "Estimated Output (W)",
                    },
                ],
            },
            {
                "type": "history-graph",
                "title": "Battery Level (24h)",
                "hours_to_show": 24,
                "entities": [
                    {
                        "entity": eid("battery_level"),
                        "name": "Energy Stored (kWh)",
                    },
                ],
            },
            {
                "type": "history-graph",
                "title": "Solar & Battery Flow (7 days)",
                "hours_to_show": 168,
                "entities": [
                    {
                        "entity": eid("estimated_output"),
                        "name": "Solar Output (W)",
                    },
                    {
                        "entity": eid("battery_charge_rate"),
                        "name": "Net Battery Flow (W)",
                    },
                ],
            },
        ],
    }


def build_dashboard(
    hass: HomeAssistant, entries: list[ConfigEntry]
) -> dict[str, Any]:
    """Return a Lovelace dashboard covering one or more Virtual Solar entries.

    Each entry gets its own view (tab) titled after the entry. Output
    matches the storage-mode raw-config format: just `views:` at the top,
    no top-level `title:` or `path:`.
    """
    return {"views": [_build_view(hass, entry) for entry in entries]}
