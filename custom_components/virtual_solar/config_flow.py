"""Config and options flow for Virtual Solar."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import PERCENTAGE
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .const import (
    CONF_BATTERY_CAPACITY,
    CONF_HOUSE_CONSUMPTION_SENSOR,
    CONF_LUX_SENSOR,
    CONF_MAX_CHARGE_RATE,
    CONF_MAX_DISCHARGE_RATE,
    CONF_PANEL_COUNT,
    CONF_PANEL_WATTAGE,
    CONF_PROFILE,
    CONF_SYSTEM_EFFICIENCY,
    DEFAULT_BATTERY_CAPACITY,
    DEFAULT_MAX_CHARGE_RATE,
    DEFAULT_MAX_DISCHARGE_RATE,
    DEFAULT_PANEL_COUNT,
    DEFAULT_PANEL_WATTAGE,
    DEFAULT_SYSTEM_EFFICIENCY,
    DOMAIN,
)
from .util import apply_profile_defaults, async_load_profiles


def _with_default(
    key: str, defaults: dict[str, Any], fallback: Any = vol.UNDEFINED
) -> Any:
    if key in defaults and defaults[key] is not None:
        return defaults[key]
    return fallback


def _profile_schema(profiles: list[dict[str, Any]]) -> vol.Schema:
    options = [
        selector.SelectOptionDict(
            value=p["id"], label=p.get("name", p["id"])
        )
        for p in profiles
    ] or [selector.SelectOptionDict(value="custom", label="Custom (no preset)")]
    return vol.Schema(
        {
            vol.Required(CONF_PROFILE, default="custom"): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=options,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
        }
    )


def _sensors_schema(defaults: dict[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(
                CONF_LUX_SENSOR,
                default=_with_default(CONF_LUX_SENSOR, defaults),
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain="sensor", device_class="illuminance"
                ),
            ),
            vol.Required(
                CONF_HOUSE_CONSUMPTION_SENSOR,
                default=_with_default(CONF_HOUSE_CONSUMPTION_SENSOR, defaults),
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor", device_class="power"),
            ),
        }
    )


def _panel_schema(defaults: dict[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(
                CONF_PANEL_WATTAGE,
                default=_with_default(
                    CONF_PANEL_WATTAGE, defaults, DEFAULT_PANEL_WATTAGE
                ),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=100,
                    max=800,
                    step=10,
                    unit_of_measurement="W",
                    mode=selector.NumberSelectorMode.BOX,
                ),
            ),
            vol.Required(
                CONF_PANEL_COUNT,
                default=_with_default(CONF_PANEL_COUNT, defaults, DEFAULT_PANEL_COUNT),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1,
                    max=60,
                    step=1,
                    mode=selector.NumberSelectorMode.BOX,
                ),
            ),
        }
    )


def _battery_schema(defaults: dict[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(
                CONF_BATTERY_CAPACITY,
                default=_with_default(
                    CONF_BATTERY_CAPACITY, defaults, DEFAULT_BATTERY_CAPACITY
                ),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0.1,
                    max=100,
                    step=0.01,
                    unit_of_measurement="kWh",
                    mode=selector.NumberSelectorMode.BOX,
                ),
            ),
            vol.Required(
                CONF_MAX_CHARGE_RATE,
                default=_with_default(
                    CONF_MAX_CHARGE_RATE, defaults, DEFAULT_MAX_CHARGE_RATE
                ),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=100,
                    max=15000,
                    step=50,
                    unit_of_measurement="W",
                    mode=selector.NumberSelectorMode.BOX,
                ),
            ),
            vol.Required(
                CONF_MAX_DISCHARGE_RATE,
                default=_with_default(
                    CONF_MAX_DISCHARGE_RATE, defaults, DEFAULT_MAX_DISCHARGE_RATE
                ),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=100,
                    max=15000,
                    step=50,
                    unit_of_measurement="W",
                    mode=selector.NumberSelectorMode.BOX,
                ),
            ),
            vol.Required(
                CONF_SYSTEM_EFFICIENCY,
                default=_with_default(
                    CONF_SYSTEM_EFFICIENCY, defaults, DEFAULT_SYSTEM_EFFICIENCY
                ),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=50,
                    max=100,
                    step=1,
                    unit_of_measurement=PERCENTAGE,
                    mode=selector.NumberSelectorMode.BOX,
                ),
            ),
        }
    )


def _profile_by_id(
    profiles: list[dict[str, Any]], profile_id: str
) -> dict[str, Any] | None:
    for p in profiles:
        if p.get("id") == profile_id:
            return p
    return None


class VirtualSolarConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Initial setup flow."""

    VERSION = 3

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}
        self._profile: dict[str, Any] | None = None
        self._profiles: list[dict[str, Any]] = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        if not self._profiles:
            self._profiles = await async_load_profiles(self.hass)
        if user_input is not None:
            self._profile = _profile_by_id(self._profiles, user_input[CONF_PROFILE])
            return await self.async_step_sensors()
        return self.async_show_form(
            step_id="user", data_schema=_profile_schema(self._profiles)
        )

    async def async_step_sensors(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_panel()
        return self.async_show_form(
            step_id="sensors", data_schema=_sensors_schema({})
        )

    async def async_step_panel(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_battery()
        defaults = apply_profile_defaults(self._profile, {})
        return self.async_show_form(
            step_id="panel", data_schema=_panel_schema(defaults)
        )

    async def async_step_battery(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            self._data.update(user_input)
            return self.async_create_entry(title="Virtual Solar", data=self._data)
        defaults = apply_profile_defaults(self._profile, {})
        return self.async_show_form(
            step_id="battery", data_schema=_battery_schema(defaults)
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> VirtualSolarOptionsFlow:
        return VirtualSolarOptionsFlow(config_entry)


class VirtualSolarOptionsFlow(config_entries.OptionsFlow):
    """Edit configuration after install."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._entry = config_entry
        self._data: dict[str, Any] = {}

    def _defaults(self) -> dict[str, Any]:
        merged: dict[str, Any] = {**self._entry.data, **self._entry.options}
        merged.update(self._data)
        return merged

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_battery()
        return self.async_show_form(
            step_id="init", data_schema=_sensors_schema(self._defaults())
        )

    async def async_step_battery(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            self._data.update(user_input)
            return self.async_create_entry(title="", data=self._data)
        return self.async_show_form(
            step_id="battery", data_schema=_battery_schema(self._defaults())
        )
