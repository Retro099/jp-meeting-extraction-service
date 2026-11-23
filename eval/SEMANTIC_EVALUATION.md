# Semantic Evaluation Design: Bridging the Exact-Match Gap

**Repository**: `jp-meeting-extraction-service`  
**Location**: `eval/SEMANTIC_EVALUATION.md`  
**Classification**: AI/ML Evaluation Architecture  
**Target Audience**: Tokyo AI/ML Engineering Leads & Evaluators  

---

## 1. Executive Summary

In automated CRM entity extraction from unstructured Japanese text, standard evaluation pipelines face a well-known dilemma: **exact string matching is deterministic and zero-cost, but severely under-reports real-world extraction accuracy on free-text fields.**

In our frozen baseline (`gold_30.jsonl`, 150 fields):
- **Official Exact-Match Headline**: **59.8%** (3-run mean; single-run reproduction: **60.7%** / 91 of 150 fields correct).
- **Core Entity Exact Match (`相手`, `会社名`, `期限`)**: **94.4%** (84 of 90 fields correct).
- **Free-Text Semantic Fields (`次アクション`, `リスク`)**: **11.7%** (7 of 60 fields correct under exact string equality).

This document details why exact match fails on free-text Japanese business fields, presents concrete forensic evidence from baseline predictions, and specifies our **LLM-as-a-Judge semantic scoring protocol** implemented in `eval/core_scoring.py`.

> **Evaluation Policy Guardrail**:  
> The official benchmark headline remains strictly pinned at **59.8% exact match**. Semantic scoring is provided as an interpretability layer and diagnostic metric; it does not replace or artificially inflate the official headline.

---

## 2. Forensic Analysis: Why Exact Match Breaks Down

### 2.1. Canonical Entities vs. Natural Japanese Phrasing

| Field | 2026-11-06 Exact Match | String Variance Type | Root Cause Analysis |
|---|---|---|---|
| `相手` (Contact) | **30 / 30 (100.0%)** | Low | High honorific regularity (e.g. `佐藤様`, `田中部長`). |
| `会社名` (Company) | **29 / 30 (96.7%)** | Low | Canonical corporate legal suffixes (e.g. `株式会社〜`). 1 mismatch due to abbreviation. |
| `期限` (Deadline) | **25 / 30 (83.3%)** | Medium | Relative dates (`来週金曜`, `月内目処`) usually extracted verbatim. |
| `次アクション` (Action) | **7 / 30 (23.3%)** | Very High | Synthetic gold uses short imperative forms; model extracts complete verb phrases. |
| `リスク` (Risk) | **0 / 30 (0.0%)** | Very High | Gold uses `未検出` when no risk exists; model frequently outputs `特になし` or `なし`. |

### 2.2. Concrete Prediction Discrepancies from `eval/runs/2026-11-06`

#### Case A: Synonymy & Equivalent Business Action (`次アクション`)
- **Note Input**: 「...見積書の修正版を週明け月曜日までにメール送付することになった。」
- **Gold Target**: `見積書を再送する`
- **Model Prediction**: `修正した見積書をメールにて再送`
- **Exact Match Verdict**: **MISS (0.0 points)**
- **Real-World Business Impact**: In a production CRM, the salesperson or account executive receives the exact right follow-up task. Under string equality, it is penalized as an error.

#### Case B: Negative Marker Variation (`リスク`)
- **Note Input**: 「...技術的な懸念点や納期遅延のリスクは特段見当たらず、順調に進捗中。」
- **Gold Target**: `未検出`
- **Model Prediction**: `特になし`
- **Exact Match Verdict**: **MISS (0.0 points)**
- **Real-World Business Impact**: Both indicate zero blockers. String equality treats `特になし` as an invalid string and awards zero credit.

