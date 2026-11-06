"""Step 1: single-call exact-match baseline over the 30 synthetic notes (150 fields).

Reuses the core extractor (pinned v1.0.0) and core scoring. No LLM judge, no attacks, one run.
Key is read from the environment only (AICREDITS_API_KEY); never printed or saved.
"""

import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from core_scoring import FIELDS, overall, score_exact  # noqa: E402

GOLD = HERE / "data" / "gold_30.jsonl"


def load_gold(path=GOLD):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def main(out_dir):
    from crm_extractor.extractor import extract_crm_data
    from crm_extractor.prompts import API_BASE_URL, MODEL_NAME, TEMPERATURE
    from openai import OpenAI

    client = OpenAI(api_key=os.environ["AICREDITS_API_KEY"], base_url=API_BASE_URL, timeout=90, max_retries=1)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    with open(out / "predictions.jsonl", "w", encoding="utf-8") as f:
        for i, rec in enumerate(load_gold(), 1):
            r = extract_crm_data(client, rec["input"])
            row = {"note_id": i, "expected": rec["expected"], "predicted": r.get("data", {}) if r["success"] else {},
                   "success": r["success"], "latency_s": r.get("latency"),
                   "prompt_tokens": r.get("prompt_tokens"), "completion_tokens": r.get("completion_tokens")}
            rows.append(row)
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            f.flush()
            print(f"note {i}: success={r['success']}", flush=True)
            time.sleep(1)
    scores = score_exact((r["expected"], r["predicted"]) for r in rows)
    c, t = overall(scores)
    summary = {"model": MODEL_NAME, "temperature": TEMPERATURE,
               "defenses_enabled": os.getenv("DEFENSES_ENABLED", ""), "notes": len(rows),
               "failed_calls": sum(not r["success"] for r in rows), "correct": c, "total": t,
               "exact_match": round(c / t, 4), "per_field": {k: scores[k] for k in FIELDS},
               "prompt_tokens": sum(r["prompt_tokens"] or 0 for r in rows),
               "completion_tokens": sum(r["completion_tokens"] or 0 for r in rows)}
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"exact match {c}/{t} = {c / t:.1%}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else str(HERE / "runs" / "step1"))
