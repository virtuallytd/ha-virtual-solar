"""Build a Lovelace dashboard config from a Virtual Solar config entry."""

from __future__ import annotations

from typing import Any

from .const import (
    BATTERY_CAPACITY_ENTITY_ID,
    BATTERY_LEVEL_ENTITY_ID,
    CHARGE_RATE_ENTITY_ID,
    CONF_BATTERY_CAPACITY,
    CONF_HOUSE_CONSUMPTION_SENSOR,
    CONF_LUX_SENSOR,
    CONF_PANEL_COUNT,
    CONF_PANEL_WATTAGE,
    OUTPUT_ENTITY_ID,
    PANEL_COUNT_ENTITY_ID,
    PANEL_WATTAGE_ENTITY_ID,
    PERCENTAGE_ENTITY_ID,
    STATUS_ENTITY_ID,
    SYSTEM_EFFICIENCY_ENTITY_ID,
    TIME_TO_FULL_ENTITY_ID,
)


def build_dashboard(config: dict[str, Any]) -> dict[str, Any]:
    """Return a Lovelace dashboard config populated from a config entry.

    Output matches the storage-mode raw-config format: just `views:` at
    the top, no `title:` (set via the UI), no `path:` (auto-slugged).
    """
    lux = config[CONF_LUX_SENSOR]
    house = config[CONF_HOUSE_CONSUMPTION_SENSOR]
    panel_wattage = float(config[CONF_PANEL_WATTAGE])
    panel_count = float(config[CONF_PANEL_COUNT])
    capacity = float(config[CONF_BATTERY_CAPACITY])
    max_output = max(int(panel_wattage * panel_count), 100)

    return {
        "views": [
            {
                "title": "Solar",
                "icon": "mdi:solar-panel",
                "cards": [
                    {
                        "type": "gauge",
                        "entity": OUTPUT_ENTITY_ID,
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
                        "entity": PERCENTAGE_ENTITY_ID,
                        "name": "Battery Level",
                        "min": 0,
                        "max": 100,
                        "needle": True,
                        "severity": {"green": 60, "yellow": 20, "red": 0},
                    },
                    {
                        "type": "entity",
                        "entity": STATUS_ENTITY_ID,
                        "name": "Battery Status",
                    },
                    {
                        "type": "entities",
                        "title": "Current Status",
                        "entities": [
                            {
                                "entity": OUTPUT_ENTITY_ID,
                                "name": "Solar Output",
                                "icon": "mdi:solar-panel",
                            },
                            {
                                "entity": house,
                                "name": "House Consumption",
                                "icon": "mdi:home-lightning-bolt",
                            },
                            {
                                "entity": CHARGE_RATE_ENTITY_ID,
                                "name": "Net Battery Flow",
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
                            {"entity": PERCENTAGE_ENTITY_ID, "name": "Charge Level"},
                            {
                                "entity": BATTERY_LEVEL_ENTITY_ID,
                                "name": "Energy Stored",
                            },
                            {
                                "entity": TIME_TO_FULL_ENTITY_ID,
                                "name": "Time to Full",
                            },
                            {
                                "entity": BATTERY_CAPACITY_ENTITY_ID,
                                "name": "Capacity",
                            },
                        ],
                    },
                    {
                        "type": "entities",
                        "title": "Simulation",
                        "entities": [
                            {
                                "entity": PANEL_WATTAGE_ENTITY_ID,
                                "name": "Panel wattage (W)",
                                "icon": "mdi:solar-panel",
                            },
                            {
                                "entity": PANEL_COUNT_ENTITY_ID,
                                "name": "Number of panels",
                                "icon": "mdi:solar-panel-large",
                            },
                            {
                                "entity": SYSTEM_EFFICIENCY_ENTITY_ID,
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
                            {"entity": OUTPUT_ENTITY_ID, "name": "Estimated Output (W)"},
                        ],
                    },
                    {
                        "type": "history-graph",
                        "title": "Battery Level (24h)",
                        "hours_to_show": 24,
                        "entities": [
                            {
                                "entity": BATTERY_LEVEL_ENTITY_ID,
                                "name": "Energy Stored (kWh)",
                            },
                        ],
                    },
                    {
                        "type": "history-graph",
                        "title": "Solar & Battery Flow (7 days)",
                        "hours_to_show": 168,
                        "entities": [
                            {"entity": OUTPUT_ENTITY_ID, "name": "Solar Output (W)"},
                            {
                                "entity": CHARGE_RATE_ENTITY_ID,
                                "name": "Net Battery Flow (W)",
                            },
                        ],
                    },
                ],
            }
        ],
    }


