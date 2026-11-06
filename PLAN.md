# Plan

One project, two links: core (evaluation and defences, https://github.com/Retro099/jp-meeting-to-crm-fields) and service (this repo).

## Steps (about 10-14 days, estimate)
1. Repo skeleton, reuse core, reproduce 59.8% exact match locally — **Done 2026-11-06**: core pinned to v1.0.0 (7e24c95), one single-call run gave 91/150 = 60.7% (see eval/README.md)
2. Freeze test set (30 notes, 20 held-out attacks), add baseline file
3. API handler running locally with tests — **Checkpoint 1**
4. Deploy on AWS Lambda (or ECS Express Mode): secrets in AWS secret store, API key auth, throttle, daily cap, budget alert
5. GitHub Actions CI: lint, tests, eval gate (fails if exact match drops below baseline or held-out attack success rises above baseline), AWS via OIDC, no long-lived keys — **Checkpoint 2**
6. Logging of latency, tokens, cost per call
7. Threat model, failure modes, architecture diagram, README EN/JA, screenshots, short walkthrough video as fallback — **Checkpoint 3**
8. Review buffer

## Verified base numbers (from core repo v1.0.0, synthetic data only)
- Exact match, single call: 59.8% (30 synthetic notes, 150 fields, mean of 3 runs)
- Exact match, agent path: 58.4% (no gain)
- 20 held-out attacks, defences off -> on: 30% -> 8.3% (single call), 30% -> 10% (agent)
- Estimated cost: about Rs 0.022 per note

## Targets (targets, none measured yet)
Public URL with API key auth, throttle, daily cap, budget alert; CI eval gate; per-call latency, tokens and cost logged.

## Known limitations
Every shortcut listed here needs Prithivi's OK.

- Core is pinned to v1.0.0 (7e24c95); the 59.8% baseline came from eval v2 (2026-10-27) on later core code. Pinning a newer commit needs Prithivi's OK. (open)
- Step 1 is one run, not the 3-run mean. (open)
