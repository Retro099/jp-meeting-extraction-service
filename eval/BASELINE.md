# Baseline

Official headlines stay as measured on core eval v2 (2026-10-27). The step 1 one-run check is recorded below and is **not** a new official baseline. Synthetic data only. See `frozen/MANIFEST.md` for the pinned files.

## Official headline (unchanged)

- Exact match, single call: **59.8%** (150 fields = 30 notes × 5, defences on, mean of 3 runs)
- Agent path: **58.4%** (no gain)
- 20 held-out attacks, defences off → on: **30% → 8.3%** (single call) and **30% → 10%** (agent)
- Estimated cost: about Rs 0.022 per note

Do not headline 45% → 6.7% (circular, older self-written 40-attack set). Do not headline 60.0% (that was a single backup-model run).

## Step 1 reproduction (2026-11-06) — not official

One single-call run, exact match only, defences on, pinned core v1.0.0: **91/150 = 60.7%** (0.9 points above 59.8%). A single run can differ from a 3-run mean.

Per field, out of 30: 相手 30, 会社名 29, 期限 25, 次アクション 7, リスク 0.

Details: `runs/2026-11-06/summary.json`.
