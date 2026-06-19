"""Constants for the Virtual Solar integration."""

DOMAIN = "virtual_solar"

CONF_LUX_SENSOR = "lux_sensor"
CONF_HOUSE_CONSUMPTION_SENSOR = "house_consumption_sensor"
CONF_PANEL_WATTAGE = "panel_wattage"
CONF_PANEL_COUNT = "panel_count"
CONF_BATTERY_CAPACITY = "battery_capacity"
CONF_MAX_CHARGE_RATE = "max_charge_rate"
CONF_MAX_DISCHARGE_RATE = "max_discharge_rate"
CONF_SYSTEM_EFFICIENCY = "system_efficiency"
CONF_PROFILE = "profile"

DEFAULT_PANEL_WATTAGE = 500
DEFAULT_PANEL_COUNT = 1
DEFAULT_BATTERY_CAPACITY = 2.68
DEFAULT_MAX_CHARGE_RATE = 1200
DEFAULT_MAX_DISCHARGE_RATE = 1200
DEFAULT_SYSTEM_EFFICIENCY = 95

LUX_PER_WM2 = 120.0
STC_IRRADIANCE = 1000.0
TICK_INTERVAL_SECONDS = 60

BATTERY_LEVEL_ENTITY_ID = "number.virtual_solar_battery_level"
BATTERY_CAPACITY_ENTITY_ID = "number.virtual_solar_battery_capacity"
SYSTEM_EFFICIENCY_ENTITY_ID = "number.virtual_solar_system_efficiency"
PANEL_COUNT_ENTITY_ID = "number.virtual_solar_panel_count"
PANEL_WATTAGE_ENTITY_ID = "number.virtual_solar_panel_wattage"
OUTPUT_ENTITY_ID = "sensor.virtual_solar_estimated_output"
STATUS_ENTITY_ID = "sensor.virtual_solar_battery_status"
PERCENTAGE_ENTITY_ID = "sensor.virtual_solar_battery_percentage"
CHARGE_RATE_ENTITY_ID = "sensor.virtual_solar_battery_charge_rate"
TIME_TO_FULL_ENTITY_ID = "sensor.virtual_solar_battery_time_to_full"
GRID_EXPORT_ENTITY_ID = "sensor.virtual_solar_grid_export"

STATE_CHARGING = "Charging"
STATE_DISCHARGING = "Discharging"
STATE_FULL = "Full"
STATE_EMPTY = "Empty"
