from trace_parser import (
    build_trigger_events,
    condition_results,
    entity_id_from_trace,
    executed_triggers,
    parse_trace,
)


def test_parse_trace_structure(trace_sample):
    t = parse_trace(trace_sample)
    assert t.domain == "automation"
    assert t.item_id == "1740010526002"
    assert t.run_id == "61dd6561636f1c37e56f62c782272064"
    assert t.alias == "Theme - Set Defaulth Theme"
    assert t.state == "stopped"
    assert t.script_execution == "error"
    assert t.trigger_description == "Home Assistant starting"
    assert t.error == "Theme waves not found at 'name'"
    assert len(t.triggers) == 1
    assert len(t.conditions) == 0
    assert len(t.actions) == 1
    assert len(t.trigger_executions) == 1
    assert len(t.action_executions) == 1


def test_parse_trace_config(trace_sample):
    t = parse_trace(trace_sample)
    assert t.triggers[0] == {"trigger": "homeassistant", "event": "start"}
    assert t.actions[0] == {
        "action": "frontend.set_theme",
        "data": {"name": "waves"},
    }


def test_build_trigger_events(trace_sample):
    specs = build_trigger_events(trace_sample)
    assert len(specs) == 1
    s = specs[0]
    assert s["simulatable"] is True
    assert s["platform"] == "homeassistant"
    assert s["event"] == "start"
    assert s["fire_event"] == "homeassistant_start"


def test_executed_triggers(trace_sample):
    trigs = executed_triggers(trace_sample)
    assert len(trigs) == 1
    assert trigs[0]["platform"] == "homeassistant"
    assert trigs[0]["event"] == "start"
    assert trigs[0]["id"] == "0"


def test_entity_id_from_trace(trace_sample):
    assert entity_id_from_trace(trace_sample) == (
        "automation.theme_set_defaulth_theme"
    )


def test_build_trigger_events_unknown_platform():
    trace = {
        "config": {
            "triggers": [{"trigger": "time", "at": "06:00:00"}]
        }
    }
    specs = build_trigger_events(trace)
    assert specs == [{
        "simulatable": False,
        "platform": "time",
        "reason": "no generic re-fire path for platform 'time'",
    }]


def test_condition_results():
    trace = {
        "trace": {
            "trigger/0": [{"path": "trigger/0"}],
            "condition/0": [
                {"path": "condition/0", "result": {"result": True}},
                {"path": "condition/0", "result": {"result": True}},
            ],
            "condition/1": [
                {"path": "condition/1", "result": {"result": False},
                 "error": "state did not match"},
            ],
            "action/0": [{"path": "action/0"}],
        }
    }
    results = condition_results(trace)
    assert results == [
        {"path": "condition/0", "result": True, "error": None},
        {"path": "condition/0", "result": True, "error": None},
        {"path": "condition/1", "result": False, "error": "state did not match"},
    ]
