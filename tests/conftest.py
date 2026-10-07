import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

FIXTURE = Path(__file__).parent / "fixtures" / "trace_sample.json"


@pytest.fixture(scope="session")
def trace_sample() -> dict:
    with open(FIXTURE) as f:
        data = json.load(f)
    # fixture wraps the flat trace/get payload under "trace"
    return data["trace"]
