# jp-meeting-extraction-service

**ステータス: フィーチャーブランチ `feat/step3-api-handler`（ステップ3: ローカルAPIハンドラー、テスト、ゼロコストCI評価ゲート、脅威モデル完了）。プルリクエスト確認待ち。** [[English]](README.md)

日本語の商談メモから構造化されたCRM項目（5項目）を抽出するローカルHTTPサービスおよびLambdaハンドラー。コアエンジンである [Retro099/jp-meeting-to-crm-fields](https://github.com/Retro099/jp-meeting-to-crm-fields) のサービス運用レイヤーとして設計されています。

```bash
# レビュー対象のフィーチャーブランチをチェックアウト:
git checkout feat/step3-api-handler
```

---

## 本リポジトリの役割

コアリポジトリ（[jp-meeting-to-crm-fields](https://github.com/Retro099/jp-meeting-to-crm-fields)）では、抽出プロンプトの設計、合成データによる評価ベンチマーク、プロンプトインジェクション防御策を確立しました。

本リポジトリでは、その運用・デプロイ環境となる**サービス層**を実装しています：
- **ローカルAPIハンドラー**: Python標準ライブラリによるHTTPサーバー、およびAWS Lambda互換の `handle_extract(event, context)` ハンドラー。
- **入力・出力バリデーション**: 厳格なスキーマ検証、4,000文字の入力制限、対象5項目（`会社名`、`相手`、`次アクション`、`期限`、`リスク`）の単一スカラー文字列化およびサニタイズ。
- **認証**: 環境変数 `EXTRACTION_API_KEY` 設定時に有効化されるAPIキー認証（`x-api-key` または `Authorization: Bearer`、タイミング攻撃防止のための定数時間比較 `hmac.compare_digest` を使用）。
- **自動テスト環境**: 外部ネットワーク通信を行わず高速に完走するテストスイート（ヘルスチェック、異常系、バリデーション境界値、コスト計算、固定データチェックサム検証）。
- **CI評価ゲート**: GitHub Actions上で実行されるゼロコスト自動ゲート（`eval/eval_gate.py`）。固定データセットのハッシュ値、代表値メタデータ、スコアリング再現性を検証。

---

## ベースライン精度と公式指標

公式の評価指標は [`eval/BASELINE.md`](eval/BASELINE.md) および [`eval/baseline.json`](eval/baseline.json) に記録されています：

| 指標 | 公式値 | 説明 |
| --- | --- | --- |
| **完全一致率（Exact Match, 単一呼出）** | **59.8%** | 公式代表値（合成商談メモ30件・150項目、3回試行平均、コア eval v2） |
| **完全一致率（Agent Path）** | 58.4% | マルチステップ自律経路（単一呼出に対する統計的優位性はなし） |
| **未知の攻撃成功率（防御OFF → ON）** | 30.0% → 8.3% | 未知のプロンプトインジェクション攻撃20件（`H001`〜`H020`）での防御効果 |
| **推定推論コスト** | 約 0.022円 / 件 | API経由の Qwen 2.5 72B（約 $0.00026 / 抽出） |

> **59.8% と 60.7% の関係について**:  
> 固定されたコア `v1.0.0`（`7e24c95`）上での1回試行再現テストでは **60.7% (91/150)** を記録しました。この単一試行による差（+0.9ポイント）は再現記録として `eval/runs/2026-11-06/summary.json` に記載されていますが、公式の代表値は3回試行平均である **59.8%** を維持します。
> 
> 文字単位の厳格な完全一致判定では、自由記述項目が低く判定される傾向があります：
> - 固有名詞・日時項目: `相手` 30/30、`会社名` 29/30、`期限` 25/30
> - 自由記述項目: `次アクション` 7/30、`リスク` 0/30（※項目別のLLM意味的評価設計については [`eval/SEMANTIC_EVALUATION.md`](eval/SEMANTIC_EVALUATION.md) を参照）。

---

## クイックスタートとインストール

### 1. 必要要件
- Python 3.11 以上
- Git

### 2. 仮想環境のセットアップ
```bash
git clone https://github.com/Retro099/jp-meeting-extraction-service.git
cd jp-meeting-extraction-service
git checkout feat/step3-api-handler
python -m venv .venv

# Linux / macOS の場合:
source .venv/bin/activate
# Windows (PowerShell) の場合:
.venv\Scripts\Activate.ps1
```

### 3. 依存パッケージのインストール
```bash
pip install -r requirements.txt
pip install -e .
pip install pytest ruff
```

*補足*: パッケージインストール（`pip install -e .`）を行わない場合、`PYTHONPATH` を直接設定して実行することも可能です：
```bash
# Linux / macOS:
export PYTHONPATH=src
# Windows (PowerShell):
$env:PYTHONPATH = "src"
```

### 4. テストの実行
```bash
# 全単体テストおよび固定データ不変性テストの実行
pytest -v

# コード品質チェック
ruff check .

# CI評価ゲートの実行
python eval/eval_gate.py
```

---

## ローカルサービスの起動

Python標準ライブラリによるローカルHTTPサーバーを起動します：

```bash
python -m jp_extraction_service.handler
# Serving jp-meeting-extraction-service on http://127.0.0.1:8000 (POST /extract, GET /health)
```

### 1. ヘルスチェックの確認
```bash
curl http://127.0.0.1:8000/health
# {"status": "ok", "version": "0.0.1", "defenses_enabled": true}
```

### 2. 抽出エンドポイントの確認
抽出エンドポイント（POST `/extract`）で実際のLLM抽出を実行するには、上流モデル（Qwen 2.5 72B）のAPIキー（`AICREDITS_API_KEY`）が必要です。実際のAPI呼出には推論費用が発生します（約 0.022円 / 件）。

**環境変数 `AICREDITS_API_KEY` が設定されていない場合**、サーバーは安全にリクエストを拒否します：
```bash
curl -X POST http://127.0.0.1:8000/extract \
  -H "Content-Type: application/json" \
  -d '{"note": "本日は株式会社さくら商事の佐藤様と打ち合わせ。来週金曜までに御見積書を送付する。特段のリスクはなし。"}'
```
実際のサーバーレスポンス：
```json
{"ok": false, "error": "AICREDITS_API_KEY is not configured"}
```

**環境変数 `AICREDITS_API_KEY` 設定時のレスポンス例**（モック/動作例）：
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

## アーキテクチャおよび脅威モデル設計書
- アーキテクチャ設計書: [`docs/architecture.md`](docs/architecture.md)（コンポーネント構成、信頼境界、LambdaおよびECS Expressプロファイル）
- 脅威モデル（STRIDE）: [`docs/threat-model.md`](docs/threat-model.md)（プロンプトインジェクション、カナリア漏洩、トークン枯渇、キー保護）
- データセットカード: [`eval/DATASET_CARD.md`](eval/DATASET_CARD.md)（合成データの由来、個人情報ゼロ方針、MITライセンス）
- 意味的評価設計: [`eval/SEMANTIC_EVALUATION.md`](eval/SEMANTIC_EVALUATION.md)（自由記述項目のLLMジャッジ評価設計）

---

## 既知の制約事項
1. **合成データベンチマーク**: 使用している商談メモ30件および攻撃セット20件はすべて合成データであり、実顧客データは含まれません。
2. **完全一致評価の特性**: 文字列の完全一致を評価基準としているため、`次アクション` や `リスク` の自然言語のゆらぎが厳格に評価されます。
3. **コアドキュメントとのコミット差**: コアパッケージは `v1.0.0`（`7e24c955`）に固定されていますが、公式59.8%の3回平均値はコア eval v2 時点のプロトコルに基づきます。
4. **クラウド本番デプロイ**: AWS Lambda本番デプロイは今後実施予定（`PLAN.md` ステップ4）。GitHub ActionsにおけるゼロコストCI整合性ゲートは稼働中。

---

## ライセンス
MIT License. 詳細は [LICENSE](LICENSE) を参照してください。
