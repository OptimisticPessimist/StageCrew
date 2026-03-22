# StageCrew ローカル開発手順書

この手順書は、`backend`（FastAPI）+ `frontend`（Vite/React）+ `db`（PostgreSQL）をローカルで起動するための手順です。

## 1. 前提ツール

- Docker / Docker Desktop
- Python 3.12+
- `uv`（Python依存管理）
- Node.js 22+
- npm

## 2. 利用ポート

| サービス | URL / Port |
|---|---|
| Frontend (Vite) | `http://localhost:5173` |
| Backend (FastAPI) | `http://localhost:8000` |
| PostgreSQL (Docker) | `localhost:5432` |

## 3. 初回セットアップ

### 3.1 PostgreSQL を起動

リポジトリ直下で実行:

```bash
docker compose up -d db
docker compose ps
```

### 3.2 Backend の環境変数を作成

```bash
cd backend
cp .env.example .env
```

PowerShell で `cp` が使えない場合:

```powershell
Copy-Item .env.example .env
```

必要に応じて `.env` を編集してください。最低限、以下を確認します。

- `DATABASE_URL`（ローカルDB用）
- `JWT_SECRET_KEY`
- `DISCORD_CLIENT_ID` / `DISCORD_CLIENT_SECRET`（Discordログインを使う場合）

### 3.3 Backend 依存関係インストールとマイグレーション

```bash
cd backend
uv sync --all-extras
uv run alembic upgrade head
```

### 3.4 Frontend 依存関係インストール

```bash
cd frontend
npm ci
```

## 4. 開発サーバ起動

ターミナルを2つ使います。

### 4.1 Backend 起動

```bash
cd backend
uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### 4.2 Frontend 起動

```bash
cd frontend
npm run dev
```

補足:
- フロントエンドは `/api` を `http://localhost:8000` にプロキシします（`frontend/vite.config.ts`）。

## 5. 動作確認

```bash
curl http://localhost:8000/api/health
```

`{"status":"ok"}` が返れば Backend は正常です。  
ブラウザで `http://localhost:5173` を開いて画面表示を確認してください。

## 6. テスト/静的チェック（任意）

```bash
# backend
cd backend
uv run pytest
uv run ruff check .

# frontend
cd frontend
npm run lint
npm run build
```

## 7. 停止

```bash
# Vite / Uvicorn は Ctrl+C で停止
docker compose down
```

