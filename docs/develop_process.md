# Prism PoC 実装タスクチェックリスト

（2026/01/06 更新）
## 開発方針：ローカル環境を汚さない（テストはコンテナ内で完結）

本プロジェクトは Windows11 + Docker Desktop を前提とし、ローカルPCのPython環境（グローバル/venv）を汚さない方針とする。

- Python依存関係の導入・更新は backend コンテナ内でのみ行う
- テスト（pytest等）は backend コンテナ内でのみ実行する
- CI も「コンテナで実行するテスト手順」を基準に整備し、ローカル/CIで結果がズレないようにする

目的：
- 環境差分による不具合（依存関係・バージョン差異）を最小化する
- 参画者が増えても再現性の高い開発手順を維持する


## フェーズA：PoCを「操作可能」にする必須タスク

### A-0. 品質・土台（先に整備）

* [x] A-0-1. CORS を設定
    * [x] 例：`http://localhost:3001` を許可
    * [x] 許可オリジンは環境変数で切替できるようにする
* [x] A-0-2. テスト基盤を追加
    * [x] `pytest` / FastAPI TestClient
    * [x] カバレッジ計測（80%以上を維持）
    * [x] テストは backend コンテナ内で実行する（ローカルPCへpytest等を導入しない）

* [x] A-0-3. CI を追加
    * [x] Backend：テスト + coverage 80%以上
    * [x] Frontend：build を実行
* [x] A-0-4. Alembic 方針決定
    * [x] Alembic を導入し、起動時 `create_all` 依存を解消する方針を決める
    * [x] フェーズAでは「方針決定」まででも可（導入作業はフェーズBに寄せても良い）

#### A-0-4. Alembic 方針決定（決定事項）

- DBスキーマ管理は Alembic を正式採用する。
- フェーズAでは Alembic を導入せず、フェーズB-0で初期マイグレーションを作成する。
- フェーズB-0以降は Alembic を DB スキーマ管理の唯一の正とする。
- それに伴い、起動時の `Base.metadata.create_all(...)` は B-0 完了時に削除し、
  DB 作成・更新は `alembic upgrade head` に統一する。

---

### A-1. データセット一覧取得 API

* [x] `GET /datasets` エンドポイントを実装
* [x] `datasets` テーブルから一覧取得
* [x] 各 dataset について以下を返却

  * [x] dataset_id
  * [x] filename
  * [x] created_at
  * [x] 行数（`dataset_rows` の COUNT）
* [x] レスポンス形式を JSON として確定
* [x] Swagger（/docs）で確認
* [x] ユニットテストを追加（正常系：0件/複数件、行数COUNTが返ること）

---

### A-2. データセット詳細取得 API

* [x] `GET /datasets/{dataset_id}` を実装
* [x] 指定 dataset_id の存在チェック
* [x] 以下の情報を返却

  * [x] メタ情報（filename / created_at）
  * [x] 行数
  * [x] JSONB データのサンプル（先頭 N 行）
* [x] サンプル件数を固定値（例：10件）にする
* [x] エラー時のレスポンスを定義（404 等）
* [x] ユニットテストを追加（正常系、異常系：存在しないIDで404）

---

### A-3. フロントエンド：CSVアップロード機能

* [x] CSVアップロード用画面を作成
* [x] `<input type="file">` を配置
* [x] `POST /datasets/upload` を呼び出す処理を実装
* [x] 成功時レスポンス（dataset_id / 行数）を画面表示
* [x] エラー時の最低限の表示（alert 等）
* [x] ユニットテストを追加（少なくともAPI呼び出し処理を関数化してテスト）

#### A-3. フロントエンドテスト方針（決定事項）

- A-3実施時点で、フロントのユニットテスト基盤を**最小構成で導入**する（例：Vitest）。
- 対象はまず「API呼び出し処理」を関数化した部分とし、HTTPリクエストの成功/失敗時の整形・例外処理をテストする。
- テスト拡張（レンダリングテスト等）はフェーズC-0で実施範囲を再検討する。

---

## フェーズB：分析 PoC としての中核機能

### B-0. 品質・土台（分析機能の前に）

* [x] Alembic を導入し、初期マイグレーションを作成（`datasets` / `dataset_rows`）
* [x] 起動時の `create_all` を削除（DBスキーマはマイグレーションで管理）
* [x] CI にマイグレーション適用（例：テストDBに `alembic upgrade head`）を組み込む

#### B-0 補足：開発用DBとテスト用DBを分離する（推奨）

pytest はテストの独立性のため、テスト後に対象テーブルを TRUNCATE します。
開発用DBのデータ永続化（本番相当データでの検証）と両立するため、Composeプロジェクト名を分けてテスト専用DBを使います。

