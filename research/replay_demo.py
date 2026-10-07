"""Live end-to-end demo: replay an automation and verify a new trace appears."""
import asyncio

from ha_client import HAClient, list_traces
from replay import replay_automation


def load_token() -> str:
    with open("/opt/data/.env") as f:
        for line in f:
            if line.startswith("HASS_MINI_PC_TOKEN="):
                return line.strip().split("=", 1)[1]
    raise RuntimeError("token not found")


async def main() -> None:
    client = HAClient("http://192.168.1.186:8123", load_token())
    await client.connect()
    print("connected")

    before = await list_traces(client, domain="automation")
    print("traces before:", [(t["run_id"], t["timestamp"]["start"]) for t in before])

    entity_id = "automation.theme_set_defaulth_theme"
    result = await replay_automation(client, entity_id, skip_condition=True)
    print("replay result:", result)

    await asyncio.sleep(1)
    after = await list_traces(client, domain="automation")
    print("traces after: ", [(t["run_id"], t["timestamp"]["start"]) for t in after])

    before_ids = {t["run_id"] for t in before}
    new = [t for t in after if t["run_id"] not in before_ids]
    print("new trace runs:", len(new))
    for t in new:
        print("  ", t["run_id"], "|", t["trigger"], "|", t.get("error") or "ok")

    await client.close()


asyncio.run(main())
