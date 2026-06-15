"""The Virtual Solar integration."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
)
from homeassistant.exceptions import HomeAssistantError

from .const import (
    CONF_MAX_CHARGE_RATE,
    CONF_MAX_DISCHARGE_RATE,
    CONF_SYSTEM_EFFICIENCY,
    DEFAULT_MAX_CHARGE_RATE,
    DEFAULT_MAX_DISCHARGE_RATE,
    DEFAULT_SYSTEM_EFFICIENCY,
    DOMAIN,
)
from .dashboard import build_dashboard, dashboard_yaml

PLATFORMS: list[Platform] = [Platform.NUMBER, Platform.SENSOR]

SERVICE_GET_DASHBOARD = "get_dashboard"


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Virtual Solar from a config entry."""
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))
    _async_register_services(hass)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate an existing config entry to the current schema."""
    data = {**entry.data}
    version = entry.version
    if version == 1:
        data.pop("battery_level_sensor", None)
        data.setdefault(CONF_MAX_CHARGE_RATE, DEFAULT_MAX_CHARGE_RATE)
        version = 2
    if version == 2:
        # v3 splits charge/discharge and adds system efficiency.
        existing_rate = data.get(CONF_MAX_CHARGE_RATE, DEFAULT_MAX_CHARGE_RATE)
        data.setdefault(CONF_MAX_DISCHARGE_RATE, existing_rate)
        data.setdefault(CONF_SYSTEM_EFFICIENCY, DEFAULT_SYSTEM_EFFICIENCY)
        version = 3
    if version != entry.version:
        hass.config_entries.async_update_entry(entry, data=data, version=version)
    return True


async def _async_options_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the entry whenever options change so entities pick up new values."""
    await hass.config_entries.async_reload(entry.entry_id)


def _async_register_services(hass: HomeAssistant) -> None:
    """Register domain-wide services once."""
    if hass.services.has_service(DOMAIN, SERVICE_GET_DASHBOARD):
        return

    async def _get_dashboard(call: ServiceCall) -> ServiceResponse:
        entries = hass.config_entries.async_entries(DOMAIN)
        if not entries:
            raise HomeAssistantError("Virtual Solar is not configured.")
        entry = entries[0]
        config: dict[str, Any] = {**entry.data, **entry.options}
        return {
            "yaml": dashboard_yaml(config),
            "config": build_dashboard(config),
        }

    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_DASHBOARD,
        _get_dashboard,
        supports_response=SupportsResponse.ONLY,
    )
