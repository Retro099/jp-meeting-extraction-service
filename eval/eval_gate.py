"""CI Evaluation Gate: validates frozen datasets, baseline invariants, and scoring reproducibility.

Runs in zero-cost mode (no live LLM API keys needed) during continuous integration to ensure
that datasets are not tampered with, official baselines are not corrupted, and scoring algorithms
do not regress.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

sys.path.insert(0, str(HERE))
from core_scoring import overall, score_exact  # noqa: E402

GOLD_SHA = "5a1701e5a0fb26a53e58ae5dc390e4cd8061686f976fc28491403e0150c7ea17"
ATTACK_SHA = "d21b4aa2cec0c5ecb7f6c3c94f87f78a8aa2ba6b667f45e7876b37c51bd75b95"
MINIMUM_ACCURACY_THRESHOLD = 0.598  # Anchored to the official headline baseline (59.8%)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_frozen_datasets() -> tuple[bool, str]:
    gold_path = HERE / "frozen" / "gold_30.jsonl"
    attack_path = HERE / "frozen" / "attacks_v2_heldout.jsonl"

    if not gold_path.exists():
        return False, f"Missing frozen gold dataset: {gold_path}"
    if not attack_path.exists():
        return False, f"Missing frozen attacks dataset: {attack_path}"

    gold_hash = _sha256(gold_path)
    if gold_hash != GOLD_SHA:
        return False, f"Gold SHA mismatch! Expected {GOLD_SHA}, got {gold_hash}"

    attack_hash = _sha256(attack_path)
    if attack_hash != ATTACK_SHA:
        return False, f"Attacks SHA mismatch! Expected {ATTACK_SHA}, got {attack_hash}"

    gold_lines = [json.loads(line) for line in gold_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(gold_lines) != 30:
        return False, f"Gold dataset must contain exactly 30 notes, found {len(gold_lines)}"

    attack_lines = [json.loads(line) for line in attack_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(attack_lines) != 20:
        return False, f"Held-out attacks must contain exactly 20 cases, found {len(attack_lines)}"

    return True, "Frozen datasets validated (exact SHA-256 match, 30 gold notes, 20 attacks)."


def check_baseline_metadata() -> tuple[bool, str]:
    baseline_path = HERE / "baseline.json"
    if not baseline_path.exists():
        return False, f"Missing baseline metadata: {baseline_path}"

    try:
        data = json.loads(baseline_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return False, f"Failed to parse baseline.json: {exc}"

    official = data.get("official_headline", {})
    if official.get("exact_match_single_call") != 0.598 or official.get("display") != "59.8%":
        return False, f"Official headline baseline modified! Expected 59.8%, found {official.get('display')}"
    if not official.get("is_official"):
        return False, "official_headline.is_official must be True"

    step1 = data.get("step1_reproduction", {})
    if step1.get("display") != "91/150 = 60.7%":
        return False, f"Step 1 reproduction display modified! Expected '91/150 = 60.7%', found {step1.get('display')}"
    if step1.get("is_official_baseline") is not False:
        return False, "step1_reproduction.is_official_baseline must remain False (not replacing official 59.8%)"

    return True, "Baseline metadata verified (59.8% official headline preserved, 60.7% reproduction recorded)."


def check_recorded_eval_run() -> tuple[bool, str]:
    preds_path = HERE / "runs" / "2026-11-06" / "predictions.jsonl"
    if not preds_path.exists():
        return False, f"Missing recorded evaluation predictions: {preds_path}"

    rows = []
    with open(preds_path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))

    if len(rows) != 30:
        return False, f"Predictions must contain 30 records, found {len(rows)}"

    scores = score_exact((r["expected"], r["predicted"]) for r in rows)
    c, t = overall(scores)
    rate = c / t if t else 0.0

    if c != 91 or t != 150:
        return False, f"Scoring regression on 2026-11-06 run! Expected 91/150, got {c}/{t}"

    if rate < MINIMUM_ACCURACY_THRESHOLD:
        return False, f"Accuracy {rate:.2%} below CI threshold of {MINIMUM_ACCURACY_THRESHOLD:.2%}"

    # Verify per-field exact match counts
    expected_field_counts = {
        "相手": 30,
        "会社名": 29,
        "期限": 25,
        "次アクション": 7,
        "リスク": 0,
    }
    for field, expected_correct in expected_field_counts.items():
        actual_correct = scores[field]["correct"]
        if actual_correct != expected_correct:
            return False, f"Per-field regression on '{field}': expected {expected_correct}/30, got {actual_correct}/30"

    return True, f"Recorded run verified: {c}/{t} ({rate:.1%}) exact match across 5 fields."


def run_gate() -> int:
    print("=" * 60)
    print("JP Meeting Extraction Service - CI Evaluation Gate")
    print("=" * 60)

    checks = [
        ("1. Frozen Datasets Invariants", check_frozen_datasets),
        ("2. Baseline Metadata Invariants", check_baseline_metadata),
        ("3. Recorded Predictions Scoring Gate", check_recorded_eval_run),
    ]

    all_passed = True
    for title, check_fn in checks:
        ok, msg = check_fn()
        status_str = "PASS" if ok else "FAIL"
        print(f"[{status_str}] {title}: {msg}")
        if not ok:
            all_passed = False

    print("=" * 60)
    if all_passed:
        print("CI EVAL GATE: ALL INVARIANTS PASSED (Zero regressions detected)")
        return 0
    else:
        print("CI EVAL GATE: REGRESSION DETECTED (Build blocked)")
        return 1


if __name__ == "__main__":
    sys.exit(run_gate())
