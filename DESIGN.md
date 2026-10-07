# Automation Test Kit

Test Home Assistant automations without waiting for real events. Replay a past
trigger, simulate any trigger with synthetic data, and dry-run to see what
*would* happen before it touches a real device.

## The problem (grounded)

- Feature request "Simulate Trigger", open since Oct 2024:
  https://community.home-assistant.io/t/simulated-automation-triggering/753809
- Built-in limits:
  - "Run actions" skips triggers AND conditions, so you cannot test the full
    trigger -> condition -> action pipeline.
  - "Automation: Trigger" fires for real, but you must hand-construct the
    trigger variables yourself (no way to inject a realistic payload).
  - No way to replay a saved trace after you edit the automation, to verify the
    fix without waiting for the event to happen again.
- Consequence, verbatim from users: "I'm left waiting days for a trigger to
  happen again to test my automation." Azure Logic Apps has replay; HA does not.

## What it does

1. **Replay** — re-fire an automation with the exact trigger data captured in a
   saved trace.
2. **Simulate** — fire an automation with synthetic trigger data (e.g. "motion
   at 22:00", "temperature crossed 21°C").
3. **Dry-run** — evaluate triggers + conditions + actions and report what WOULD
   change, without executing actions on real devices.

## How it works

- Reads automation traces. Source of truth: the HA WebSocket `trace/get` payload
  (also persisted to `.storage/trace.saved_traces`; restored in-memory on start,
  capped per-automation by `stored_traces`).
- Core is a pure, I/O-free function: `trace_payload -> replayed trigger payload`.
  This is golden-testable offline against a recorded trace (no live HA needed).
- Re-fires via the `automation/trigger` WebSocket command, injecting the
  reconstructed trigger variables.
- Dry-run: intercept the action runner (`hass.services.async_call` seam) and
  report instead of execute.

## Phases

1. **PoC** — replay a saved trace: pure function + a thin aiohttp WebSocket
   client. Golden tests against a recorded `trace/get` payload.
2. **Simulate** — inject arbitrary trigger data (state / event / time / numeric).
3. **Dry-run + UI** — report-only mode, then a dev panel / Lovelace panel.

## Scope guard

Pure Python, no hardware, small surface. Ships as a HACS custom integration or
a dev panel. Built to be low-maintenance: the core function is ~1 file, the
rest is thin I/O around it.

## Key technical risk

Dry-run action interception. HA runs actions through its action runner, not a
single clean mockable seam. The replay/simulate path is safe and simple; the
dry-run path needs a report-only execution mode, which is the hardest part and
is deliberately deferred to phase 3.

## Provenance

Predecessor research confirmed the adjacent "automation suggestions" space is
already crowded (Danm72, ha-insights, ha-rhythm, Tara), but none of them tests
automations. This fills the testing gap instead.