```bash
# テスト用DBを起動（開発用とは別のボリューム/ネットワーク）
docker compose -p prism2-test up -d db

# スキーマ適用（entrypointの自動migrationはOFFにして明示的に）
docker compose -p prism2-test run --rm -e RUN_MIGRATIONS=0 backend alembic upgrade head

# テスト実行
docker compose -p prism2-test run --rm -e RUN_MIGRATIONS=0 backend pytest

# 片付け（テスト用DBだけ破棄）
docker compose -p prism2-test down -v
```

---

### B-1. 最小集計（統計）API

* [x] `GET /datasets/{dataset_id}/stats` を実装
* [x] 対象 dataset の行数を算出
* [x] JSONB からカラム一覧を抽出
* [x] 数値カラムについて以下を算出（可能な範囲で）

  * [x] min
  * [x] max
  * [x] avg
* [x] 集計結果を JSON で返却
* [x] 計算不可カラムは除外（PoC割り切り）
* [x] 文字列カラムも要約対象に含める（例：案件名）
    * [x] カラムごとに kind（`number` / `string` / `mixed` / `empty`）を返す
    * [x] `string` / `mixed` は上位頻出値（top values）を返す
* [x] ユニットテストを追加（数値/非数値/欠損の混在を含む最低限のパターン）

#### B-1 レスポンス例（参考）

以下は `GET /datasets/{dataset_id}/stats` のレスポンス例です（例示のため一部省略）。

```json
{
  "dataset_id": 1,
  "rows": 4,
  "columns": [
    {
      "name": "project",
      "kind": "string",
      "present_count": 4,
      "non_empty_count": 3,
      "numeric": null,
      "top_values": [
        { "value": "案件A", "count": 2 },
        { "value": "案件B", "count": 1 }
      ]
    },
    {
      "name": "amount",
      "kind": "number",
      "present_count": 4,
      "non_empty_count": 3,
      "numeric": { "count": 3, "min": 100.0, "max": 300.0, "avg": 200.0 },
      "top_values": null
    },
    {
      "name": "mixed",
      "kind": "mixed",
      "present_count": 4,
      "non_empty_count": 4,
      "numeric": { "count": 3, "min": 1.0, "max": 3.0, "avg": 2.0 },
      "top_values": [{ "value": "x", "count": 1 }]
    },
    {
      "name": "empty",
      "kind": "empty",
      "present_count": 4,
      "non_empty_count": 0,
      "numeric": null,
      "top_values": null
    }
  ]
}
```

---

### B-2. LLM 簡易分析 API

* [ ] 集計結果（B-1）を入力とする処理を実装
* [ ] LLM 用プロンプトをコード内に定義
* [ ] 「注目点 / 仮説」をテキスト生成
* [ ] `GET /datasets/{dataset_id}/analysis` 等で提供
* [ ] 出力は保存せず都度生成（PoC割り切り）
* [ ] ユニットテストを追加（LLM呼び出しはスタブ/モックし、プロンプト組み立てとレスポンス整形を検証）

---

## フェーズC：管理画面として最低限成立させる

### C-0. 品質・土台（画面機能の前に）

* [ ] フロントのCIを整備（`npm ci` → `npm run build`）
* [ ] フロントの簡易テスト導入（最低限のレンダリング/ロジックのテスト。テスト方式はここで確定）

---

### C-1. データセット一覧画面

* [ ] 起動時に `GET /datasets` を呼び出す
* [ ] データセット一覧をテーブル表示
* [ ] dataset_id をクリック可能にする
* [ ] 選択時に詳細画面へ遷移
* [ ] ユニットテストを追加（一覧表示・エラー表示の最低限）

---

### C-2. データセット詳細・分析画面

* [ ] 詳細 API（A-2）の結果を表示
* [ ] 集計 API（B-1）の結果を表示
* [ ] LLM 分析結果（B-2）を表示
* [ ] レイアウトは最小限（装飾不要）
* [ ] ユニットテストを追加（詳細取得失敗時の表示、主要コンポーネントが落ちないこと）

---

### C-3. 簡易グラフ表示（任意）

* [ ] グラフライブラリを 1 つ選定
* [ ] 件数 or 数値分布を 1 種類表示
* [ ] 見た目より「動くこと」を優先

---

## フェーズD：安定性・PoC品質の底上げ（後回し可）

* [ ] CSV の文字コードエラー対策（UTF-8前提明示）
* [ ] 空 CSV / 不正 CSV のエラーハンドリング
* [ ] Backend ログの粒度整理
* [ ] README に「PoCでやらないこと」を再明示

---

## PoC完了チェック（Done 定義との照合）

* [ ] CSV をブラウザからアップロードできる
* [ ] PostgreSQL にデータが格納される
* [ ] 集計結果を API で取得できる
* [ ] LLM の分析コメントが生成される
* [ ] すべてを画面上で確認できる

---