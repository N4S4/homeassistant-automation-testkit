"""Config flow for Automation Test Kit.

Single-instance: the flow has no options, it just creates the entry that
triggers panel + WebSocket setup.
"""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigFlow

from .const import DOMAIN


class AutomationTestKitConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Automation Test Kit."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> Any:
        """Create the single entry (no options)."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        return self.async_create_entry(title="Automation Test Kit", data={})
