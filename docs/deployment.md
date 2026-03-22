# StageCrew デプロイメントランブック

## 概要

StageCrew を Fly.io へデプロイするための手順書です。

| リソース | アプリ名 | リージョン |
|---|---|---|
| バックエンド（FastAPI） | `stagecrew-api` | nrt（東京） |
| フロントエンド（nginx） | `stagecrew-web` | nrt（東京） |
| データベース（PostgreSQL） | `stagecrew-db` | nrt（東京） |

### アーキテクチャ

```
ブラウザ → stagecrew-web.fly.dev
              │
              ├─ /api/* → nginx リバースプロキシ
              │           → stagecrew-api.internal:8000（Fly 内部ネットワーク）
              │           → FastAPI
              │
              └─ /* → index.html（React SPA）
```

フロントエンドの nginx が `/api/*` リクエストをバックエンドへプロキシするため、
ビルド時に API の URL を埋め込む必要がありません。

---

## 前提条件

- [ ] [Fly.io アカウント](https://fly.io) 作成済み
- [ ] `flyctl` CLI インストール済み
  ```bash
  curl -L https://fly.io/install.sh | sh
  ```
- [ ] `fly auth login` で認証済み
- [ ] [Discord Developer Portal](https://discord.com/developers/applications) でアプリケーション作成済み
- [ ] GitHub リポジトリへのアクセス権限

---

## 初回セットアップ手順

### 1. Alembic 初期マイグレーションの生成

ローカル環境で実行します（Docker Compose の PostgreSQL を使用）。

```bash
# ローカル DB を起動
docker compose up -d

# マイグレーションファイルを自動生成
cd backend
uv run alembic revision --autogenerate -m "initial_schema"

# 生成されたファイルを確認
ls alembic/versions/

# ローカルで適用して動作確認
uv run alembic upgrade head
uv run alembic current

# git にコミット
git add alembic/versions/
git commit -m "マイグレーション: 初期スキーマを追加"
```

> **重要**: このファイルが存在しないと CI のテストも失敗します。
> 必ずデプロイ前にコミットしてください。

### 2. Fly Postgres データベースの作成

```bash
fly postgres create \
  --name stagecrew-db \
  --region nrt \
  --initial-cluster-size 1 \
  --vm-size shared-cpu-1x \
  --volume-size 10
```

出力される接続文字列（`postgres://...`）を控えておきます。

### 3. バックエンドアプリの作成

```bash
cd backend
fly apps create stagecrew-api
```

### 4. データベースのアタッチ

```bash
fly postgres attach stagecrew-db --app stagecrew-api
```

> **注意**: このコマンドは `DATABASE_URL` シークレットを自動設定しますが、
> 形式が `postgres://` になります。asyncpg は `postgresql+asyncpg://` が必要なため
> 次のステップで上書きします。

### 5. DATABASE_URL の形式変換と再設定

```bash
# 現在の DATABASE_URL を確認
fly secrets list --app stagecrew-api

# asyncpg 形式に変換して再設定（<PASSWORD> を実際のパスワードに置き換え）
fly secrets set \
  "DATABASE_URL=postgresql+asyncpg://stagecrew:<PASSWORD>@stagecrew-db.internal:5432/stagecrew" \
  --app stagecrew-api
```

### 6. バックエンドのシークレット設定

```bash
# JWT_SECRET_KEY の生成
python -c "import secrets; print(secrets.token_hex(32))"

# シークレットを一括設定
fly secrets set \
  DISCORD_CLIENT_ID="<Discord アプリケーション ID>" \
  DISCORD_CLIENT_SECRET="<Discord クライアントシークレット>" \
  JWT_SECRET_KEY="<上で生成したキー>" \
  --app stagecrew-api
```

### 7. Discord OAuth2 リダイレクト URI の登録

[Discord Developer Portal](https://discord.com/developers/applications) にて:

1. アプリケーションを選択
2. **OAuth2 → General** へ移動
3. **Redirects** に以下を追加:
   ```
   https://stagecrew-api.fly.dev/api/auth/discord/callback
   ```

### 8. フロントエンドアプリの作成

```bash
cd frontend
fly apps create stagecrew-web
```

### 9. 初回デプロイの実行

```bash
# バックエンドを先にデプロイ（マイグレーション自動実行）
cd backend
fly deploy --remote-only

# フロントエンドをデプロイ
cd ../frontend
fly deploy --remote-only
```

### 10. GitHub Actions の設定

GitHub リポジトリの **Settings > Secrets and variables > Actions** にて
`production` 環境を作成し、以下のシークレットを登録します:

| シークレット名 | 取得方法 |
|---|---|
| `FLY_API_TOKEN` | `fly tokens create deploy -x 999999h` の出力 |

以降は master への push で自動デプロイされます。

---

## 動作確認

初回デプロイ後に以下を確認します:

```bash
# バックエンドのヘルスチェック
curl https://stagecrew-api.fly.dev/api/health
# → {"status": "ok"} が返ること

# フロントエンドの表示確認
# ブラウザで https://stagecrew-web.fly.dev を開き、ログイン画面が表示されること

# nginx プロキシの確認
curl https://stagecrew-web.fly.dev/api/health
# → バックエンドと同じレスポンスが返ること
```

---

## 日常運用

### ログの確認

```bash
# バックエンドのリアルタイムログ
fly logs --app stagecrew-api

# フロントエンドのリアルタイムログ
fly logs --app stagecrew-web
```

### デプロイ状況の確認

```bash
fly status --app stagecrew-api
fly releases --app stagecrew-api
```

### マイグレーションの手動実行

```bash
fly ssh console --app stagecrew-api --command "alembic upgrade head"
```

### シークレットの更新

```bash
# 例: JWT_SECRET_KEY のローテーション
fly secrets set JWT_SECRET_KEY="<新しいキー>" --app stagecrew-api
# → アプリが自動再起動される
```

### スケールアップ

```bash
# メモリを増加（256mb → 512mb）
fly scale memory 512 --app stagecrew-api

# インスタンス数を増加
fly scale count 2 --app stagecrew-api
```

---

## トラブルシューティング

### マイグレーション失敗時

```bash
# 現在のマイグレーション状態を確認
fly ssh console --app stagecrew-api --command "alembic current"

# 1つ前にロールバック
fly ssh console --app stagecrew-api --command "alembic downgrade -1"
```

### デプロイ失敗時

```bash
# デプロイ履歴を確認
fly releases --app stagecrew-api

# 前バージョンへロールバック
fly releases rollback <バージョン番号> --app stagecrew-api
```

### DATABASE_URL の接続エラー

`postgresql+asyncpg://` 形式になっているかを確認します:

```bash
fly secrets list --app stagecrew-api
```

`postgres://` になっている場合は [手順 5](#5-database_url-の形式変換と再設定) を再実行してください。

---

## 環境変数一覧

### fly secrets（暗号化・Fly 側管理）

| 変数名 | 説明 |
|---|---|
| `DATABASE_URL` | PostgreSQL 接続文字列（asyncpg 形式） |
| `DISCORD_CLIENT_ID` | Discord アプリケーション ID |
| `DISCORD_CLIENT_SECRET` | Discord クライアントシークレット |
| `JWT_SECRET_KEY` | JWT 署名キー（32バイト以上のランダム文字列） |

### fly.toml [env]（非機密・公開設定）

| 変数名 | 値 |
|---|---|
| `DEBUG` | `false` |
| `CORS_ORIGINS` | `["https://stagecrew-web.fly.dev"]` |
| `FRONTEND_URL` | `https://stagecrew-web.fly.dev` |
| `DISCORD_REDIRECT_URI` | `https://stagecrew-api.fly.dev/api/auth/discord/callback` |
