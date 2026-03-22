# StageCrew Fly.io デプロイ手順書

この手順書は、StageCrew を Fly.io へデプロイするための手順です。  
対象は以下の3コンポーネントです。

- Backend: FastAPI（`backend`）
- Frontend: nginx + React build（`frontend`）
- Database: Fly Postgres

## 1. このリポジトリの前提

- Backend App 名: `stagecrew-api`（`backend/fly.toml`）
- Frontend App 名: `stagecrew-web`（`frontend/fly.toml`）
- Postgres App 名: `stagecrew-db`（推奨）
- Region: `nrt`
- Frontend の `/api/*` は `stagecrew-api.internal:8000` にプロキシ（`frontend/nginx.conf`）

App 名を変える場合は、`frontend/nginx.conf` の `proxy_pass` も合わせて変更してください。

## 2. 事前準備

- Fly.io アカウント作成
- `flyctl` インストール
- `fly auth login` 実行
- Discord Developer Portal で OAuth アプリを作成（ログイン利用時）

## 3. 初回構築

### 3.1 Fly Postgres 作成

```bash
fly postgres create \
  --name stagecrew-db \
  --region nrt \
  --initial-cluster-size 1 \
  --vm-size shared-cpu-1x \
  --volume-size 10
```

### 3.2 Backend/Frontend App 作成

```bash
cd backend
fly apps create stagecrew-api

cd ../frontend
fly apps create stagecrew-web
```

### 3.3 Postgres を Backend にアタッチ

```bash
fly postgres attach stagecrew-db --app stagecrew-api
```

`attach` 後に `DATABASE_URL` が `postgres://...` 形式で作られることがあります。  
このプロジェクトは `asyncpg` を使うため、`postgresql+asyncpg://...` 形式に上書きしてください。

```bash
fly secrets set \
  "DATABASE_URL=postgresql+asyncpg://stagecrew:<PASSWORD>@stagecrew-db.internal:5432/stagecrew" \
  --app stagecrew-api
```

### 3.4 Backend Secrets 設定

```bash
fly secrets set \
  DISCORD_CLIENT_ID="<Discord Client ID>" \
  DISCORD_CLIENT_SECRET="<Discord Client Secret>" \
  JWT_SECRET_KEY="<ランダムな長い文字列>" \
  --app stagecrew-api
```

JWTシークレット例（ローカル生成）:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 3.5 Discord Redirect URI 設定

Discord 側の OAuth2 Redirects に次を登録:

```text
https://stagecrew-api.fly.dev/api/auth/discord/callback
```

App 名を変更した場合は、URL も合わせて変更してください。

## 4. デプロイ

### 4.1 Backend デプロイ

```bash
cd backend
fly deploy --remote-only
```

`backend/fly.toml` の `release_command = "alembic upgrade head"` により、リリース時にマイグレーションが実行されます。

### 4.2 Frontend デプロイ

```bash
cd frontend
fly deploy --remote-only
```

## 5. 動作確認

```bash
curl https://stagecrew-api.fly.dev/api/health
curl https://stagecrew-web.fly.dev/api/health
```

- 1つ目: Backend のヘルスチェック
- 2つ目: Frontend nginx 経由で Backend に到達できるかの確認

ブラウザで `https://stagecrew-web.fly.dev` も確認してください。

## 6. GitHub Actions で自動デプロイ（任意）

`.github/workflows/deploy.yml` は `master` への push でデプロイします。  
GitHub の `production` Environment に以下の Secret を設定してください。

- `FLY_API_TOKEN`

トークン作成例:

```bash
fly tokens create deploy -x 999999h
```

## 7. 運用で使うコマンド

```bash
fly status --app stagecrew-api
fly releases --app stagecrew-api
fly logs --app stagecrew-api
fly logs --app stagecrew-web
```

ロールバック:

```bash
fly releases rollback <RELEASE_ID> --app stagecrew-api
```

Secrets 確認:

```bash
fly secrets list --app stagecrew-api
```

