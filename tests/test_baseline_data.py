import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "eval"))

from core_scoring import FIELDS, overall, score_exact  # noqa: E402
from run_baseline import load_gold  # noqa: E402


def test_gold_has_30_notes_150_fields():
    gold = load_gold()
    assert len(gold) == 30
    assert all(set(FIELDS) <= set(g["expected"]) for g in gold)


def test_scoring_perfect_on_gold():
    gold = load_gold()
    c, t = overall(score_exact((g["expected"], g["expected"]) for g in gold))
    assert (c, t) == (150, 150)
