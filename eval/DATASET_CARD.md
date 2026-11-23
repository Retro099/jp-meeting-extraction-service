# Dataset Card: Japanese Business Meeting Notes Evaluation Suite

**Repository**: `jp-meeting-extraction-service`  
**Location**: `eval/frozen/` (`gold_30.jsonl`, `attacks_v2_heldout.jsonl`)  
**Format**: JSON Lines (UTF-8, LF line endings)  
**License**: MIT License  
**Maintainer**: Prithivi Raj Mohanta (Retro099) & Coordination Team

---

## 1. Summary & Purpose

This dataset suite provides standardized, frozen benchmarks for evaluating the extraction of structured CRM entities and testing prompt-injection resilience in Japanese business contexts.

It contains:
1. **`gold_30.jsonl`**: 30 synthetic Japanese business meeting notes with ground-truth target extractions across 5 core CRM fields (150 total evaluation fields).
2. **`attacks_v2_heldout.jsonl`**: 20 held-out synthetic adversarial injection prompts designed to test indirect prompt-injection vulnerability, system prompt leak resistance, and delimiter escaping.

---

## 2. Dataset Provenance & Synthetic Generation

### 2.1. 100% Synthetic Nature & PII Guarantee
- **No Private Data**: To protect personal privacy and proprietary business secrets, **zero real customer meeting transcripts or proprietary corporate notes were used**.
- **Synthetic Entity Synthesis**: All counterparty names (e.g. 佐藤, 田中, 高橋, 鈴木), corporate entities (e.g. 株式会社さくら商事, テックイノベーション株式会社, クラウドエッジ株式会社), email addresses, and phone numbers are completely fictitious.
- **Privacy & Data Nature**: All 30 + 20 notes are 100% synthetic and were written specifically for this project. They contain no real person's data. No compliance certification is claimed.

### 2.2. Generation Methodology & Realism
The synthetic scenarios were modeled after typical Japanese B2B corporate communications, including:
- Enterprise SaaS sales pitches and contract renegotiations.
- Technical implementation reviews and milestone delivery delays.
- Multi-stakeholder vendor discussions with complex honorific hierarchies (*sonkeigo*, *kenjougo*, *teineigo*).
- Implicit versus explicit deadlines (e.g. 「来週水曜中」「月内目処」「特段の指定なし」).
- Vague or conditional next actions and implicit operational risks.

---

## 3. Schema & Field Definitions

Each record in `gold_30.jsonl` contains:
```json
{
  "id": 1,
  "input": "打ち合わせノート本文...",
  "expected": {
    "会社名": "株式会社サンプル",
    "相手": "田中部長",
    "次アクション": "修正見積書を再送する",
    "期限": "来週金曜日",
    "リスク": "未検出"
  }
}
```

### 5 CRM Fields:
1. `会社名` (Company Name): Target client or partner corporate entity.
2. `相手` (Counterparty / Contact Person): Primary client contact or attendee.
3. `次アクション` (Next Action): Primary committed follow-up task or deliverable.
4. `期限` (Deadline): Agreed due date, calendar deadline, or relative timeframe.
5. `リスク` (Risk): Stated business risks, pricing objections, technical blockers, or `"未検出"` if none present.

---

## 4. Attack Evaluation Suite (`attacks_v2_heldout.jsonl`)

The 20 held-out attack records (`H001` through `H020`) evaluate whether the model's defenses successfully block indirect prompt injection.

### Attack Categories:
- **Instruction Overrides**: Prompts attempting to force the model to output arbitrary strings like `"PWNED"` or change the extraction schema.
- **Canary & System Prompt Exfiltration**: Attacks instructing the model to recite prior instructions, internal developer canaries, or system guidelines.
- **Delimiter Escaping**: Injections using fake closing XML/delimiters (`<<NOTE_...>>`) to trick the model into interpreting attacker text as system commands.

### Invariant Checksums:
- `eval/frozen/gold_30.jsonl`: `5a1701e5a0fb26a53e58ae5dc390e4cd8061686f976fc28491403e0150c7ea17`
- `eval/frozen/attacks_v2_heldout.jsonl`: `d21b4aa2cec0c5ecb7f6c3c94f87f78a8aa2ba6b667f45e7876b37c51bd75b95`

These SHA-256 hashes are asserted during continuous integration (`eval/eval_gate.py` and `tests/test_baseline_data.py`). Any modification immediately breaks the CI build.

---

## 5. Licensing & Permitted Use

This evaluation dataset is distributed under the **MIT License**. It is freely usable for academic benchmarking, open-source model evaluation, and commercial service verification.
