"""Capture a real automation trace from HA into a golden fixture.

Read-only: lists automation traces via trace/list, then saves one full trace
(trace/get) plus its summary as a JSON fixture for golden tests.
"""
import asyncio
import json
import os

from ha_client import HAClient, get_trace, list_traces


def load_token() -> str:
    with open("/opt/data/.env") as f:
        for line in f:
            if line.startswith("HASS_MINI_PC_TOKEN="):
                return line.strip().split("=", 1)[1]
    raise RuntimeError("HASS_MINI_PC_TOKEN not found in /opt/data/.env")


async def main() -> None:
    client = HAClient("http://192.168.1.186:8123", load_token())
    await client.connect()
    print("connected")

    traces = await list_traces(client, domain="automation")
    print(f"automation traces: {len(traces)}")

    if not traces:
        print("no automation traces in memory; nothing to capture")
        await client.close()
        return

    # pick the most recent finished trace
    t = traces[0]
    item_id = t["item_id"]
    run_id = t["run_id"]
    full = await get_trace(client, "automation", item_id, run_id)

    out = {
        "domain": "automation",
        "item_id": item_id,
        "run_id": run_id,
        "summary": t,
        "trace": full,
    }
    os.makedirs("tests/fixtures", exist_ok=True)
    path = "tests/fixtures/trace_sample.json"
    with open(path, "w") as f:
        json.dump(out, f, indent=2, default=str)
    print(f"saved fixture -> {path}")
    print("trace top-level keys:", list(full.keys()))
    print("--- trace (first 2500 chars) ---")
    print(json.dumps(full, default=str)[:2500])
    await client.close()


if __name__ == "__main__":
    asyncio.run(main())
