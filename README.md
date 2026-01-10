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

---

## PoCの範囲と制約（重要）

このプロジェクトは **PoC（Proof of Concept）** であり、本番運用には以下の改善が必要です。

### ✅ PoCで実装済み

- CSVアップロード（UTF-8 / Shift_JIS対応）
- PostgreSQLへのJSONB形式でのデータ格納
- 基本的な統計情報の算出（数値/文字列カラムの要約）
- LLM（Gemini）による簡易分析コメント生成
- Webブラウザでの閲覧画面（一覧/詳細/グラフ表示）
- ユニットテスト（カバレッジ80%以上）
- CI/CD（GitHub Actions）

### ❌ PoCで意図的に実装していないこと

#### 1. セキュリティ

- **認証・認可なし**: 誰でもアクセス・アップロード可能
- **SQLインジェクション対策**: SQLAlchemyのパラメータ化のみ（ユーザー入力の厳密なバリデーションなし）
- **XSS対策**: Reactのデフォルト機能のみ
- **CSRF対策なし**: APIにトークン認証なし
- **ファイルサイズ制限**: 最小限の検証のみ
- **レート制限なし**: DoS攻撃への対策なし

#### 2. データの永続性・バックアップ

- **バックアップなし**: DBボリュームのバックアップ/リストア機能なし
- **データ削除機能なし**: アップロードしたデータセットの削除機能なし
- **データ保持期限なし**: 古いデータの自動削除なし

#### 3. パフォーマンス・スケーラビリティ

- **大容量CSV未対応**: メモリ上で全行をロードするため、大きなファイル（100MB以上）は失敗する可能性
- **統計処理の最適化なし**: 大量データでの統計算出が遅い
- **ページネーションなし**: データセット一覧は全件取得
- **インデックス設計**: 最小限のみ
- **並列処理なし**: アップロード処理は逐次実行
- **キャッシュなし**: 統計情報の再計算が毎回発生

#### 4. 運用性

- **監視なし**: メトリクス収集、アラート機能なし
- **ログのローテーション**: ログファイルが無限に増加する可能性
- **エラー通知**: エラー発生時の管理者通知なし
- **ダウンタイム管理**: メンテナンスモードなし

#### 5. 機密情報・プライバシー

- **個人情報検出なし**: アップロードされたCSVに個人情報が含まれていても警告しない
- **データマスキングなし**: LLMに送信するデータのマスキング処理なし
- **監査ログなし**: 誰がいつ何をしたかの記録なし

#### 6. LLM関連

- **コスト制御が不十分**: LLM API呼び出しの上限設定が不十分
- **プロンプトインジェクション対策なし**: 悪意のある列名等への対策なし
- **レスポンス品質保証なし**: LLMの出力内容の検証なし
- **リトライ機能なし**: LLMタイムアウト時の自動リトライなし

### 🔧 本番運用に向けた推奨改善事項

1. **認証・認可の実装**（例: OAuth2, JWT）
2. **入力バリデーション強化**（スキーマ検証、サニタイゼーション）
3. **ファイルサイズ制限の厳格化**（環境変数で設定可能に）
4. **ストリーミング処理の導入**（大容量CSV対応）
5. **監視・ログ管理の整備**（Prometheus, Grafana, ELKなど）
6. **バックアップ戦略の策定**（定期バックアップ、PITR）
7. **HTTPS対応**（本番環境では必須）
8. **環境変数管理の厳格化**（Secrets Manager等）
9. **レート制限の実装**（API Gateway, nginx等）
10. **個人情報検出・マスキング機能**（PII検出ライブラリの導入）

### 📚 詳細ドキュメント

- 開発プロセス・タスク進捗: `docs/develop_process.md`
- 環境変数サンプル: `docs/env.example`
