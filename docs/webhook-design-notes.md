# Discord Webhook / 通知設計メモ

## 経緯

PR #5（本番カウントダウン機能）のレビューで、`ProductionResponse` に `discord_webhook_url` が含まれており、一般メンバーのブラウザに機密情報が露出する問題が指摘された。

### 対応内容（PR #5）
- `ProductionResponse` から `discord_webhook_url` を除外
- 管理者専用の `GET .../productions/{id}/webhook` エンドポイントを新設
- カウントダウン用に機密情報を含まない `GET .../productions/{id}/summary` エンドポイントを新設

### 見送った対応
- `create_production` / `update_production` のレスポンスにwebhook URLを含める管理者用スキーマの分離
  - 理由: 現時点でフロントエンドにwebhook設定UIが存在しないため、実装しても使われない

## Discord通知機能で対応すべきこと

現在の `Production.discord_webhook_url`（単一フィールド）は暫定的な設計。
Discord通知機能の実装時に以下を含めて再設計する。

### データモデル（想定）
- **団体レベル**の設定として管理:
  - 出欠確認用チャンネルID
  - 部署別Webhook URL（全体・制作部・演出部など）
- 現在の `Production.discord_webhook_url` は部署別Webhookに移行

### API設計
- Webhook設定の作成・更新レスポンスは管理者用スキーマを使用（webhook URLを含む）
- 一般メンバー向けレスポンスには引き続きwebhook URLを含めない

### 参照
- 要件定義: `docs/requirements.md` セクション5（通知）
- ロードマップ: `docs/roadmap.md` Phase 1 - Discord Webhook通知
