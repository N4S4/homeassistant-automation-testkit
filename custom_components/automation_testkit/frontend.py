"""Frontend panel registration for Automation Test Kit.

Serves the panel JS as a static path and registers a native (non-iframe) sidebar
panel. The panel is a vanilla-JS custom element; it receives the `hass` object
via HA's `setCustomPanelProperties` and drives everything through HA's own
WebSocket / service APIs.
"""

from __future__ import annotations

from pathlib import Path

from homeassistant.components import frontend
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

from .const import PANEL_NAME, PANEL_URL_PATH, STATIC_URL_PATH


async def async_setup_frontend(hass: HomeAssistant) -> None:
    """Serve the panel assets and register the sidebar panel."""
    await hass.http.async_register_static_paths(
        [
            StaticPathConfig(
                url_path=STATIC_URL_PATH,
                path=str(Path(__file__).parent / "frontend"),
                cache_headers=False,
            )
        ]
    )

    frontend.async_register_built_in_panel(
        hass,
        component_name="custom",
        sidebar_title="Automation Test Kit",
        sidebar_icon="mdi:flask-outline",
        frontend_url_path=PANEL_URL_PATH,
        config={
            "_panel_custom": {
                "name": PANEL_NAME,
                "module_url": f"{STATIC_URL_PATH}/panel.js",
                "embed_iframe": False,
                "trust_external": False,
            }
        },
        require_admin=True,
    )
