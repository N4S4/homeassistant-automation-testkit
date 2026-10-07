"""Pure parsing of Home Assistant automation traces.

No network I/O: every function maps a trace dict (as returned by the
`trace/get` WebSocket command) to a structured, testable form. This is the
unit-testable core of the automation test kit.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# platform "homeassistant" `event` -> internal HA event name
HOMEASSISTANT_EVENT_MAP = {
    "start": "homeassistant_start",
    "shutdown": "homeassistant_stop",
    "final_write": "homeassistant_final_write",
}


@dataclass
class TraceData:
    """Structured view of a single automation trace run."""

    domain: str
    item_id: str
    run_id: str
    alias: str
    state: str
    script_execution: str
    trigger_description: str
    error: str | None
    triggers: list[dict]
    conditions: list[dict]
    actions: list[dict]
    trigger_executions: dict[str, list[dict]]
    action_executions: dict[str, list[dict]]


def parse_trace(trace: dict[str, Any]) -> TraceData:
    """Parse the flat `trace/get` response into a structured TraceData."""
    config = trace.get("config", {})
    steps = trace.get("trace", {})

    trigger_executions: dict[str, list[dict]] = {}
    action_executions: dict[str, list[dict]] = {}
    for path, steps_list in steps.items():
        if not isinstance(steps_list, list):
            continue
        if path.startswith("trigger/"):
            trigger_executions[path] = steps_list
        elif path.startswith("action/"):
            action_executions[path] = steps_list

    return TraceData(
        domain=trace.get("domain", ""),
        item_id=trace.get("item_id", ""),
        run_id=trace.get("run_id", ""),
        alias=config.get("alias", ""),
        state=trace.get("state", ""),
        script_execution=trace.get("script_execution", ""),
        trigger_description=trace.get("trigger", ""),
        error=trace.get("error"),
        triggers=config.get("triggers", []),
        conditions=config.get("conditions", []),
        actions=config.get("actions", []),
        trigger_executions=trigger_executions,
        action_executions=action_executions,
    )


def build_trigger_events(trace: dict[str, Any]) -> list[dict[str, Any]]:
    """Map each configured trigger to a simulation spec (how to re-fire it).

    For each trigger in `config.triggers`, return a dict describing how to
    re-fire that trigger, or `{"simulatable": False, "reason": ...}` when no
    clean re-fire path exists (e.g. time/sun triggers).
    """
    config = trace.get("config", {})
    return [_simulation_spec(t) for t in config.get("triggers", [])]


def _simulation_spec(trigger: dict[str, Any]) -> dict[str, Any]:
    platform = trigger.get("trigger") or trigger.get("platform")

    if platform == "homeassistant":
        event = trigger.get("event")
        ha_event = HOMEASSISTANT_EVENT_MAP.get(event)
        if ha_event is None:
            return {
                "simulatable": False,
                "platform": "homeassistant",
                "reason": f"unsupported homeassistant event: {event}",
            }
        return {
            "simulatable": True,
            "platform": "homeassistant",
            "event": event,
            "fire_event": ha_event,
        }

    if platform == "event":
        return {
            "simulatable": True,
            "platform": "event",
            "event_type": trigger.get("event_type"),
            "event_data": trigger.get("event_data") or {},
        }

    if platform == "state":
        return {
            "simulatable": True,
            "platform": "state",
            "entity_id": trigger.get("entity_id"),
            "to_state": trigger.get("to"),
            "note": "state-trigger simulation needs a real state change",
        }

    return {
        "simulatable": False,
        "platform": platform,
        "reason": f"no generic re-fire path for platform '{platform}'",
    }


def executed_triggers(trace: dict[str, Any]) -> list[dict[str, Any]]:
    """Return the runtime trigger variables from the trace's trigger steps."""
    steps = trace.get("trace", {})
    out: list[dict[str, Any]] = []
    for path in sorted(steps):
        if not path.startswith("trigger/"):
            continue
        for step in steps[path]:
            trigger_var = step.get("changed_variables", {}).get("trigger")
            if trigger_var:
                out.append(trigger_var)
    return out


def condition_results(trace: dict[str, Any]) -> list[dict[str, Any]]:
    """Return per-condition evaluation results from the trace's condition steps.

    Each item is ``{path, result, error}`` where ``result`` is the boolean
    outcome (or ``None``) of that condition. Nested conditions (AND/OR, and
    state/numeric_state entity groups) appear as their own nested paths, e.g.
    ``condition/0`` alongside ``condition/0/conditions/0``.
    """
    steps = trace.get("trace", {})
    out: list[dict[str, Any]] = []
    for path in sorted(steps):
        if not path.startswith("condition/"):
            continue
        for step in steps[path]:
            result = step.get("result", {})
            passed = result.get("result") if isinstance(result, dict) else result
            out.append(
                {
                    "path": path,
                    "result": passed,
                    "error": step.get("error"),
                }
            )
    return out


def entity_id_from_trace(trace: dict[str, Any]) -> str | None:
    """Recover the automation's entity_id from a trigger step's `this`."""
    for steps_list in trace.get("trace", {}).values():
        if not isinstance(steps_list, list):
            continue
        for step in steps_list:
            this = step.get("changed_variables", {}).get("this")
            if this and this.get("entity_id"):
                return this["entity_id"]
    return None
