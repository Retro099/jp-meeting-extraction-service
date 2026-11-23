"""Test CI Eval Gate invariants."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "eval"))

from eval_gate import (  # noqa: E402
    check_baseline_metadata,
    check_frozen_datasets,
    check_recorded_eval_run,
    run_gate,
)


def test_eval_gate_frozen_datasets():
    ok, msg = check_frozen_datasets()
    assert ok is True, msg


def test_eval_gate_baseline_metadata():
    ok, msg = check_baseline_metadata()
    assert ok is True, msg


def test_eval_gate_recorded_run():
    ok, msg = check_recorded_eval_run()
    assert ok is True, msg


def test_eval_gate_overall():
    assert run_gate() == 0