#### Case C: Modifier Specificity
- **Note Input**: 「...先方の予算枠が今年度は厳しく、追加費用の承認が下りない可能性が高い。」
- **Gold Target**: `予算超過の懸念`
- **Model Prediction**: `追加費用の承認が得られないリスク`
- **Exact Match Verdict**: **MISS (0.0 points)**
- **Real-World Business Impact**: The model actually captured the nuance more accurately than the generic gold label, yet scores 0 in strict string comparison.

---

## 3. Dual-Metric Architecture

To balance rigorous non-cheating benchmarks with realistic operational metrics, we maintain a dual-layer evaluation framework:

```
+-----------------------------------------------------------------------------------+
|                        LAYER 1: OFFICIAL CI REGRESSION GATE                       |
|   Strict Exact Match (59.8% Headline / 60.7% Reproduction)                        |
|   - Deterministic, zero-cost, zero variance                                       |
|   - Enforced by eval/eval_gate.py on every commit and PR                          |
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                     LAYER 2: SEMANTIC LLM-AS-A-JUDGE METRIC                       |
|   Field-Level Semantic Rubric (eval/core_scoring.py)                              |
|   - Evaluates '次アクション' and 'リスク' using structured LLM rubric            |
|   - Classifies outputs into 'match' (1.0), 'partial' (0.5), and 'miss' (0.0)      |
|   - Reports true semantic fidelity alongside official exact-match stats           |
+-----------------------------------------------------------------------------------+
```

---

## 4. Semantic Judge Specification (`core_scoring.py`)

The helper module `eval/core_scoring.py` defines the scoring primitives:

### 4.1. Point Allocation
```python
VERDICT_POINTS = {
    "match": 1.0,    # Semantically equivalent intent, action, and entity scope
    "partial": 0.5,  # Core action captured, but minor non-critical condition omitted
    "miss": 0.0,     # Factually inaccurate, opposite sentiment, or hallucinated
}
```

### 4.2. Judge System Prompt Template
When running semantic evaluation, the judge LLM is prompted with strict field boundaries:
```
You are an expert bilingual Japanese business evaluation judge.
Evaluate whether the predicted CRM field extraction matches the gold target extraction.

Input Meeting Context: {note_text}
Target Field: {field_name}
Gold Standard Extraction: {gold_value}
Model Predicted Extraction: {predicted_value}

Guidelines:
- "match": Identical semantic meaning. Variations in politeness (Keigo), verb endings, or trivial phrasing differences (e.g., "未検出" vs "特になし") MUST be scored as "match".
- "partial": Primary task or risk identified, but omits a secondary constraint (e.g., omitted method "メールで").
- "miss": Contradicts gold standard, hallucinated entity, or missed a material action.

Respond ONLY with valid JSON:
{
  "verdict": "match" | "partial" | "miss",
  "reason": "<one sentence explanation in Japanese>"
}
```

### 4.3. Parsing & Aggregation
`core_scoring.parse_verdict` and `core_scoring.summarize_verdicts` safely parse the JSON output, strip Markdown fences, and calculate:
- `semantic_score`: `(match * 1.0 + partial * 0.5) / n`
- `strict_match_rate`: `match / n`

---

## 5. Engineering Guidance for Tokyo Evaluators

1. **Why not just rewrite `gold_30.jsonl`?**  
   Rewriting test sets to match model outputs is benchmark manipulation. Pinned datasets must remain immutable (`eval/frozen/`) with asserted SHA-256 checksums.
2. **Why not use cosine embedding similarity?**  
   Embedding similarity (e.g. OpenAI `text-embedding-3-small`) fails on negation in Japanese business text: `契約締結を急ぐ` and `契約締結を見送る` have cosine similarity > 0.88 despite having completely opposite business meanings. An LLM judge correctly identifies the semantic contradiction.
3. **Execution Guardrail**:  
   Live judge execution requires OpenAI / Qwen inference API calls. It is run only when requested with explicit budget approval, while exact match runs in CI on every push for $0.00.
