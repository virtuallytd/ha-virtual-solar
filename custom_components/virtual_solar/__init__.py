"""The Virtual Solar integration."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, Platform
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
from .dashboard import build_dashboard

PLATFORMS: list[Platform] = [Platform.NUMBER, Platform.SENSOR]

SERVICE_GET_DASHBOARD = "get_dashboard"


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Virtual Solar from a config entry.

    Platforms are set up sequentially (number before sensor) so that the
    sensors can resolve their sibling number entities via the entity
    registry when they first run `async_added_to_hass`. This matters
    because several sensors read live values from number entities in the
    same config entry.
    """
    await hass.config_entries.async_forward_entry_setups(entry, [Platform.NUMBER])
    await hass.config_entries.async_forward_entry_setups(entry, [Platform.SENSOR])
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
    if version == 3:
        # v4 introduces multi-instance support. Existing entries need a
        # name in data so the sensors and dashboard can reference it.
        data.setdefault(CONF_NAME, entry.title or "Virtual Solar")
        version = 4
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

        # Optional entry_id: return just that entry's dashboard.
        # Omitted: return a combined dashboard with one view per entry.
        entry_id = call.data.get("entry_id") if call.data else None
        if entry_id:
            selected = [e for e in entries if e.entry_id == entry_id]
            if not selected:
                raise HomeAssistantError(
                    f"No Virtual Solar entry found with id {entry_id!r}."
                )
            return build_dashboard(hass, selected)
        return build_dashboard(hass, entries)

    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_DASHBOARD,
        _get_dashboard,
        supports_response=SupportsResponse.ONLY,
    )
