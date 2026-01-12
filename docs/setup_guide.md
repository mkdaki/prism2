# Prism プロジェクト セットアップガイド

新規参加エンジニア向けのDocker Compose環境構築手順書です。

## 目次

1. [前提条件](#前提条件)
2. [初期セットアップ手順](#初期セットアップ手順)
3. [起動と動作確認](#起動と動作確認)
4. [開発時の基本操作](#開発時の基本操作)
5. [トラブルシューティング](#トラブルシューティング)

---

## 前提条件

### 必須ソフトウェア

ローカルPCに以下がインストールされていることを確認してください。

- **Docker Desktop**（Windows 11の場合）
  - バージョン: 20.10 以上
  - Docker Compose V2 が含まれています
- **Git for Windows**
  - Git Bash を使用します
- **テキストエディタ**
  - VS Code 推奨

### 動作確認コマンド

```bash
# Dockerバージョン確認
docker --version
# 出力例: Docker version 24.0.7, build afdd53b

# Docker Composeバージョン確認
docker compose version
# 出力例: Docker Compose version v2.23.0

# Gitバージョン確認
git --version
# 出力例: git version 2.43.0.windows.1
```

---

## 初期セットアップ手順

### ステップ1: リポジトリのクローン

Git Bash を開き、作業ディレクトリでリポジトリをクローンします。

```bash
# リポジトリをクローン
git clone <リポジトリURL> prism2
cd prism2
```

### ステップ2: 環境変数ファイルの作成

LLM機能（Gemini）を使用する場合は、環境変数ファイルを作成します。

```bash
# サンプルファイルをコピーして .env を作成
cp docs/env.example .env
```

`.env` ファイルを編集し、必要な設定を行います。

```bash
# エディタで .env を開く（VS Codeの例）
code .env
```

**設定項目:**

```env
# LLM機能を使用する場合（使わない場合は 0 のまま）
ANALYSIS_USE_LLM=1
LLM_PROVIDER=gemini
LLM_API_KEY=YOUR_GEMINI_API_KEY_HERE
LLM_MODEL=gemini-2.0-flash
LLM_TIMEOUT_SECONDS=20
GEMINI_API_BASE_URL=https://generativelanguage.googleapis.com
```

**注意事項:**
- LLM機能を使わない場合は `ANALYSIS_USE_LLM=0` のままで問題ありません
- API キーは **絶対にコミットしないでください**（`.gitignore` で除外済み）
- Gemini APIキーは [Google AI Studio](https://makersuite.google.com/app/apikey) で取得できます

### ステップ3: Dockerイメージのビルド

初回起動時にイメージをビルドします。

```bash
# 全サービスをビルド（5〜10分程度かかります）
docker compose build
```

**ビルドの内容:**
- `backend`: Python依存パッケージのインストール（FastAPI, SQLAlchemy等）
- `frontend`: Node.js依存パッケージのインストール（React, Vite等）
- `db`: PostgreSQL公式イメージを使用（ビルド不要）

---

## 起動と動作確認

### ステップ4: サービスの起動

```bash
# 全サービスを起動（初回はDBの初期化とマイグレーションが実行されます）
docker compose up -d
```

**起動の流れ:**
1. `db` サービスが起動（PostgreSQL）
2. `db` のヘルスチェックが完了するまで待機
3. `backend` サービスが起動（FastAPI）
   - 環境変数 `RUN_MIGRATIONS=1` により、起動時に `alembic upgrade head` が自動実行されます
4. `frontend` サービスが起動（React + Vite開発サーバ）

**起動状態の確認:**

```bash
# サービスの状態確認
docker compose ps

# 期待される出力:
# NAME                  IMAGE               STATUS              PORTS
# prism2-backend-1     prism2-backend      Up (healthy)        0.0.0.0:8001->8000/tcp
# prism2-frontend-1    prism2-frontend     Up                  0.0.0.0:3001->3000/tcp
# prism2-db-1          postgres:16         Up (healthy)        5432/tcp
```

### ステップ5: 動作確認

#### Backend APIの確認

ブラウザまたはcurlで以下のエンドポイントにアクセスします。

```bash
# ヘルスチェックAPI
curl http://localhost:8001/health

# 期待されるレスポンス:
# {"status":"ok"}
```

または、ブラウザで `http://localhost:8001/health` を開きます。

#### Frontendの確認

ブラウザで以下のURLを開きます。

```
http://localhost:3001/
```

**期待される表示:**
- Prism のデータセット一覧画面が表示されます
- 初回起動時はデータセットが空なので「データセットがありません」と表示されます

#### API ドキュメントの確認

FastAPI は自動的にAPIドキュメントを生成します。

```
http://localhost:8001/docs
```

Swagger UI が表示され、各エンドポイントを試すことができます。

### ステップ6: ログの確認

```bash
# 全サービスのログをリアルタイム表示
docker compose logs -f

# 特定のサービスのログのみ表示
docker compose logs -f backend
docker compose logs -f frontend
docker compose logs -f db

# 最新100行のみ表示
docker compose logs --tail=100
```

**ログの見方:**
- `backend-1`: FastAPIのリクエストログ、エラーログ
- `frontend-1`: Viteの開発サーバログ、ビルドログ
- `db-1`: PostgreSQLの起動ログ、クエリログ（詳細はデフォルトOFF）

---

## 開発時の基本操作

### サービスの停止・再起動

```bash
# 全サービスを停止（コンテナは削除されますが、データベースは保持されます）
docker compose down

# 全サービスを再起動
docker compose restart

# 特定のサービスのみ再起動（例: バックエンドの再起動）
docker compose restart backend
```

### コードを変更した場合

#### Backendコードの変更

```bash
# 変更を反映するには再ビルドと再起動が必要
docker compose up -d --build backend
```

#### Frontendコードの変更

- Vite開発サーバはホットリロードに対応しているため、コードを保存すると自動的にブラウザがリロードされます
- 依存パッケージを追加した場合は再ビルドが必要:

```bash
docker compose up -d --build frontend
```

### テストの実行

**重要:** テストは開発用DBとは別のDB環境で実行します。

```bash
# 1. テスト用DBを起動
docker compose -p prism2-test up -d db

# 2. テスト用DBにスキーマを適用
docker compose -p prism2-test run --rm -e RUN_MIGRATIONS=0 backend alembic upgrade head

# 3. テストを実行
docker compose -p prism2-test run --rm -e RUN_MIGRATIONS=0 backend pytest

# 4. カバレッジ付きでテストを実行
docker compose -p prism2-test run --rm -e RUN_MIGRATIONS=0 backend pytest --cov=app --cov-report=term-missing

# 5. テスト環境のクリーンアップ（DBデータも削除）
docker compose -p prism2-test down -v
```

**解説:**
- `-p prism2-test`: プロジェクト名を指定して開発環境と分離
- `--rm`: コマンド終了後にコンテナを自動削除
- `-e RUN_MIGRATIONS=0`: 起動時の自動マイグレーションを無効化
- `-v`: ボリュームも削除（テストデータを完全にクリーンアップ）

### データベースマイグレーション

#### マイグレーションの適用

通常は起動時に自動適用されますが、手動で適用する場合:

```bash
# 最新のマイグレーションを適用
docker compose run --rm -e RUN_MIGRATIONS=0 backend alembic upgrade head

# 1つ前のバージョンに戻す
docker compose run --rm -e RUN_MIGRATIONS=0 backend alembic downgrade -1

# 特定のリビジョンに移動
docker compose run --rm -e RUN_MIGRATIONS=0 backend alembic upgrade <revision_id>
```

#### マイグレーションファイルの作成

モデル（`backend/app/models.py`）を変更した場合、マイグレーションファイルを生成します。

```bash
# 変更を自動検出してマイグレーションファイルを生成
docker compose run --rm -e RUN_MIGRATIONS=0 backend alembic revision --autogenerate -m "変更内容の説明"

# 生成されたファイルを確認
ls -l backend/alembic/versions/
```

**注意事項:**
- 自動生成されたファイルは必ず内容を確認してください
- 意図しない変更が含まれていないかチェックが必要です
- 生成後は `docker compose up -d` で自動適用されます

#### マイグレーション履歴の確認

```bash
# 現在のマイグレーション状態を確認
docker compose run --rm -e RUN_MIGRATIONS=0 backend alembic current

# マイグレーション履歴を表示
docker compose run --rm -e RUN_MIGRATIONS=0 backend alembic history
```

### データベースの直接操作

開発時にDBを直接確認したい場合:

```bash
# DBコンテナ内でpsqlを起動
docker compose exec db psql -U prism -d prism

# よく使うSQLコマンド例:
# \dt              -- テーブル一覧
# \d datasets      -- テーブル構造を表示
# SELECT * FROM datasets LIMIT 10;  -- データを確認
# \q               -- psql終了
```

**注意:** デフォルトではDBポートはホストに公開されていません。PgAdmin等のGUIツールを使いたい場合は `docker-compose.yml` の該当箇所をコメント解除してください。

### データベースのリセット

開発中にDBを完全にリセットしたい場合:

```bash
# 警告: 全データが削除されます！

# 1. サービスを停止してボリュームを削除
docker compose down -v

# 2. 再起動（DBが初期化されます）
docker compose up -d
```

### 依存パッケージの追加

#### Backend（Python）

```bash
# 1. requirements.txt を編集
echo "new-package==1.0.0" >> backend/requirements.txt

# 2. イメージを再ビルド
docker compose up -d --build backend
```

#### Frontend（Node.js）

```bash
# 1. package.json を編集するか、コンテナ内でnpm installを実行
docker compose exec frontend npm install <package-name>

# 2. package.jsonの変更を反映（ホスト側に同期されます）
# 3. イメージを再ビルド（本番ビルド時のため）
docker compose up -d --build frontend
```

---

## トラブルシューティング

### 起動時のよくある問題

#### 問題1: ポートが既に使用されている

**エラーメッセージ:**
```
Error response from daemon: Ports are not available: exposing port TCP 0.0.0.0:8001 -> 0.0.0.0:0: listen tcp 0.0.0.0:8001: bind: address already in use
```

**解決方法:**

```bash
# 使用中のポートを確認（Git Bashの場合）
netstat -ano | grep :<ポート番号>

# 該当するプロセスを終了するか、docker-compose.yml のポート番号を変更
```

#### 問題2: DBのヘルスチェックが失敗する

**症状:** `docker compose ps` で `db` が `unhealthy` と表示される

**解決方法:**

```bash
# DBのログを確認
docker compose logs db

# DBコンテナを再起動
docker compose restart db

# それでも解決しない場合はボリュームを削除して再作成
docker compose down -v
docker compose up -d
```

#### 問題3: マイグレーションエラー

**エラーメッセージ:**
```
alembic.util.exc.CommandError: Target database is not up to date.
```

**解決方法:**

```bash
# 現在のマイグレーション状態を確認
docker compose run --rm -e RUN_MIGRATIONS=0 backend alembic current

# 強制的に最新に更新
docker compose run --rm -e RUN_MIGRATIONS=0 backend alembic upgrade head

# それでも解決しない場合はDBをリセット
docker compose down -v
docker compose up -d
```

#### 問題4: Frontendがビルドエラーで起動しない

**解決方法:**

```bash
# Frontendのログを確認
docker compose logs frontend

# node_modules をクリーンアップして再ビルド
docker compose down
docker compose up -d --build frontend
```

#### 問題5: Backendが起動しない（依存パッケージエラー）

**解決方法:**

```bash
# Backendのログを確認
docker compose logs backend

# イメージを完全に再ビルド（キャッシュなし）
docker compose build --no-cache backend
docker compose up -d backend
```

### Docker環境のクリーンアップ

開発中に不要なイメージやボリュームが溜まった場合:

```bash
# 停止中のコンテナを削除
docker container prune

# 未使用のイメージを削除
docker image prune -a

# 未使用のボリュームを削除（注意: データが削除されます）
docker volume prune

# 全てをクリーンアップ（注意: 全プロジェクトに影響します）
docker system prune -a --volumes
```

### ログの詳細確認

```bash
# 特定のサービスのログを詳細表示
docker compose logs -f --tail=1000 backend

# エラーログのみ抽出（Git Bashの場合）
docker compose logs backend | grep -i error

# タイムスタンプ付きでログ表示
docker compose logs -t backend
```

---

## 次のステップ

セットアップが完了したら、以下のドキュメントを参照してください。

- **開発プロセス**: `docs/develop_process.md`
  - タスク管理、Git運用、開発フローの詳細
- **要件定義**: `docs/Requirements Definition.md`
  - プロジェクトの目的と機能仕様
- **E2Eテスト計画**: `docs/E2_User_Test_Plan.md`
  - ユーザーシナリオテストの手順
- **メインREADME**: `README.md`
  - プロジェクト概要と制約事項

---

## よくある質問

### Q1: ローカルPCにPythonやNode.jsをインストールする必要はありますか？

**A:** いいえ、必要ありません。全ての実行環境はDockerコンテナ内で完結します。ローカルPCの環境を汚さない方針です。

### Q2: LLM機能を使わずに開発できますか？

**A:** はい、できます。`.env` ファイルで `ANALYSIS_USE_LLM=0` に設定すれば、LLM機能なしで動作します。統計情報の算出のみが実行されます。

### Q3: VSCodeでデバッグはできますか？

**A:** FastAPIのデバッグはDockerコンテナ内で実行されるため、通常のVSCodeデバッガは使えません。代わりにログ出力や `pdb` を使ったデバッグを推奨します。または、`docker-compose.yml` でデバッグポートを公開する設定を追加する必要があります。

### Q4: テストは毎回テスト用DBを起動する必要がありますか？

**A:** はい、開発用DBとテスト用DBを分離することで、開発中のデータが消えないようにしています。テスト終了後は `down -v` でクリーンアップしてください。

### Q5: Dockerイメージのサイズが大きいのですが問題ないですか？

**A:** PoCのため最適化は行っていません。本番運用時には multi-stage build やイメージの最適化を検討してください。

---

## 困ったときは

1. まずログを確認: `docker compose logs`
2. サービスを再起動: `docker compose restart`
3. それでもダメならクリーンビルド: `docker compose down -v && docker compose up -d --build`
4. チームメンバーやドキュメントに相談

---

**最終更新日**: 2026-01-12
**対象バージョン**: Prism PoC v0.0.1
