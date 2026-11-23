# Architecture & System Design

**Repository**: `jp-meeting-extraction-service`  
**Core Dependency**: `jp-meeting-to-crm-fields` (`v1.0.0` / commit `7e24c955`)  
**Target Environment**: AWS Lambda / Containerized Microservice (ECS Express Mode / Docker) / Local Runner

---

## 1. System Overview

This service provides an automated, secure pipeline for extracting 5 standardized CRM fields from unstructured Japanese business meeting notes:
1. `会社名` (Company Name)
2. `相手` (Counterparty / Contact Person)
3. `次アクション` (Next Action)
4. `期限` (Deadline)
5. `リスク` (Risk / Red Flags)

```
+-----------------------------------------------------------------------------------+
|                                 CLIENT REQUEST                                    |
|   POST /extract  {"note": "..."}  [Headers: x-api-key / Authorization]             |
+-----------------------------------------+-----------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                         INGRESS & AUTHENTICATION LAYER                            |
|  - Method Check (GET /health, POST /extract)                                      |
|  - API Key Verification (_check_auth via EXTRACTION_API_KEY)                      |
|  - Rate Throttling & Daily Cap Boundary                                           |
+-----------------------------------------+-----------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                     INPUT VALIDATION & SANITIZATION LAYER                         |
|  - JSON Decoding & Structural Validation                                          |
|  - Character Ceiling Enforcement (MAX_NOTE_CHARS = 4,000)                         |
|  - Empty / Whitespace Note Rejection (HTTP 400)                                   |
+-----------------------------------------+-----------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|               CORE EXTRACTION & PROMPT-INJECTION DEFENSE ENGINE                   |
|  (Imported from pinned crm_extractor v1.0.0)                                      |
|  - Layer 1: Feature Flag (DEFENSES_ENABLED)                                       |
|  - Layer 2: Delimiter Encapsulation (<<NOTE_<boundary>>>)                          |
|  - Layer 3: System Prompt Canary Hardening                                        |
|  - Upstream LLM: Qwen 2.5 72B Instruct via OpenAI-compatible endpoint             |
+-----------------------------------------+-----------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                     OUTPUT NORMALIZATION & OBSERVABILITY                          |
|  - Field Allowlisting (Strict scalar string filter across 5 CRM fields)           |
|  - Default Fallback Substitution ("未検出" for missing or untrusted fields)      |
|  - Observability Metadata (Latency, Prompt Tokens, Completion Tokens, Cost)       |
+-----------------------------------------+-----------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                                JSON HTTP RESPONSE                                 |
|  HTTP 200 {"ok": true, "data": {...}, "meta": {...}}                              |
+-----------------------------------------------------------------------------------+
```

---

## 2. Core vs. Service Architectural Split

To maintain separation of concerns, the project is strictly partitioned across two repositories:

1. **`jp-meeting-to-crm-fields` (Core Evaluation & Prompt Package)**:
   - Owns the gold standard synthetic datasets (`gold_30.jsonl`, `attacks_v2_heldout.jsonl`).
   - Owns the prompt templates and defense algorithms (`crm_extractor.security`).
   - Owns the baseline evaluation scripts and exact-match / semantic scoring logic.

2. **`jp-meeting-extraction-service` (Production Service & CI Gate)**:
   - Pins the core library as an external dependency at `v1.0.0` (`7e24c955`).
   - Exposes standard HTTP and AWS Lambda entry points (`handle_extract`).
   - Enforces ingress security, payload caps, and API authentication.
   - Implements automated CI regression gates to prevent model or prompt regressions from silently reaching production.

---

## 3. Trust Boundaries & Network Topology

- **Trust Boundary 1 (Client to Ingress)**:
  - Untrusted client input enters via public internet.
  - Mitigations: SSL/TLS termination, API key verification, payload size limits (4,000 chars), strict HTTP method enforcement (only GET `/health` and POST `/extract` permitted).
- **Trust Boundary 2 (Service to Upstream LLM Provider)**:
  - Communicates over HTTPS to OpenAI-compatible LLM inference endpoints (Qwen 2.5 72B).
  - Credentials (`AICREDITS_API_KEY`) injected at runtime via environment variables or AWS Secrets Manager / Parameter Store; never written to disk or logs.
- **Trust Boundary 3 (LLM Output to Application State)**:
  - Model completions are treated as untrusted text.
  - Mitigations: Output JSON is strictly validated against allowed CRM keys. Any non-dict structure or unexpected nested array is sanitized to scalar strings or replaced with `"未検出"`.

---

## 4. Deployment Profiles

### A. Local / Containerized Service
Built with Python's standard library `http.server`, allowing deployment into lightweight Docker containers or ECS Express Mode with zero third-party framework overhead:
```bash
python -m jp_extraction_service.handler
```

### B. Serverless (AWS Lambda)
The entry point `handle_extract(event, context)` directly accepts AWS API Gateway proxy events (v1 and v2 payload formats) without requiring adapter layers like Mangum or serverless frameworks.

---

## 5. Observability & Logging Strategy
Every extraction response returns operational metadata:
- `latency_s`: Round-trip upstream inference time in seconds.
- `prompt_tokens`: Input token count for prompt and notes.
- `completion_tokens`: Output token count.
- `defenses_enabled`: Boolean flag indicating active security posture.
- Estimated per-call cost logged internally based on Qwen 2.5 72B token rates (~$0.00026 / note).
