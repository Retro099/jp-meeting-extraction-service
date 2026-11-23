# jp-meeting-extraction-service

**Status: In Progress (Step 3: Local API Handler & Test Suite Complete).** [[日本語]](README.ja.md)

A production microservice and evaluation gate for extracting structured CRM fields from Japanese business meeting notes. Built as the deployment companion to the core engine [Retro099/jp-meeting-to-crm-fields](https://github.com/Retro099/jp-meeting-to-crm-fields).

---

## What This Repository Does

The core repository ([jp-meeting-to-crm-fields](https://github.com/Retro099/jp-meeting-to-crm-fields)) establishes the extraction prompt, synthetic evaluation benchmark, and prompt-injection defense mechanisms.

This repository implements the **service and operations layer**:
- **Local API Handler**: Python standard-library HTTP server and AWS Lambda-compatible `handle_extract(event, context)` handler.
- **Input & Output Validation**: Strict schema verification, 4,000 character note limit, and field scalar sanitization across the 5 target fields (`会社名`, `相手`, `次アクション`, `期限`, `リスク`).
- **Authentication**: Optional API key check via `x-api-key` or `Authorization: Bearer <key>` when `EXTRACTION_API_KEY` is configured.
- **Automated Verification**: Fast local test suite (16 tests in <1s) covering health checks, error cases, validation boundaries, and frozen baseline checksums.

---

## Baseline Accuracy & Metrics

Official metrics are established in [`eval/BASELINE.md`](eval/BASELINE.md) and [`eval/baseline.json`](eval/baseline.json):

| Metric | Official Value | Description |
| --- | --- | --- |
| **Exact Match (Single Call)** | **59.8%** | Official headline (3-run mean on 30 synthetic notes / 150 fields, core eval v2) |
| **Exact Match (Agent Path)** | 58.4% | Multi-step agent path (no statistical gain over single-call prompt) |
| **Held-Out Attacks (Defenses OFF → ON)** | 30.0% → 8.3% | Tested on 20 held-out prompt injection attacks (`H001`–`H020`) |
| **Estimated Cost** | ~₹0.022 / note | Qwen 2.5 72B via API (~$0.00026 per extraction) |

> **Note on 59.8% vs. 60.7%**:
> A local single-run reproduction on pinned core `v1.0.0` (`7e24c95`) achieved **60.7% (91/150)**. This single-run variance (+0.9 pts) is recorded in `eval/runs/2026-11-06/summary.json` as a reproduction check, but **59.8%** remains the official 3-run mean headline.
> 
> Strict character-for-character exact match penalizes free-text fields:
> - Literal fields: `相手` 30/30, `会社名` 29/30, `期限` 25/30
> - Free-text fields: `次アクション` 7/30, `リスク` 0/30 (semantic LLM judges in the core repository score these fields at 0.89 and 0.73 respectively).

---

## Quick Start & Installation

### 1. Requirements
- Python 3.11 or higher
- Git

### 2. Setup Virtual Environment
```bash
git clone https://github.com/Retro099/jp-meeting-extraction-service.git
cd jp-meeting-extraction-service
python -m venv .venv

# On Linux/macOS:
source .venv/bin/activate
# On Windows (PowerShell):
.venv\Scripts\Activate.ps1
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
pip install pytest ruff
```

### 4. Run the Test Suite
```bash
# Run all unit tests and baseline invariant checks
pytest -v

# Run lint checks
ruff check .
```

---

## Running the Local Service

Start the local HTTP service (built on Python's standard library):

```bash
python -m jp_extraction_service.handler
# Serving jp-meeting-extraction-service on http://127.0.0.1:8000 (POST /extract, GET /health)
```

### Test Health Endpoint
```bash
curl http://127.0.0.1:8000/health
# {"status": "ok", "version": "0.0.1", "defenses_enabled": true}
```

### Test Extraction (Mock / Dev Mode)
In local development with mocked client or configured `AICREDITS_API_KEY`:
```bash
curl -X POST http://127.0.0.1:8000/extract \
  -H "Content-Type: application/json" \
  -d '{"note": "本日は株式会社さくら商事の佐藤様と打ち合わせ。来週金曜までに御見積書を送付する。特段のリスクはなし。"}'
```

Response:
```json
{
  "ok": true,
  "data": {
    "会社名": "株式会社さくら商事",
    "相手": "佐藤様",
    "次アクション": "御見積書を送付する",
    "期限": "来週金曜",
    "リスク": "未検出"
  },
  "meta": {
    "defenses_enabled": true,
    "latency_s": 0.42,
    "prompt_tokens": 180,
    "completion_tokens": 45
  }
}
```

---

## Architecture & Threat Model Status
- Architecture documentation: [`docs/architecture.md`](docs/architecture.md) *(Work in progress)*
- Threat model & prompt-injection defense analysis: [`docs/threat-model.md`](docs/threat-model.md) *(Work in progress)*

---

## Known Limitations
1. **Synthetic Evaluation Set**: All 30 test meeting notes and 20 held-out attacks are synthetic benchmarks; no customer data is present or stored.
2. **Exact-Match Sensitivity**: Character-level exact match strictly penalizes phrasing variations in `次アクション` and `リスク`.
3. **Core Dependency Pin**: Core engine is pinned to `v1.0.0` (`7e24c955`), whereas official 59.8% baseline derived from core eval v2 protocol.
4. **Cloud Deployment**: AWS Lambda and CI evaluation gate are in active development (Steps 4–5 of `PLAN.md`).

---

## License
MIT License. See [LICENSE](LICENSE).
