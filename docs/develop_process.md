# Prism PoC 実装タスクチェックリスト

（2026/01/09 更新）

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

# backend のソースを変更している場合は、テスト前に必ず再ビルドする（COPY型のため）
# ※ build を省略すると「古いイメージ」でpytestが走り、結果（テスト数/カバレッジ）がズレます
docker compose -p prism2-test build backend

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

目的：B-1 の集計結果を入力として、LLM で「注目点 / 仮説」を生成し API で返す（PoC割り切りで保存しない）。

#### B-2 方針（決めること）

* [x] 利用する LLM の方式を決定（**Gemini API** を利用）
* [ ] 機密/個人情報の扱い方針を決定
  * [ ] 原則：**行データは送らない**（B-1 stats など要約のみ送る）
  * [ ] カラム名/頻出値に機微が含まれる可能性があるため、送信前にマスク/制限するかを決める
* [x] タイムアウト/失敗時の API 方針を決定（例：503/504、リトライ有無）
* [ ] コスト/速度の上限を決める（例：最大トークン、stats の入力サイズ上限）

#### B-2-0. 最小の土台（LLM なしで形を固める）

* [x] `GET /datasets/{dataset_id}/analysis` を追加
* [x] 内部で B-1 の集計結果を取得できるようにする（処理の共有/再利用）
* [x] 返却 JSON の形を確定（例：`dataset_id` / `generated_at` / `analysis_text`）
* [x] まずは固定文言 + stats の要点だけでレスポンスが返る（LLM未接続でもUIが作れる状態）
* [x] ユニットテスト：正常系（存在する dataset_id）、異常系（存在しない dataset_id は 404）

#### B-2-1. LLM クライアントの抽象化（テスト容易性）

* [x] LLM 呼び出しをラップするインターフェースを作る（実装差し替え可能に）
* [x] 環境変数で API Key / モデル名 / タイムアウト等を切替できるようにする
* [x] ユニットテスト：LLM 部分はスタブ/モックで差し替え可能であること

#### B-2-2. プロンプト v1（品質より再現性を優先）

* [x] プロンプトをコード内に定義（テンプレート化）
* [x] 出力フォーマットを指示（見出し付き箇条書き、過度な断定を避ける、前提と限界を明記）
* [x] stats の入力を必要最小限に圧縮（列一覧/数値統計/上位頻出値など）
* [x] ユニットテスト：プロンプト組み立てが期待通り（stats が埋め込まれる、サイズ上限が効く）

補足（初期パラメータ / v1 方針）：

- **max_columns=30**
- **max_top_values_per_column=3**
- **max_prompt_chars=9000**
- サイズ上限超過時は段階的に省略（まず top_values を落とす → 列数を絞る → 最低限の概要に落とす）

#### B-2-3. エラーハンドリング（PoCでも最低限）

* [x] LLM 失敗時の扱いを実装（タイムアウト、認証エラー、上限超過など）
* [x] API レスポンス（ステータス/メッセージ）を確定
* [x] ユニットテスト：LLM 例外時に期待ステータス/レスポンスになる

#### B-2-4. 代表 CSV での手動評価（品質チューニングの入口）

* [x] 代表データ（想定利用に近い CSV）で B-1 stats → B-2 出力を確認し、改善点をメモする
  * 例：Playwright スクレイピング結果の列を含む CSV
  * 注意：**機密/個人情報が含まれる場合はコミットしない**（匿名化したサンプルのみリポジトリに入れる）
  * 代表CSVの置き場所：`samples/playwright_scrape_sample.csv`（必要に応じて更新）
  * 手順（最小）：
    * [x] CSV をアップロードして dataset_id を得る
    * [x] `GET /datasets/{dataset_id}/stats` を確認（入力が想定通りか）
    * [x] `GET /datasets/{dataset_id}/analysis` を確認（出力の妥当性/言い回し/過度な断定がないか）
    * [x] 改善点をメモし、B-2-2 のプロンプトと B-2-3 のエラーハンドリングへ反映する

メモ（代表CSVでの確認結果 / 改善点）：

- `CategoryText` の上位値に不自然な空白混入（例：`IT・通信・インターネ ット`）が見られた。
  - 対応案：CSV取り込み時または集計前に、連続空白の圧縮・全角/半角スペース正規化を検討。
- LLM出力の見出しが崩れるケース（例：`## 前 提・限界` のようにスペースが混入）が見られた。
  - 対応案：プロンプトに「見出しはスペースを入れず、指定の文言を完全一致で出力」と追記することを検討。

#### B-2-5. 実LLMプロバイダ導入（Gemini）＋疎通確認

目的：`GET /datasets/{dataset_id}/analysis` が **実際に Gemini API を呼び出して**分析テキストを返せる状態にする（PoC割り切りで保存しない）。

* [x] Gemini の利用方式を確定（**Google AI Studio（API Key方式）** を利用）
* [x] 利用モデル名を確定（デフォルト：`gemini-1.5-flash`、必要に応じて変更）
* [x] Backend に Gemini クライアント実装を追加（`LLM_PROVIDER=gemini` で選択できるように）
* [x] Backend の環境変数を確定・Compose に反映（例：`LLM_PROVIDER` / `LLM_API_KEY` / `LLM_MODEL` / `LLM_TIMEOUT_SECONDS`）
  * [x] **APIキーはコミットしない**（`.env` / CI secret / ローカル設定で注入）
  * [x] ローカル用サンプル：`docs/env.example` をリポジトリルートの `.env` にコピーして編集する
* [x] 動作確認手順を確定（コンテナ内で実行）
  * [x] `ANALYSIS_USE_LLM=1` を有効化して `/analysis` を叩く
  * [x] 代表CSVで `stats → analysis` が一連で動くことを確認（必要なら B-2-4 と統合してOK）
* [ ] 失敗時の挙動が B-2-3 の仕様どおりであることを確認（タイムアウト/認証/上限など）
* [x] テスト方針を確定（ユニットテストはモック継続、疎通は手動/任意のintegrationに分離）

#### B-2 Done（最小）

* [x] `GET /datasets/{dataset_id}/analysis` が Swagger で確認できる
* [x] stats を入力にしたテキストが返り、失敗時の挙動（ステータス/メッセージ）が決まっている
* [x] テストがあり、LLM 呼び出し部分はモックで検証できる

---

## フェーズC：管理画面として最低限成立させる

### C-0. 品質・土台（画面機能の前に）

* [x] フロントのCIを整備（`npm ci` → `npm run build`）
* [x] フロントの簡易テスト導入（最低限のレンダリング/ロジックのテスト。テスト方式はここで確定）

#### C-0 決定事項（テスト方式メモ）

- ユニットテストは **Vitest** を採用し、`frontend` で `npm test`（=`vitest run`）として実行する。
- 当面の対象は **ロジック/API呼び出し（例：`src/api/*`）** を優先する（ブラウザ依存はモック/スタブで吸収）。
- CI では `frontend-build` ジョブで `npm ci` → `npm test` → `npm run build` を実行し、失敗時はPRを落とす。
- Reactコンポーネントのレンダリングテスト（Testing Library / jsdom 等）は、C-1/C-2の画面実装が進んだ段階で必要最小限を追加する。

---

### C-1. データセット一覧画面

* [x] 起動時に `GET /datasets` を呼び出す
* [x] データセット一覧をテーブル表示
* [x] dataset_id をクリック可能にする
* [x] 選択時に詳細画面へ遷移
* [x] ユニットテストを追加（一覧表示・エラー表示の最低限）

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
