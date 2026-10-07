"""Verify the shipped integration parser behaves like the golden-tested core.

Loads `custom_components/automation_testkit/parser.py` directly (no HA imports
in that file) so we validate exactly what ships, offline.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

PARSER_PATH = (
    Path(__file__).resolve().parent.parent
    / "custom_components"
    / "automation_testkit"
    / "parser.py"
)


def _load_parser():
    import sys

    spec = importlib.util.spec_from_file_location("atk_parser", PARSER_PATH)
    mod = importlib.util.module_from_spec(spec)
    # Register the module so dataclass string annotations (from
    # `from __future__ import annotations`) resolve `cls.__module__`.
    sys.modules["atk_parser"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_shipped_parser_parse_trace(trace_sample):
    parser = _load_parser()
    t = parser.parse_trace(trace_sample)
    assert t.domain == "automation"
    assert t.item_id == "1740010526002"
    assert t.run_id == "61dd6561636f1c37e56f62c782272064"
    assert t.alias == "Theme - Set Defaulth Theme"
    assert t.state == "stopped"
    assert t.script_execution == "error"
    assert t.trigger_description == "Home Assistant starting"
    assert len(t.triggers) == 1
    assert len(t.actions) == 1


def test_shipped_parser_build_trigger_events(trace_sample):
    parser = _load_parser()
    specs = parser.build_trigger_events(trace_sample)
    assert len(specs) == 1
    assert specs[0]["simulatable"] is True
    assert specs[0]["fire_event"] == "homeassistant_start"


def test_shipped_parser_executed_triggers(trace_sample):
    parser = _load_parser()
    trigs = parser.executed_triggers(trace_sample)
    assert len(trigs) == 1
    assert trigs[0]["event"] == "start"


def test_shipped_parser_entity_id(trace_sample):
    parser = _load_parser()
    assert parser.entity_id_from_trace(trace_sample) == (
        "automation.theme_set_defaulth_theme"
    )
