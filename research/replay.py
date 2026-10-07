"""Replay an automation by re-triggering it (side-effecting; opt-in)."""
from __future__ import annotations

from ha_client import HAClient


async def replay_automation(
    client: HAClient,
    entity_id: str,
    skip_condition: bool = True,
) -> dict:
    """Re-run an automation's actions via the `automation.trigger` service.

    `skip_condition=True` (HA default) fires actions directly without
    re-evaluating conditions. Returns the service-call result.
    """
    resp = await client.request(
        "call_service",
        domain="automation",
        service="trigger",
        service_data={"skip_condition": skip_condition},
        target={"entity_id": entity_id},
    )
    if not resp.get("success"):
        raise RuntimeError(f"automation.trigger failed: {resp}")
    return resp.get("result", {})
