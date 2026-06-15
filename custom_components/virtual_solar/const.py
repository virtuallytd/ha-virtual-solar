"""Constants for the Virtual Solar integration."""

DOMAIN = "virtual_solar"

CONF_LUX_SENSOR = "lux_sensor"
CONF_HOUSE_CONSUMPTION_SENSOR = "house_consumption_sensor"
CONF_PANEL_WATTAGE = "panel_wattage"
CONF_PANEL_COUNT = "panel_count"
CONF_BATTERY_CAPACITY = "battery_capacity"
CONF_MAX_CHARGE_RATE = "max_charge_rate"

DEFAULT_PANEL_WATTAGE = 500
DEFAULT_PANEL_COUNT = 1
DEFAULT_BATTERY_CAPACITY = 2.68
DEFAULT_MAX_CHARGE_RATE = 1200

LUX_PER_WM2 = 120.0
STC_IRRADIANCE = 1000.0
TICK_INTERVAL_SECONDS = 60

BATTERY_LEVEL_ENTITY_ID = "number.virtual_solar_battery_level"

STATE_CHARGING = "Charging"
STATE_DISCHARGING = "Discharging"
STATE_FULL = "Full"
STATE_EMPTY = "Empty"
