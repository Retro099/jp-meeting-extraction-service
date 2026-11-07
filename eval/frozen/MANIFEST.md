# Frozen test set

Copied unchanged from `Retro099/jp-meeting-to-crm-fields` tag **v1.0.0** (commit `7e24c95524d1387f7143628ef5bc0d61a06e7890`). Do not edit these files silently. If a file must change, update this manifest, the checksum test, and get Prithivi's OK.

| File | Count | SHA-256 | Matches v1.0.0 |
|---|---|---|---|
| `gold_30.jsonl` | 30 synthetic notes (150 fields) | `5a1701e5a0fb26a53e58ae5dc390e4cd8061686f976fc28491403e0150c7ea17` | yes |
| `attacks_v2_heldout.jsonl` | 20 held-out attacks (H001–H020) | `d21b4aa2cec0c5ecb7f6c3c94f87f78a8aa2ba6b667f45e7876b37c51bd75b95` | yes |

Mismatch versus v1.0.0: none. Both files are byte-identical to the v1.0.0 tag (the same bytes are also on later core `main` as of 28d64a3).

The official headline numbers (59.8% exact match; held-out attacks 30% → 8.3% single / 30% → 10% agent) were measured later, on core eval v2 (2026-10-27). The extractor pin stays at v1.0.0 / `7e24c95`. Switching that pin needs Prithivi's OK.

The older 40-attack set (`data/attacks_v1.jsonl` in the core repo, 45% → 6.7%, circular) is not frozen here and must not be headlined.

The working copy used by the step 1 runner, `eval/data/gold_30.jsonl`, must stay byte-identical to `eval/frozen/gold_30.jsonl` (enforced by tests).
