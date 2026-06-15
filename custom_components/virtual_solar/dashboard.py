"""Build a Lovelace dashboard config from a Virtual Solar config entry."""

from __future__ import annotations

from typing import Any

import yaml

from .const import (
    BATTERY_LEVEL_ENTITY_ID,
    CONF_BATTERY_CAPACITY,
    CONF_HOUSE_CONSUMPTION_SENSOR,
    CONF_LUX_SENSOR,
    CONF_PANEL_COUNT,
    CONF_PANEL_WATTAGE,
)

OUTPUT_SENSOR = "sensor.virtual_solar_estimated_output"
STATUS_SENSOR = "sensor.virtual_solar_battery_status"


def build_dashboard(config: dict[str, Any]) -> dict[str, Any]:
    """Return a dashboard config dict populated with entities from the config entry."""
    lux = config[CONF_LUX_SENSOR]
    house = config[CONF_HOUSE_CONSUMPTION_SENSOR]
    panel_wattage = float(config[CONF_PANEL_WATTAGE])
    panel_count = float(config[CONF_PANEL_COUNT])
    capacity = float(config[CONF_BATTERY_CAPACITY])
    max_output = max(int(panel_wattage * panel_count), 100)

    return {
        "title": "Solar",
        "views": [
            {
                "title": "Solar",
                "path": "solar",
                "icon": "mdi:solar-panel",
                "cards": [
                    {
                        "type": "gauge",
                        "entity": OUTPUT_SENSOR,
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
                        "entity": BATTERY_LEVEL_ENTITY_ID,
                        "name": "Battery Level",
                        "min": 0,
                        "max": capacity,
                        "needle": True,
                        "severity": {
                            "green": capacity * 0.6,
                            "yellow": capacity * 0.2,
                            "red": 0,
                        },
                    },
                    {
                        "type": "entity",
                        "entity": STATUS_SENSOR,
                        "name": "Battery Status",
                    },
                    {
                        "type": "entities",
                        "title": "Current Status",
                        "entities": [
                            {
                                "entity": OUTPUT_SENSOR,
                                "name": "Solar Output",
                                "icon": "mdi:solar-panel",
                            },
                            {
                                "entity": house,
                                "name": "House Consumption",
                                "icon": "mdi:home-lightning-bolt",
                            },
                            {
                                "entity": BATTERY_LEVEL_ENTITY_ID,
                                "name": "Stored Energy",
                                "icon": "mdi:battery",
                            },
                            {
                                "entity": lux,
                                "name": "Light Level",
                                "icon": "mdi:brightness-5",
                            },
                        ],
                    },
                    {
                        "type": "history-graph",
                        "title": "Solar Output (24h)",
                        "hours_to_show": 24,
                        "entities": [
                            {"entity": OUTPUT_SENSOR, "name": "Estimated Output (W)"},
                        ],
                    },
                    {
                        "type": "history-graph",
                        "title": "Solar & Battery (7 days)",
                        "hours_to_show": 168,
                        "refresh_interval": 300,
                        "entities": [
                            {"entity": OUTPUT_SENSOR, "name": "Solar Output (W)"},
                            {
                                "entity": BATTERY_LEVEL_ENTITY_ID,
                                "name": "Stored Energy (kWh)",
                            },
                        ],
                    },
                ],
            }
        ],
    }


def dashboard_yaml(config: dict[str, Any]) -> str:
    """Serialise the dashboard config to a YAML string."""
    return yaml.safe_dump(
        build_dashboard(config),
        default_flow_style=False,
        sort_keys=False,
        allow_unicode=True,
    )
