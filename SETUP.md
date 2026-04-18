# StageCrew デプロイ設定ガイド

Cloudflare Pages + Supabase + Render 構成のセットアップ手順。

---

## 1. Supabase

### 1.1 プロジェクト作成

1. [supabase.com](https://supabase.com) にログイン
2. **New Project** をクリック
3. 以下を設定:
   - **Name**: `stagecrew`
   - **Database Password**: 安全なパスワードを生成（後で使うので控える）
   - **Region**: `Northeast Asia (Tokyo)` — `ap-northeast-1`

### 1.2 キー・接続情報の取得

プロジェクト作成後、以下の値を控える:

#### Settings > API Keys

| キー | 環境変数 | 用途 |
|------|---------|------|
| **Publishable Key** (`sb_publishable_...`) | `SUPABASE_PUBLISHABLE_KEY` / `VITE_SUPABASE_PUBLISHABLE_KEY` | フロントエンド + Backend の Supabase クライアント初期化 |
| **Secret Key** (`sb_secret_...`) | — | 将来的にサーバー側で Supabase Admin API を使う場合のみ |

> **注意**: Legacy API Keys タブに表示される `anon key` / `service_role key` は非推奨。新規プロジェクトでは Publishable Key / Secret Key を使用すること。

#### Settings > General

| 値 | 環境変数 |
|----|---------|
| **Project URL** (`https://[ref].supabase.co`) | `SUPABASE_URL` / `VITE_SUPABASE_URL` |

#### Settings > JWT Signing Keys

新規プロジェクトでは **RS256 (非対称鍵)** がデフォルト。

- バックエンドは JWKS エンドポイント (`https://[ref].supabase.co/auth/v1/.well-known/jwks.json`) から公開鍵を自動取得するため、**JWT Secret の手動設定は不要**。
- `SUPABASE_JWT_SECRET` 環境変数は使用しない。

#### Settings > Database

| 接続方式 | ポート | 用途 | 環境変数 |
|---------|--------|------|---------|
| Transaction mode (Supavisor) | 6543 | アプリケーション用 | `DATABASE_URL` |
| Session mode | 5432 | Alembic マイグレーション用 | `MIGRATION_DATABASE_URL` |

接続文字列の形式:
```
postgresql+asyncpg://postgres.[project-ref]:[password]@aws-1-ap-northeast-1.pooler.supabase.com:[port]/postgres?ssl=require
export MIGRATION_DATABASE_URL="postgresql+asyncpg://postgres.[project-ref]:[password]@aws-1-ap-northeast-1.pooler.supabase.com:5432/postgres?ssl=require"
export DATABASE_URL="$MIGRATION_DATABASE_URL"

uv run alembic upgrade head
```

### 1.5 締切リマインダー (pg_cron) の設定

1. **Database > Extensions** で以下を有効化:
   - `pg_cron`
   - `pg_net`
2. **SQL Editor** を開く
3. `supabase/migrations/001_deadline_reminder_cron.sql` の内容を貼り付けて実行
4. 動作確認:
   ```sql
   -- cron ジョブ一覧を確認
   SELECT * FROM cron.job;

   -- 手動テスト実行
   SELECT public.notify_deadline_reminders();
   ```

---

## 2. Render (Backend)

### 2.1 Web Service 作成

1. [render.com](https://render.com) にログイン
2. **New > Web Service** をクリック
3. GitHub リポジトリを接続
4. 以下を設定:
   - **Name**: `stagecrew-api`
   - **Region**: `Singapore` (東京に最も近い)
   - **Runtime**: `Docker`
   - **Docker Context**: `./backend`
   - **Dockerfile Path**: `./backend/Dockerfile`
   - **Instance Type**: `Free`
   - **Pre-Deploy Command**: `alembic upgrade head`

### 2.2 環境変数

Render ダッシュボードの **Environment** タブで以下を設定:

| 変数名 | 値 | 説明 |
|--------|-----|------|
| `DATABASE_URL` | `postgresql+asyncpg://postgres.[ref]:[pass]@...pooler.supabase.com:6543/postgres?ssl=require` | Supabase pooled connection (port **6543**) |
| `MIGRATION_DATABASE_URL` | `postgresql+asyncpg://postgres.[ref]:[pass]@...pooler.supabase.com:5432/postgres?ssl=require` | Supabase direct connection (port **5432**) |
| `SUPABASE_URL` | `https://[ref].supabase.co` | Supabase プロジェクト URL |
| `SUPABASE_PUBLISHABLE_KEY` | `sb_publishable_...` | Publishable Key |
| `FRONTEND_URL` | `https://stagecrew.pages.dev` | Cloudflare Pages の URL |
| `CORS_ORIGINS` | `["https://stagecrew.pages.dev"]` | CORS 許可オリジン |
| `DEBUG` | `false` | 本番では false |

### 2.3 Deploy Hook (任意)

自動デプロイが不要な場合:
1. **Settings > Deploy Hook** から URL を生成
2. GitHub Secrets に `RENDER_DEPLOY_HOOK` として保存

---

## 3. Cloudflare Pages (Frontend)

### 3.1 プロジェクト作成

1. [Cloudflare Dashboard](https://dash.cloudflare.com) にログイン
2. **Workers & Pages > Create** をクリック
3. **Connect to Git** で GitHub リポジトリを選択
4. ビルド設定:
   - **Project name**: `stagecrew`
   - **Production branch**: `master`
   - **Framework preset**: `None`
   - **Root directory**: `frontend`
   - **Build command**: `npm run build`
   - **Build output directory**: `dist`

### 3.2 環境変数

**Settings > Environment variables** で以下を設定 (Production と Preview 両方):

| 変数名 | 値 | 説明 |
|--------|-----|------|
| `VITE_SUPABASE_URL` | `https://[ref].supabase.co` | Supabase プロジェクト URL |
| `VITE_SUPABASE_PUBLISHABLE_KEY` | `sb_publishable_...` | Publishable Key |
| `VITE_API_URL` | `https://stagecrew-api.onrender.com/api` | Render の Backend URL |

### 3.3 カスタムドメイン (任意)

1. **Custom domains** タブでドメインを追加
2. DNS レコードを Cloudflare に向ける
3. CORS_ORIGINS をカスタムドメインに更新

---

## 4. GitHub Secrets

リポジトリの **Settings > Secrets and variables > Actions** で設定:

| Secret 名 | 値 | 用途 |
|-----------|-----|------|
| `RENDER_DEPLOY_HOOK` | Render の Deploy Hook URL | deploy.yml で使用 |

---

## 5. ローカル開発

### Backend

```bash
cd backend

# .env を編集 (ローカル DB を使う場合)
cp .env.example .env
# DATABASE_URL をローカル PostgreSQL または Supabase に設定

# 依存インストール
uv sync --all-extras

# マイグレーション
uv run alembic upgrade head

# 起動 (DEBUG=true でトークンなしアクセス可能)
uv run uvicorn src.main:app --reload
```

### Frontend

```bash
cd frontend

# 依存インストール
npm install

# .env.local を作成
cat > .env.local << 'EOF'
VITE_SUPABASE_URL=https://[ref].supabase.co
VITE_SUPABASE_PUBLISHABLE_KEY=sb_publishable_...
VITE_API_URL=http://localhost:8000/api
EOF

# 起動
npm run dev
```

---

## 6. 確認チェックリスト

- [ ] Supabase プロジェクト作成済み
- [ ] Publishable Key を取得済み（Settings > API Keys）
- [ ] JWT Signing Keys が RS256 であることを確認（Settings > JWT Signing Keys）
- [ ] Discord プロバイダー有効化済み
- [ ] Alembic マイグレーション実行済み
- [ ] pg_cron + pg_net 拡張有効化済み
- [ ] 締切リマインダー SQL 実行済み
- [ ] Render Web Service 作成済み
- [ ] Render 環境変数設定済み
- [ ] Cloudflare Pages プロジェクト作成済み
- [ ] Cloudflare Pages 環境変数設定済み
- [ ] Discord ログインが動作する
- [ ] `/api/health` がレスポンスを返す
- [ ] CORS が正しく動作する（ブラウザコンソールでエラーなし）
- [ ] 締切リマインダーの cron ジョブが登録されている (`SELECT * FROM cron.job`)

---

## アーキテクチャ図

```
[ユーザー]
    |
    v
[Cloudflare Pages]  ------>  [Render (FastAPI)]  ------>  [Supabase PostgreSQL]
  (Frontend)          API       (Backend)           DB        (Database)
  React + Vite        呼出      Python 3.12                   + pg_cron (リマインダー)
                                                              + pg_net (Discord通知)
    |
    v
[Supabase Auth]                [JWKS Endpoint]
  Discord OAuth      <------     RS256 公開鍵
                     JWT検証
```

## 無料枠の制限

| サービス | 制限 |
|---------|------|
| **Cloudflare Pages** | 無制限リクエスト, 500回ビルド/月 |
| **Render** | 750時間/月, 15分無操作でスリープ, コールドスタート30-50秒 |
| **Supabase** | 500MB DB, 5万MAU, 50万 Edge Function 呼出/月, 2プロジェクト |
