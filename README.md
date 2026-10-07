# Automation Test Kit

A native Home Assistant integration for testing automations without waiting for
the real trigger. Inspect past runs, replay actions, simulate a trigger in
isolation, and dry-run the whole pipeline without touching a single device.

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration)
[![License: GPL-3.0](https://img.shields.io/badge/license-GPL--3.0-blue.svg?style=for-the-badge)](LICENSE)

<p align="center">
  <a href="https://my.home-assistant.io/redirect/hacs_repository/?owner=N4S4&repository=homeassistant-automation-testkit&category=integration">
    <img src="https://my.home-assistant.io/badges/hacs_repository.svg" alt="Open your Home Assistant instance and open a repository inside the Home Assistant Community Store." />
  </a>
</p>

---

## Features

- **Browse** your automations and their recorded trace runs.
- **Inspect** triggers, conditions and actions from a saved trace.
- **Replay** an automation's actions without waiting for the real trigger.
- **Simulate** a trigger in isolation. It injects a reconstructed trigger
  variable so the full pipeline runs (trigger → conditions → actions), without
  waking any other automation.
- **Simulate never-run automations**. Synthetic triggers are built from the
  config, so even an automation with no recorded trace can be tested.
- **Edit** the trigger variable by hand before injecting it. Change a time, a
  state, event data.
- **Dry-run** the pipeline. Conditions are evaluated, templates rendered and
  branches taken, but every service call is intercepted, so no device is
  touched. You see exactly what *would* change, including **which condition
  failed** and why.

A native sidebar panel (no iframe, no external server, no build step), driven
by Home Assistant's own WebSocket API.

## Installation

### HACS (Recommended)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=N4S4&repository=homeassistant-automation-testkit&category=integration)

1. Click the badge above, or go to HACS → Integrations → ⋮ → Custom repositories
2. Add `https://github.com/N4S4/homeassistant-automation-testkit` as an **Integration** type
3. Search for "Automation Test Kit" and install
4. Restart Home Assistant
5. Go to **Settings → Devices & Services → Add Integration** → search "Automation Test Kit"

### Manual

```bash
cd /path/to/homeassistant/config/custom_components
git clone https://github.com/N4S4/homeassistant-automation-testkit.git automation_testkit
```

Then restart HA and add the integration via the UI.

## Usage

Open the **Automation Test Kit** panel from the sidebar. Pick an automation to
see its triggers, conditions and actions, plus every recorded trace run.

Each trigger exposes three actions:

| Action | What it does |
|--------|--------------|
| **Simulate** | Runs the full pipeline (conditions + actions) with a reconstructed trigger, in isolation. |
| **Dry run** | Same pipeline, but service calls are intercepted. Nothing touches a device. Shows which conditions passed or failed. |
| **Edit** | Edit the trigger variable as raw JSON, then simulate or dry-run with your value. |

Simulation is **isolated**. It calls the target automation's internal trigger
directly, so no other automation is woken and nothing is fired on the event bus.

## How it works

The panel drives Home Assistant's own WebSocket API:

- `trace/list`, `trace/get` → read trace runs.
- `automation/config` → read an automation's triggers/conditions/actions.
- `automation_testkit/parse_trace` → structured view of a raw trace.
- `automation_testkit/config` → synthetic trigger variables built from config.
- `automation_testkit/simulate` → inject a trigger variable into one automation.
- `automation_testkit/dry_run` → same, but service calls are intercepted.

## Requirements

- Home Assistant 2026.9.0+
- No extra Python dependencies

## License

GPL-3.0. See [LICENSE](LICENSE).

---

© 2026 Renato Visaggio. Licensed under GPL-3.0.
