# jp-meeting-extraction-service

**ステータス: 開発中（2026-11-04 開始）** [English](README.md)

日本語の商談メモから CRM 項目を抽出するサービス。評価とプロンプトインジェクション対策を CI で自動チェックします。

コア（評価と防御）: https://github.com/Retro099/jp-meeting-to-crm-fields
本リポジトリは同一プロジェクトのサービス部分（本番デプロイと CI ゲート）です。

## 概要
## アーキテクチャ
[docs/architecture.md](docs/architecture.md)
## 評価と CI ゲート
[eval/README.md](eval/README.md)、[PLAN.md](PLAN.md)
## セキュリティ / 脅威モデル
[docs/threat-model.md](docs/threat-model.md)
## 既知の制約
[PLAN.md](PLAN.md)
## ライセンス
MIT
