"""WebSocket API for Automation Test Kit.

Exposes one command: `automation_testkit/parse_trace`, which runs the pure
parser over a raw `trace/get` payload and returns a structured view. The
frontend panel reads raw traces via HA's built-in `trace/list` / `trace/get`
commands and replays via the `automation.trigger` service, so only the parsing
needs a custom command here.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.components.automation import DOMAIN as AUTOMATION_DOMAIN
from homeassistant.components.trace.util import async_get_trace, async_list_traces
from homeassistant.core import Context, HomeAssistant, ServiceRegistry, callback
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .parser import (
    build_trigger_events,
    condition_results,
    entity_id_from_trace,
    executed_triggers,
    parse_trace,
)


@callback
def async_register_commands(hass: HomeAssistant) -> None:
    """Register the WebSocket commands."""
    websocket_api.async_register_command(hass, ws_parse_trace)
    websocket_api.async_register_command(hass, ws_simulate)
    websocket_api.async_register_command(hass, ws_config)
    websocket_api.async_register_command(hass, ws_dry_run)


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/parse_trace",
        vol.Required("trace"): dict,
    }
)
@websocket_api.async_response
async def ws_parse_trace(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Parse a raw `trace/get` payload into a structured view."""
    raw = msg["trace"]

    result = {
        "trace": asdict(parse_trace(raw)),
        "trigger_events": build_trigger_events(raw),
        "executed_triggers": executed_triggers(raw),
        "entity_id": entity_id_from_trace(raw),
    }

    connection.send_result(msg["id"], result)


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/simulate",
        vol.Required("entity_id"): str,
        vol.Required("trigger"): dict,
        vol.Optional("skip_condition", default=False): bool,
    }
)
@websocket_api.async_response
async def ws_simulate(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Inject a trigger variable into a single automation (isolated).

    Calls the automation entity's internal `async_trigger` directly with a
    reconstructed `trigger` variable. This is isolated (no event fired on the
    bus, so no other automation reacts) and runs the full pipeline: trigger
    variable -> conditions (when skip_condition=False) -> actions.
    """
    component = hass.data.get(AUTOMATION_DOMAIN)
    entity = component.get_entity(msg["entity_id"]) if component is not None else None
    if entity is None:
        connection.send_error(
            msg["id"], websocket_api.ERR_NOT_FOUND, "Automation not found"
        )
        return

    try:
        await entity.async_trigger(
            {"trigger": msg["trigger"]},
            context=Context(),
            skip_condition=msg["skip_condition"],
        )
    except Exception as exc:  # noqa: BLE001 — surface any runtime error to the caller
        connection.send_error(msg["id"], "unknown_error", str(exc))
        return

    connection.send_result(
        msg["id"], {"triggered": True, "entity_id": msg["entity_id"]}
    )


def build_synthetic_trigger(hass: HomeAssistant, idx: int, cfg: dict) -> dict[str, Any]:
    """Build a best-effort synthetic `trigger` variable from a trigger config.

    Lets an automation that has never run (no trace) still be simulated: we
    construct the `trigger` variable the trigger WOULD have produced, instead of
    firing the real event / mocking time. State triggers use the entity's current
    state as a base; time triggers use "now".
    """
    platform = cfg.get("platform") or cfg.get("trigger") or "event"
    trigger: dict[str, Any] = {
        "platform": platform,
        "id": str(idx),
        "idx": str(idx),
    }

    if platform == "event":
        event_type = cfg.get("event_type", "custom_event")
        trigger["description"] = cfg.get("alias") or f"event '{event_type}'"
        trigger["event"] = {"event_type": event_type, "data": cfg.get("event_data", {})}
    elif platform == "homeassistant":
        ev = cfg.get("event", "start")
        trigger["description"] = cfg.get("alias") or f"homeassistant '{ev}'"
        trigger["event"] = ev
    elif platform in ("state", "numeric_state"):
        entity_id = cfg.get("entity_id", "")
        cur = hass.states.get(entity_id)
        state_val = cur.state if cur else "0"
        to = cfg.get("to")
        if platform == "state" and to is not None:
            state_val = to[0] if isinstance(to, (list, tuple)) else to
        trigger["description"] = cfg.get("alias") or f"{platform} of {entity_id or '?'}"
        trigger["entity_id"] = entity_id
        trigger["to_state"] = {
            "entity_id": entity_id,
            "state": str(state_val),
            "attributes": dict(cur.attributes) if cur else {},
        }
    elif platform in ("time", "time_pattern"):
        trigger["description"] = cfg.get("alias") or platform
        now = dt_util.now()
        at = cfg.get("at")
        if at:
            at = at[0] if isinstance(at, list) else at
            try:
                parts = str(at).split(":")
                now = now.replace(
                    hour=int(parts[0]),
                    minute=int(parts[1]) if len(parts) > 1 else 0,
                    second=0,
                    microsecond=0,
                )
            except (ValueError, TypeError):
                pass
        trigger["now"] = now.isoformat()
    elif platform == "sun":
        ev = cfg.get("event", "sunrise")
        trigger["description"] = cfg.get("alias") or f"sun '{ev}'"
        trigger["event"] = ev
    else:
        trigger["description"] = cfg.get("alias") or f"{platform} trigger"

    return trigger


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/config",
        vol.Required("entity_id"): str,
    }
)
@websocket_api.async_response
async def ws_config(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Return an automation's config as synthetic trigger variables + conditions/actions."""
    component = hass.data.get(AUTOMATION_DOMAIN)
    entity = component.get_entity(msg["entity_id"]) if component is not None else None
    if entity is None:
        connection.send_error(
            msg["id"], websocket_api.ERR_NOT_FOUND, "Automation not found"
        )
        return

    raw = getattr(entity, "raw_config", None) or {}
    triggers_cfg = raw.get("triggers", []) or []
    if isinstance(triggers_cfg, dict):
        triggers_cfg = [triggers_cfg]
    triggers = [
        build_synthetic_trigger(hass, i, cfg)
        for i, cfg in enumerate(triggers_cfg)
    ]

    connection.send_result(
        msg["id"],
        {
            "triggers": triggers,
            "conditions": raw.get("conditions") or [],
            "actions": raw.get("actions") or [],
        },
    )


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/dry_run",
        vol.Required("entity_id"): str,
        vol.Required("trigger"): dict,
        vol.Optional("skip_condition", default=False): bool,
    }
)
@websocket_api.async_response
async def ws_dry_run(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Dry-run an automation: full pipeline, but intercept service calls.

    Conditions are evaluated and templates are rendered for real, so branches
    and resolved data are accurate — but every service call is captured instead
    of dispatched, so no device is touched. Interception is scoped by context,
    so concurrent automations are unaffected.
    """
    component = hass.data.get(AUTOMATION_DOMAIN)
    entity = component.get_entity(msg["entity_id"]) if component is not None else None
    if entity is None:
        connection.send_error(
            msg["id"], websocket_api.ERR_NOT_FOUND, "Automation not found"
        )
        return

    dry_context = Context()
    calls: list[dict[str, Any]] = []
    original = ServiceRegistry.async_call

    async def fake_async_call(
        self,
        domain: str,
        service: str,
        service_data: dict[str, Any] | None = None,
        blocking: bool = False,
        context: Context | None = None,
        target: dict[str, Any] | None = None,
        return_response: bool = False,
    ) -> dict[str, Any] | None:
        if context is not None and context.parent_id == dry_context.id:
            calls.append(
                {
                    "domain": domain,
                    "service": service,
                    "data": service_data,
                    "target": target,
                }
            )
            return {} if return_response else None
        return await original(
            self, domain, service, service_data, blocking=blocking,
            context=context, target=target, return_response=return_response,
        )

    ServiceRegistry.async_call = fake_async_call  # type: ignore[method-assign]
    try:
        await entity.async_trigger(
            {"trigger": msg["trigger"]},
            context=dry_context,
            skip_condition=msg["skip_condition"],
        )
    finally:
        ServiceRegistry.async_call = original  # type: ignore[method-assign]

    script_execution = None
    conditions: list[dict[str, Any]] = []
    try:
        key = f"automation.{entity.unique_id}"
        traces = await async_list_traces(hass, "automation", key)
        if traces:
            latest = traces[-1]
            script_execution = latest.get("script_execution")
            run_id = latest.get("run_id")
            if run_id:
                full = await async_get_trace(hass, key, run_id)
                conditions = condition_results(full)
    except Exception:  # noqa: BLE001 — outcome is best-effort
        pass

    connection.send_result(
        msg["id"],
        {
            "calls": calls,
            "script_execution": script_execution,
            "conditions": conditions,
        },
    )
