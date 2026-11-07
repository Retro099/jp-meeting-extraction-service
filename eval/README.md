# Evaluation

Synthetic data only. `data/gold_30.jsonl` is copied unchanged from the core repo at v1.0.0 (30 notes x 5 fields = 150 fields).
`core_scoring.py` is copied unchanged from core `eval/scoring.py` at v1.0.0. The extractor is used from the pinned core package (`requirements.txt`).

## Step 1 baseline check (2026-11-06)
`DEFENSES_ENABLED=1 python eval/run_baseline.py eval/runs/2026-11-06`: single-call path, exact match only, one run, no judge, no attacks.

| Result | Value |
|---|---|
| Exact match (this run) | 91/150 = 60.7% |
| Reference baseline | 59.8% (mean of 3 runs, core eval v2, 2026-10-27) |
| Gap | +0.9 points (one run can differ from a 3-run mean) |
| Failed calls | 0 of 30 |

Per field: 会社名 29/30, 相手 30/30, 次アクション 7/30, 期限 25/30, リスク 0/30 (free-text fields score low on strict exact match).
The frozen copies and checksums are in `frozen/` (see `frozen/MANIFEST.md`). Official headlines stay in `BASELINE.md` / `baseline.json`; 60.7% is not a new official baseline.
