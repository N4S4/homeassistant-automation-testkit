# Release Notes

## v1.0.0

First release. A native Home Assistant panel for testing automations end to end.

### Features

- Browse automations and their recorded trace runs.
- Inspect triggers, conditions and actions from a saved trace.
- Replay an automation's actions without the real trigger.
- Simulate a trigger in isolation. The trigger variable is injected into one
  automation only, so no other automation is woken.
- Simulate automations that have never run, using synthetic triggers built from
  the config.
- Edit the trigger variable by hand (raw JSON) before injecting.
- Dry-run the full pipeline with every service call intercepted, showing which
  condition failed and why.

### Verified

- Live-tested against Home Assistant 2026.9.4 on a standalone container install.
