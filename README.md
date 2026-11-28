# jp-meeting-extraction-service

**Status: Step 4 deployed live on AWS Lambda (`ap-south-1`, Python `3.13`, `x86_64`) (merged to `main` in PR #2).** [[日本語]](README.ja.md)

- **Live Demo Endpoint (Function URL):** `https://thcp6fpe4pdphbodm2d4c2kqlm0npixj.lambda-url.ap-south-1.on.aws` (`GET /` and `GET /health` open; `POST /extract` protected by `EXTRACTION_API_KEY` header auth + soft `50/day` per-container cap)

A local HTTP service and AWS Lambda handler for extracting structured CRM fields from Japanese business meeting notes. Built as the operational service layer for the core engine [Retro099/jp-meeting-to-crm-fields](https://github.com/Retro099/jp-meeting-to-crm-fields).

```bash
# Check out the reviewed feature branch:
git checkout feat/step3-api-handler
```

---

## What This Repository Does

The core repository ([jp-meeting-to-crm-fields](https://github.com/Retro099/jp-meeting-to-crm-fields)) establishes the extraction prompt, synthetic evaluation benchmark, and prompt-injection defense mechanisms.

This repository implements the **service and operations layer**:
- **Local API Handler**: Python standard-library HTTP server and AWS Lambda-compatible `handle_extract(event, context)` handler.
- **Input & Output Validation**: Strict schema verification, 4,000 character note limit, and field scalar sanitization across the 5 target fields (`会社名`, `相手`, `次アクション`, `期限`, `リスク`).
- **Authentication**: Ingress API key verification via `x-api-key` or `Authorization: Bearer <key>` using constant-time comparison (`hmac.compare_digest`) when `EXTRACTION_API_KEY` is configured.
- **Automated Verification**: Fast local test suite covering health checks, error cases, validation boundaries, cost calculation, and frozen baseline checksums.
- **CI Evaluation Gate**: Zero-cost automated GitHub Actions gate (`eval/eval_gate.py`) asserting frozen test set checksums, baseline metadata, and reproducible scoring.

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
> - Free-text fields: `次アクション` 7/30, `リスク` 0/30 (see [`eval/SEMANTIC_EVALUATION.md`](eval/SEMANTIC_EVALUATION.md) for field-level semantic scoring analysis).

---

## Quick Start & Installation

### 1. Requirements
- Python 3.11 or higher
- Git

### 2. Setup Virtual Environment
```bash
git clone https://github.com/Retro099/jp-meeting-extraction-service.git
cd jp-meeting-extraction-service
git checkout feat/step3-api-handler
python -m venv .venv

# On Linux/macOS:
source .venv/bin/activate
# On Windows (PowerShell):
.venv\Scripts\Activate.ps1
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
pip install -e .
pip install pytest ruff
```

*Note*: Alternatively, without editable installation (`pip install -e .`), you can set `PYTHONPATH`:
```bash
# Linux/macOS:
export PYTHONPATH=src
# Windows (PowerShell):
$env:PYTHONPATH = "src"
```

### 4. Run the Test Suite
```bash
# Run all unit tests and baseline invariant checks
pytest -v

# Run lint checks
ruff check .

# Run CI evaluation gate
python eval/eval_gate.py
```

---

## Running the Local Service

Start the local HTTP service (built on Python's standard library):

```bash
python -m jp_extraction_service.handler
# Serving jp-meeting-extraction-service on http://127.0.0.1:8000 (POST /extract, GET /health)
```

### 1. Test Health Endpoint
```bash
curl http://127.0.0.1:8000/health
# {"status": "ok", "version": "0.0.1", "defenses_enabled": true}
```

### 2. Test Extraction Endpoint
The extraction endpoint requires an upstream LLM API key (`AICREDITS_API_KEY`) to perform live extraction against Qwen 2.5 72B. Real API calls consume token budget (~₹0.022 / note).

**Without `AICREDITS_API_KEY` configured**, the server safely rejects the request:
```bash
curl -X POST http://127.0.0.1:8000/extract \
  -H "Content-Type: application/json" \
  -d '{"note": "本日は株式会社さくら商事の佐藤様と打ち合わせ。来週金曜までに御見積書を送付する。特段のリスクはなし。"}'
```
Server response:
```json
{"ok": false, "error": "AICREDITS_API_KEY is not configured"}
```

**With `AICREDITS_API_KEY` configured** (example output):
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
    "completion_tokens": 45,
    "estimated_cost_usd": 0.000126,
    "estimated_cost_inr": 0.0107
  }
}
```

---

## Architecture & Threat Model Documentation
- Architecture Design: [`docs/architecture.md`](docs/architecture.md) (Component flow, trust boundaries, Lambda & ECS profiles)
- Threat Model: [`docs/threat-model.md`](docs/threat-model.md) (STRIDE threat matrix, prompt injection, canary defense, token exhaustion)
- Dataset Card: [`eval/DATASET_CARD.md`](eval/DATASET_CARD.md) (Synthetic provenance statement, zero personal data, MIT license)
- Semantic Evaluation: [`eval/SEMANTIC_EVALUATION.md`](eval/SEMANTIC_EVALUATION.md) (LLM-as-a-judge rubric for free-text fields)

---

## Known Limitations
1. **Synthetic Evaluation Set**: All 30 test meeting notes and 20 held-out attacks are synthetic benchmarks; no customer data is present or stored.
2. **Exact-Match Sensitivity**: Character-level exact match strictly penalizes phrasing variations in `次アクション` and `リスク`.
3. **Core Dependency Pin**: Core engine is pinned to `v1.0.0` (`7e24c955`), whereas official 59.8% baseline derived from core eval v2 protocol.
4. **Cloud Deployment & Guardrails**: Live demo deployed to AWS Lambda (`ap-south-1` Mumbai, Python `3.13`, `x86_64`, `512 MB`, `60s` timeout, `7`-day CloudWatch retention) via Function URL. Unauthenticated `POST /extract` is blocked (`401`); the `50/day` daily counter is a soft per-container guard that resets on cold starts/scaling. Zero-cost CI integrity gate is active in GitHub Actions (Python `3.11` & `3.13`).

---

## License
MIT License. See [LICENSE](LICENSE).
