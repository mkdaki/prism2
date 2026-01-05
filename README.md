## Prism

Docker Compose で **frontend（React + Vite）/ backend（FastAPI）/ db（PostgreSQL）** をまとめて起動する PoC 構成です。

## プロジェクト現状（箇条書き）
2025/12/28時点
- **全体構成**
    - **3サービス構成**：`frontend`（React+Vite）/ `backend`（FastAPI）/ `db`（PostgreSQL）を `docker-compose.yml` で起動する設計
    - **ディレクトリ**：`backend/`, `frontend/`, `db/`（現状は空ディレクトリ）

- **Docker / Compose**
    - **DB**
        - `postgres:16`
        - データは名前付きボリューム `pgdata` に永続化
        - **DBポートはデフォルトでホスト公開しない**（必要なら `docker-compose.yml` の `ports` をコメント解除して利用）
    - **Backend**
        - `./backend/Dockerfile` でビルド
        - ホスト `8001` → コンテナ `8000` に公開
        - DB接続は `DATABASE_URL=postgresql+psycopg://...@db:5432/...`（Compose の環境変数で注入）
        - ヘルスチェック：`http://localhost:8000/health` を叩く設定
    - **Frontend**
        - `./frontend/Dockerfile` でビルド
        - ホスト `3001` → コンテナ `3000` に公開
        - 環境変数 `VITE_API_BASE_URL=http://localhost:8001`

- **Backend（FastAPI / SQLAlchemy）**
    - **依存**：`fastapi`, `uvicorn`, `python-multipart`, `SQLAlchemy 2.x`, `psycopg3`（`backend/requirements.txt`）
    - **起動時の挙動**：PoCとして **起動時に Alembic（`alembic upgrade head`）を自動実行**してスキーマを最新化（後でOFF可能）
    - **API**
        - `GET /health`：`{"status":"ok"}`
        - `POST /datasets/upload`：CSV（UTF-8前提）を受け取り、`csv.DictReader` で読み込み→DBに保存して `dataset_id` と行数を返す
    - **DBモデル**（`backend/app/models.py`）
        - `datasets`：`id`, `filename`, `created_at`
        - `dataset_rows`：`id`, `dataset_id`（CASCADE）, `row_index`, `data`（PostgreSQL `JSONB`）, `created_at`
    - **DB接続**（`backend/app/db.py`）：環境変数 `DATABASE_URL` 必須、`SessionLocal` を用意

- **Frontend（React + Vite + TypeScript）**
    - **依存**：React 18 / Vite 5 / TypeScript 5（最小構成）
    - **画面**：`Prism Frontend` と `It works.` を表示するだけ（API呼び出し等は未実装）
    - **設定**：Vite dev server は `0.0.0.0:3000`（Docker前提）

- **Git管理上の状態（.gitignore）**
    - `frontend/node_modules/` は ignore 対象（ただし作業ツリー上には `frontend/node_modules/` ディレクトリが存在）

## 起動手順（具体的）

リポジトリ直下で以下を実行します。

```bash
docker compose up --build
```

## テスト手順（重要：ローカルPCのPython環境は使わない）

このプロジェクトは「ローカル環境を汚さない」方針のため、pytestは **backendコンテナ内** で実行します。

```bash
# テストはDBをTRUNCATEするため、開発用DB（pgdata）とは分離して実行する
# -p prism2-test を付けることで、DB/ネットワーク/ボリュームが別管理になる

# テスト用DBを起動
docker compose -p prism2-test up -d db

# スキーマを適用（entrypoint側の自動migrationはOFFにして明示的に実行）
docker compose -p prism2-test run --rm -e RUN_MIGRATIONS=0 backend alembic upgrade head

# pytest実行（終了後にbackendコンテナは自動削除）
docker compose -p prism2-test run --rm -e RUN_MIGRATIONS=0 backend pytest

# 片付け（テスト用DBは捨てる）
docker compose -p prism2-test down -v
```

## マイグレーション（Alembic）

### 適用（PoCデフォルト：起動時に自動適用）

backend コンテナはデフォルトで `RUN_MIGRATIONS=1` のため、起動時に `alembic upgrade head` を実行します。
後で本番寄りにしたい場合は `RUN_MIGRATIONS=0` にして、以下のように手動で適用できます。

```bash
docker compose up -d db
docker compose run --rm -e RUN_MIGRATIONS=0 backend alembic upgrade head
```

### リビジョン作成（例）

```bash
docker compose run --rm -e RUN_MIGRATIONS=0 backend alembic revision --autogenerate -m "change schema"
```

### 注意（既存の永続ボリュームを使っている場合）

PoCで `pgdata` に過去スキーマが残っていると、初期マイグレーションと衝突することがあります。
その場合は一度 `docker compose down -v` でボリュームを作り直してください（データは消えます）。

## 動作確認

- **Backend**
    - `http://localhost:8001/health`
- **Frontend**
    - `http://localhost:3001/`

## 開発方針（重要）

- ローカルPCのPython環境を汚さないため、Pythonの依存導入・テストは backend コンテナ内で完結させます。

## DBスキーマ管理について（PoC方針）

本プロジェクトでは、DBスキーマ管理に Alembic を採用する方針としています。
現状は Alembic によるマイグレーション管理へ移行済みです。
詳細は `docs/develop_process.md` を参照してください。
