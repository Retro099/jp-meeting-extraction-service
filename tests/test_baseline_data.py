import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "eval"))

from core_scoring import FIELDS, overall, score_exact  # noqa: E402
from run_baseline import load_gold  # noqa: E402

GOLD_SHA = "5a1701e5a0fb26a53e58ae5dc390e4cd8061686f976fc28491403e0150c7ea17"
ATTACK_SHA = "d21b4aa2cec0c5ecb7f6c3c94f87f78a8aa2ba6b667f45e7876b37c51bd75b95"
ROOT = Path(__file__).resolve().parents[1]


def test_gold_has_30_notes_150_fields():
    gold = load_gold()
    assert len(gold) == 30
    assert all(set(FIELDS) <= set(g["expected"]) for g in gold)


def test_scoring_perfect_on_gold():
    gold = load_gold()
    c, t = overall(score_exact((g["expected"], g["expected"]) for g in gold))
    assert (c, t) == (150, 150)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_frozen_gold_matches_checksum_and_working_copy():
    frozen = ROOT / "eval" / "frozen" / "gold_30.jsonl"
    working = ROOT / "eval" / "data" / "gold_30.jsonl"
    assert _sha256(frozen) == GOLD_SHA
    assert frozen.read_bytes() == working.read_bytes()


def test_frozen_heldout_attacks_match_checksum():
    frozen = ROOT / "eval" / "frozen" / "attacks_v2_heldout.jsonl"
    assert _sha256(frozen) == ATTACK_SHA
    rows = [json.loads(line) for line in frozen.read_text().splitlines() if line.strip()]
    assert len(rows) == 20
    assert [row["id"] for row in rows] == [f"H{i:03d}" for i in range(1, 21)]


def test_official_baseline_headline_unchanged():
    data = json.loads((ROOT / "eval" / "baseline.json").read_text())
    assert data["official_headline"]["display"] == "59.8%"
    assert data["official_headline"]["is_official"] is True
    assert data["step1_reproduction"]["display"] == "91/150 = 60.7%"
    assert data["step1_reproduction"]["is_official_baseline"] is False
    assert data["agent"]["display"] == "58.4%"
    assert data["held_out_attacks"]["single_call"]["display"] == "30% → 8.3%"
    assert data["held_out_attacks"]["agent"]["display"] == "30% → 10%"
