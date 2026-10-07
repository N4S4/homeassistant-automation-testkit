"""Automation Test Kit: test Home Assistant automations without waiting for events.

Native sidebar panel + WebSocket commands to browse traces, replay actions,
simulate a trigger in isolation, and dry-run the full pipeline without touching
devices.
"""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .frontend import async_setup_frontend
from .websocket_api import async_register_commands

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the panel and WebSocket API from a config entry."""
    await async_setup_frontend(hass)

    # Register the WS commands once (single-instance integration).
    if DOMAIN not in hass.data:
        async_register_commands(hass)
        hass.data[DOMAIN] = entry.entry_id

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Remove the panel on unload."""
    from homeassistant.components import frontend

    from .const import PANEL_URL_PATH

    if hass.data.get(DOMAIN) == entry.entry_id:
        frontend.async_remove_panel(hass, PANEL_URL_PATH)
        hass.data.pop(DOMAIN, None)

    return True
