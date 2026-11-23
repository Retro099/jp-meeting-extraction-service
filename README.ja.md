# jp-meeting-extraction-service

**ステータス: 開発中（ステップ3: ローカルAPIハンドラーおよびテスト完了）** [[English]](README.md)

日本語の商談メモから構造化されたCRM項目（5項目）を抽出する本番向けマイクロサービスおよびCI評価ゲート。コアエンジンである [Retro099/jp-meeting-to-crm-fields](https://github.com/Retro099/jp-meeting-to-crm-fields) のサービス運用レイヤーとして設計されています。

---

## 本リポジトリの役割

コアリポジトリ（[jp-meeting-to-crm-fields](https://github.com/Retro099/jp-meeting-to-crm-fields)）では、抽出プロンプトの設計、合成データによる評価ベンチマーク、プロンプトインジェクション防御策を確立しました。

本リポジトリでは、その運用・デプロイ環境となる**マイクロサービス層**を実装しています：
- **ローカルAPIハンドラー**: Python標準ライブラリ（外部フレームワーク依存ゼロ）によるHTTPサーバー、およびAWS Lambda互換の `handle_extract(event, context)` ハンドラー。
- **入力・出力バリデーション**: 厳格なスキーマ検証、4,000文字の入力制限、対象5項目（`会社名`、`相手`、`次アクション`、`期限`、`リスク`）の単一スカラー文字列化およびサニタイズ。
- **認証**: 環境変数 `EXTRACTION_API_KEY` 設定時に有効化されるAPIキー認証（`x-api-key` または `Authorization: Bearer`）。
- **自動テスト環境**: 外部ネットワーク通信を行わず1秒未満で完走する16件のテストスイート（ヘルスチェック、異常系、バリデーション境界値、固定データチェックサム検証）。

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
> - 自由記述項目: `次アクション` 7/30、`リスク` 0/30（※コアリポジトリ内のLLMセマンティックジャッジでは、それぞれ 0.89、0.73 の高スコアを記録しています）。

---

## クイックスタートとインストール

### 1. 必要要件
- Python 3.11 以上
- Git

### 2. 仮想環境のセットアップ
```bash
git clone https://github.com/Retro099/jp-meeting-extraction-service.git
cd jp-meeting-extraction-service
python -m venv .venv

# Linux / macOS の場合:
source .venv/bin/activate
# Windows (PowerShell) の場合:
.venv\Scripts\Activate.ps1
```

### 3. 依存パッケージのインストール
```bash
pip install -r requirements.txt
pip install pytest ruff
```

### 4. テストの実行
```bash
# 全単体テストおよび固定データ不変性テストの実行
pytest -v

# コード品質チェック
ruff check .
```

---

## ローカルサービスの起動

Python標準ライブラリによるローカルHTTPサーバーを起動します：

```bash
python -m jp_extraction_service.handler
# Serving jp-meeting-extraction-service on http://127.0.0.1:8000 (POST /extract, GET /health)
```

### ヘルスチェックの確認
```bash
curl http://127.0.0.1:8000/health
# {"status": "ok", "version": "0.0.1", "defenses_enabled": true}
```

### 抽出リクエストの確認（ローカル開発 / モック）
```bash
curl -X POST http://127.0.0.1:8000/extract \
  -H "Content-Type: application/json" \
  -d '{"note": "本日は株式会社さくら商事の佐藤様と打ち合わせ。来週金曜までに御見積書を送付する。特段のリスクはなし。"}'
```

レスポンス例:
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

## アーキテクチャと脅威モデルの策定状況
- アーキテクチャ設計書: [`docs/architecture.md`](docs/architecture.md)（策定中・プレースホルダー）
- 脅威モデルおよび防御検証: [`docs/threat-model.md`](docs/threat-model.md)（策定中・プレースホルダー）

---

## 既知の制約事項
1. **合成データベンチマーク**: 使用している商談メモ30件および攻撃セット20件はすべて合成データであり、実顧客データは含まれません。
2. **完全一致評価の特性**: 文字列の完全一致を評価基準としているため、`次アクション` や `リスク` の自然言語のゆらぎが厳格に評価されます。
3. **コアドキュメントとのコミット差**: コアパッケージは `v1.0.0`（`7e24c955`）に固定されていますが、公式59.8%の3回平均値はコア eval v2 時点のプロトコルに基づきます。
4. **クラウド本番デプロイ**: AWS Lambda および CI自動評価ゲートは順次展開中です（`PLAN.md` のステップ4〜5）。

---

## ライセンス
MIT License. 詳細は [LICENSE](LICENSE) を参照してください。
