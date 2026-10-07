# Home Assistant WebSocket API reference (2026.9.4)

The integration's own commands plus the HA built-in commands it drives.

## Built-in commands the panel uses

| Command | Input | Returns |
|---|---|---|
| `trace/list` | `{domain, item_id?}` | short-dict summaries (`run_id`, `state`, `script_execution`, `timestamp`) |
| `trace/get` | `{domain, item_id, run_id}` | flat extended dict (`trace`, `config`, `context`) |
| `config/entity_registry/list` | `{}` | all entities (filter `entity_id` starts with `automation.`) |
| `automation/config` | `{entity_id}` | `{config: raw_config}` (keys `triggers`/`conditions`/`actions`, plural) |

All trace commands and `automation/config` are `@require_admin`, so the panel is
registered with `require_admin=True`.

## The integration's own commands

| Command | Input | Returns |
|---|---|---|
| `automation_testkit/parse_trace` | `{trace}` | `{trace, trigger_events, executed_triggers, entity_id}` |
| `automation_testkit/config` | `{entity_id}` | `{triggers, conditions, actions}` (synthetic trigger variables) |
| `automation_testkit/simulate` | `{entity_id, trigger, skip_condition?}` | `{triggered, entity_id}` |
| `automation_testkit/dry_run` | `{entity_id, trigger, skip_condition?}` | `{calls, script_execution}` |

## Key facts

- `item_id` is the automation's `unique_id`; the entity registry maps
  `unique_id` → `entity_id`.
- `raw_config` uses PLURAL keys (`triggers`, `conditions`, `actions`); trigger
  configs use `trigger: <platform>` (not `platform:`).
- `simulate` calls the entity's internal `async_trigger(run_variables, context,
  skip_condition)` directly — isolated, full trigger variable injection. The
  public `automation.trigger` service forces `trigger: {"platform": None}`.
- `dry_run` patches `ServiceRegistry.async_call` (class-level, it has `__slots__`)
  and captures calls whose `context.parent_id` matches the dry-run context, so
  concurrent automations are unaffected.
