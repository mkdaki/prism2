# Prism PoC 実装タスクチェックリスト

（最終更新：2026/01/12）

**重要な変更（2026/01/12）**:
- フェーズE-0「推移比較機能の実装」を追加
- この機能はPrismの最重要機能（キラー機能）であり、E2実ユーザーテストの前提条件
- E2, E3, E4の内容を自社テスト中心に修正（外部ユーザーテスト不要）
- 詳細は `docs/E2_User_Test_Plan.md` を参照

## 開発方針：ローカル環境を汚さない（テストはコンテナ内で完結）

本プロジェクトは Windows11 + Docker Desktop を前提とし、ローカルPCのPython環境（グローバル/venv）を汚さない方針とする。

- Python依存関係の導入・更新は backend コンテナ内でのみ行う
- テスト（pytest等）は backend コンテナ内でのみ実行する
- CI も「コンテナで実行するテスト手順」を基準に整備し、ローカル/CIで結果がズレないようにする

目的：

- 環境差分による不具合（依存関係・バージョン差異）を最小化する
- 参画者が増えても再現性の高い開発手順を維持する

---

## 実装時の必須確認事項（2026/01/16追加）

新機能実装時は、推測ではなく確認を優先する。特にデータベースモデルやAPIのような基盤部分は必ず既存定義を確認すること。

**重要**: 以下は毎回の実装時に確認すべき事項であり、一度確認したら終わりではない。

### 実装前の必須確認（コード生成前に毎回実施）

1. **モデル定義の確認**: 使用するテーブル・カラムの実際の定義を `backend/app/models.py` で確認
2. **既存パターンの確認**: 類似機能の既存コードを grep 検索して実装パターンを確認
   ```bash
   # 例: DatasetRow のカラム名を確認
   grep -r "DatasetRow\." backend/app/
   ```
3. **命名規則の確認**: プロジェクト内の命名規則（キャメルケース、スネークケースなど）を既存コードから確認

### 実装中の確認

1. **型の整合性**: モデル定義と実装コードで型が一致しているか
2. **既存APIとの整合性**: 新しいエンドポイントが既存の設計パターンに従っているか

### よくあるミス事例と対策

**ミス事例1**: データベースカラム名の推測
```python
# ❌ 間違い（推測）
select(DatasetRow.jsonb)  # JSONBカラムだから "jsonb" だろう

# ✅ 正しい（models.py で確認済み）
select(DatasetRow.data)   # 実際の定義は "data"
```

**対策**: 実装前に必ず `backend/app/models.py` を確認する

**ミス事例2**: 既存パターンを無視した実装
```python
# 既存コードに同じパターンがあるのに、別の方法で実装してしまう
```

**対策**: `grep` で既存の類似コードを検索し、パターンを踏襲する

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
* [x] 失敗時の挙動が B-2-3 の仕様どおりであることを確認（タイムアウト/認証/上限など）
* [x] テスト方針を確定（ユニットテストはモック継続、疎通は手動/任意のintegrationに分離）

#### B-2-5 確認結果（2026/01/10）

**テスト実行結果:**
- 全29テスト通過（test_gemini_client.py 8件、test_dataset_analysis.py 4件を含む）
- カバレッジ: 89.55%（目標80%以上を達成）

**確認済みエラーハンドリング:**

1. **LLMエラークラス定義** (`app/llm.py`)
   - `LLMTimeoutError` → 504 Gateway Timeout (retryable)
   - `LLMAuthError` → 503 Service Unavailable (non-retryable)
   - `LLMRateLimitError` → 503 Service Unavailable (retryable)
   - `LLMInputTooLargeError` → 413 Payload Too Large (non-retryable)
   - `LLMProviderError` → 502 Bad Gateway (retryable)

2. **Geminiクライアントでのマッピング** (`app/llm.py` lines 140-198)
   - HTTP 401/403 → `LLMAuthError`
   - HTTP 429 → `LLMRateLimitError`
   - HTTP 413 / 400(message含む) → `LLMInputTooLargeError`
   - HTTP 500-599 → `LLMProviderError`
   - `httpx.TimeoutException` → `LLMTimeoutError`

3. **APIエンドポイントでのエラーレスポンス** (`app/main.py` lines 279-304)
   - エラーレスポンス形式: `{"error": {"code": "...", "message": "...", "retryable": true/false}}`
   - 各LLMエラーが適切なHTTPステータスにマップされることを確認

**テスト実行手順:**
```bash
# テスト用DBを起動
docker compose -p prism2-test up -d db

# Backendをビルド
docker compose -p prism2-test build backend

# スキーマ適用
docker compose -p prism2-test run --rm -e RUN_MIGRATIONS=0 backend alembic upgrade head

# テスト実行
docker compose -p prism2-test run --rm -e RUN_MIGRATIONS=0 backend pytest -v --cov=app

# クリーンアップ
docker compose -p prism2-test down -v
```

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

* [x] 詳細 API（A-2）の結果を表示
* [x] 集計 API（B-1）の結果を表示
* [x] LLM 分析結果（B-2）を表示
* [x] レイアウトは最小限（装飾不要）
* [x] ユニットテストを追加（詳細取得失敗時の表示、主要コンポーネントが落ちないこと）

#### C-2 実装内容（完了）

- `frontend/src/api/datasets.ts` に3つのAPI型定義と関数を追加
  - `getDatasetDetail(datasetId)` - データセット詳細取得
  - `getDatasetStats(datasetId)` - 統計情報取得
  - `getDatasetAnalysis(datasetId)` - 分析結果取得
- `frontend/src/pages/DatasetDetailPage.tsx` を実装
  - 3つのAPIを並行で呼び出し（Promise.all）
  - メタ情報セクション（ファイル名、作成日時、行数）
  - サンプルデータテーブル（先頭10行）
  - 統計情報セクション（カラムごとの集計結果、kind別の色分け）
  - LLM分析結果セクション（テキスト表示）
  - ローディング状態とエラーハンドリング
- `frontend/src/api/datasets.test.ts` にテストを追加
  - 各API関数の正常系テスト
  - 404エラー時のテスト
  - LLMエラー時のテスト
- 動作確認（実データでの表示確認）
  - フロントエンドテスト: 12件すべて通過
  - APIエンドポイント疎通確認: 詳細/統計/分析すべて正常動作

---

### C-3. 簡易グラフ表示（任意）

* [x] グラフライブラリを 1 つ選定
* [x] 件数 or 数値分布を 1 種類表示
* [x] 見た目より「動くこと」を優先

#### C-3 実装内容（完了）

- **グラフライブラリ選定: Recharts v2.13.3**
  - 選定理由: React専用、シンプルなAPI、TypeScript対応、軽量、ドキュメント充実
  
- **実装内容:**
  - 数値カラム（kind="number"）の統計グラフ
    - 最小値、平均値、最大値を棒グラフで表示
    - 青色（#2196f3）のバーで視覚化
  - 文字列カラム（kind="string" or "mixed"）の頻出値グラフ
    - 上位頻出値を棒グラフで表示
    - 緑色（#4caf50）のバーで視覚化
  - ResponsiveContainer でレスポンシブ対応
  - ツールチップ、凡例、グリッド線を実装

- **動作確認:**
  - フロントエンドテスト: 12件すべて通過
  - コンパイルエラー: なし
  - 確認URL:
    - シンプルデータ: http://localhost:3001/datasets/5
    - 大規模データ: http://localhost:3001/datasets/3

---

## フェーズD：安定性・PoC品質の底上げ（後回し可）

* [x] CSV の文字コードエラー対策（UTF-8前提明示）
* [x] 空 CSV / 不正 CSV のエラーハンドリング
* [x] Backend ログの粒度整理
* [x] README に「PoCでやらないこと」を再明示

### D-1. CSV文字コードエラー対策（完了）

**実装内容:**
- UTF-8とShift_JIS（CP932）の自動検出と変換を追加
- フロントエンドに対応エンコーディングの注意書きを表示
- エラーメッセージを改善（具体的な対処法を提示）

**変更ファイル:**
- `backend/app/main.py`: エンコード自動検出処理を追加
- `frontend/src/pages/UploadPage.tsx`: 対応形式の注意書きを追加

**テスト:**
- `testPostDatasetsUploadAcceptsShiftJis`: Shift_JIS対応を確認

### D-2. 空CSV/不正CSVのエラーハンドリング（完了）

**実装内容:**
- 完全な空ファイルのチェックを追加
- ヘッダー行の検証（カラム名が空でないか）
- エラーメッセージの改善

**変更ファイル:**
- `backend/app/main.py`: バリデーション処理を強化

**テスト:**
- `testPostDatasetsUploadRejectsCompletelyEmptyFile`: 空ファイル拒否を確認
- `testPostDatasetsUploadRejectsEmptyColumnName`: 空カラム名拒否を確認
- `testPostDatasetsUploadRejectsEmptyCsv`: データ行なし拒否を確認（既存）

### D-3. Backendログの粒度整理（完了）

**実装内容:**
- すべてのエンドポイントにリクエスト/レスポンスログを追加
- エラー時のスタックトレース出力（`exc_info=True`）
- LLM呼び出し時のログ追加（成功時の文字数、失敗時の詳細）
- アップロード時のエンコード検出ログ

**変更ファイル:**
- `backend/app/main.py`: ロギング設定と各エンドポイントへのログ追加

**ログ出力例:**
```
2026-01-10 05:21:15 [INFO] prism.backend: POST /datasets/upload - Uploading file: sample.csv
2026-01-10 05:21:15 [INFO] prism.backend: POST /datasets/upload - Detected encoding: utf-8
2026-01-10 05:21:15 [INFO] prism.backend: POST /datasets/upload - Success: dataset_id=1, rows=2, filename=sample.csv
```

### D-4. READMEに「PoCでやらないこと」を再明示（完了）

**実装内容:**
- README.mdに「PoCの範囲と制約」セクションを追加
- 実装済み機能と意図的に実装していない機能を明示
- 本番運用に向けた推奨改善事項を列挙

**追加内容:**
- セキュリティ制約（認証・認可なし等）
- データ永続性・バックアップなし
- パフォーマンス・スケーラビリティの制限
- 運用性の不足（監視、ログローテーションなし等）
- 機密情報・プライバシー対策の不足
- LLM関連の制約（コスト制御、プロンプトインジェクション対策なし等）

**変更ファイル:**
- `README.md`: 約100行の詳細な制約説明を追加

### フェーズD完了確認（2026/01/10）

**テスト実行結果:**
```
全32テスト通過 ✓
カバレッジ: 89.26%（目標80%以上達成）
```

**新規追加テスト（3件）:**
1. `testPostDatasetsUploadRejectsCompletelyEmptyFile` - 空ファイル拒否
2. `testPostDatasetsUploadAcceptsShiftJis` - Shift_JIS対応確認
3. `testPostDatasetsUploadRejectsEmptyColumnName` - 空カラム名拒否

**変更ファイル一覧:**
- Backend: `backend/app/main.py`（エンコード検出、バリデーション、ログ追加）
- Frontend: `frontend/src/pages/UploadPage.tsx`（注意書き追加）
- テスト: `backend/tests/test_datasets_upload.py`（3件追加、1件修正）
- ドキュメント: `README.md`（PoC制約セクション追加）

---

## PoC完了チェック（Done 定義との照合）

* [x] CSV をブラウザからアップロードできる
* [x] PostgreSQL にデータが格納される
* [x] 集計結果を API で取得できる
* [x] LLM の分析コメントが生成される
* [x] すべてを画面上で確認できる

### 確認結果（2026/01/10）

#### 1. 環境起動・アクセス確認 ✓
- Backend: `http://localhost:8001` - 正常動作
- Frontend: `http://localhost:3001` - 正常動作
- Database: PostgreSQL - 正常動作

#### 2. CSV アップロード機能 ✓
- `POST /datasets/upload` でsample.csvをアップロード成功
- レスポンス: `{"dataset_id":5,"rows":2,"filename":"sample.csv"}`

#### 3. PostgreSQL へのデータ格納 ✓
- `datasets` テーブル: dataset_id=5 のレコードが正常に作成
- `dataset_rows` テーブル: 2行のJSONBデータが正常に格納
  - row_index=0: `{"colA": "1", "colB": "hello"}`
  - row_index=1: `{"colA": "2", "colB": "world"}`

#### 4. 集計結果 API ✓
- `GET /datasets` - データセット一覧取得成功（5件のデータセット）
- `GET /datasets/5` - 詳細情報取得成功（メタ情報+サンプルデータ）
- `GET /datasets/5/stats` - 統計情報取得成功
  - colA: 数値型、min=1.0、max=2.0、avg=1.5
  - colB: 文字列型、頻出値="hello"(1件)、"world"(1件)

#### 5. LLM 分析コメント生成 ✓
- `GET /datasets/5/analysis` - 分析結果取得成功（スタブモード）
- 出力形式: 注目点、仮説、追加確認事項、前提・限界の各セクション
- 統計情報を基にした適切な分析コメントが生成されている

#### 6. 画面上での総合確認 ✓
- フロントエンド（React + TypeScript）が正常に起動
- APIエンドポイントとの疎通確認完了
- 以下の画面が実装済み:
  - データセット一覧画面（C-1）
  - データセット詳細・分析画面（C-2）
  - CSVアップロード画面（A-3）

### 結論
**PoC の基本機能はすべて正常に動作しています。**

---

## フェーズE：価値検証（ユーザー視点での評価）

PoCとしての技術実装は完了したため、次は「実際に使えるか」「収益化できるか」を検証するフェーズに移行します。

**重要**: E2実ユーザーテスト（自社テスト）を実施する前に、**推移比較機能（E-0）の実装が必須**です。
この機能こそがPrismの最重要機能であり、価値検証の中心となります。

---

### E-0. 推移比較機能の実装（E2テスト前の必須条件）

**目的**: 同一対象を継続的にスクレイピングした複数のデータセットを比較し、変化・トレンドを自動分析する機能を実装する。

**位置づけ**: この機能はPrismの最重要機能（キラー機能）であり、単発分析との差別化要因、継続利用（サブスク化）の根拠となる。

#### E-0-1. データモデルの拡張

**目的**: データセット間の関連付けを可能にするスキーマ設計

* [x] データセット間の関連を管理するテーブル設計を決定
  * [ ] 案A: `dataset_comparisons` テーブル（comparison_id, base_dataset_id, target_dataset_id, created_at）
  * [ ] 案B: `datasets` テーブルに `parent_dataset_id` を追加（時系列の親子関係）
  * [x] **案C: 比較はAPIレベルのみで、永続化しない（最小実装）** - 採用
  
* [x] 選択した設計の実装
  * [x] データモデルの変更は不要（案Cのため）
  * [x] API実装方針の確定：`GET /datasets/compare?base={dataset_id}&target={dataset_id}` 形式
  * [x] 比較結果はレスポンスとして返すのみ（DB保存なし）

* [x] テスト
  * [x] データモデル変更なしのため、マイグレーション不要
  * [x] 既存のデータセットテーブルをそのまま利用

**決定事項（2026/01/12）**:
- **案Cを採用** - 比較はAPIレベルのみで永続化しない（最小実装）
- **理由**:
  1. PoC段階では「動く」ことが最優先 - 比較履歴の保存は後回しでも問題ない
  2. E2実ユーザーテストの目的は「推移比較機能の価値検証」 - 履歴保存の価値は未検証
  3. 手戻りリスクが低い - 案Cで価値を確認してから、必要なら案Aや案Bに拡張可能
  4. 実装スピードが速い - マイグレーション不要で、すぐにE-0-2に進める
- **実装方針**:
  - データモデルの変更なし
  - API呼び出し時に base と target の dataset_id をクエリパラメータで指定
  - 比較結果はその場で計算してレスポンスとして返す
  - DB には保存しない（将来的に必要なら案Aに拡張可能）

---

#### E-0-2. 推移比較API の実装

**目的**: 2つのデータセットの統計情報を比較し、差分を返すAPIを実装

* [x] `GET /datasets/compare?base={dataset_id}&target={dataset_id}` エンドポイントを実装
  * [x] base（基準データ）とtarget（比較対象データ）の存在チェック
  * [x] 両データセットの stats を取得（B-1の処理を再利用）
  * [x] 統計差分の計算
    * [x] 行数の差分（増減数、増減率）
    * [x] 数値カラムの差分（min/max/avg の変化）
    * [x] 文字列カラムの差分（頻出値の変化、新規/消失カテゴリ）
  
* [x] レスポンス形式を確定
  * [x] `base_dataset`（メタ情報）
  * [x] `target_dataset`（メタ情報）
  * [x] `comparison`（差分サマリー）
    * [x] `rows_change`（行数の変化）
    * [x] `columns_change`（カラムごとの変化）
  
* [x] エラーハンドリング
  * [x] データセットが存在しない場合：404
  * [x] カラム構成が大きく異なる場合：警告なしで差分表現（案Cの方針）
  * [x] 同じデータセットを指定した場合：400 Bad Request

* [x] ユニットテスト
  * [x] 正常系：2つのデータセット比較が成功
  * [x] 異常系：存在しないIDで404（base/target それぞれ）
  * [x] 異常系：同一ID指定で400
  * [x] エッジケース：カラム構成が異なる場合の挙動

**レスポンス例（参考）**:
```json
{
  "base_dataset": {
    "dataset_id": 1,
    "filename": "real_estate_2026-01-01.csv",
    "created_at": "2026-01-01T00:00:00Z",
    "rows": 100
  },
  "target_dataset": {
    "dataset_id": 2,
    "filename": "real_estate_2026-01-08.csv",
    "created_at": "2026-01-08T00:00:00Z",
    "rows": 105
  },
  "comparison": {
    "rows_change": {
      "base": 100,
      "target": 105,
      "diff": 5,
      "percent": 5.0
    },
    "columns_change": [
      {
        "name": "price",
        "kind": "number",
        "base": {"min": 1000, "max": 5000, "avg": 3000},
        "target": {"min": 1100, "max": 5200, "avg": 3150},
        "diff": {"min": 100, "max": 200, "avg": 150}
      }
    ]
  }
}
```

#### E-0-2 実装内容（完了 - 2026/01/12）

**変更ファイル**:
- `backend/app/analysis.py` - `calculate_stats_diff()` 関数を追加（差分計算ロジック）
- `backend/app/main.py` - `GET /datasets/compare` エンドポイントを追加
  - 注意：FastAPIのルーティング順序が重要。`/datasets/compare` を `/datasets/{dataset_id}` より前に配置
- `backend/tests/test_dataset_compare.py` - 新規作成（テスト5件）

**テスト結果**:
- 全37テスト通過（新規5件を含む）
- カバレッジ: 90.04%（目標80%以上達成）

**実装した機能**:
1. 2つのデータセットの統計情報を比較するAPI
2. 行数の差分計算（件数、増減率）
3. 数値カラムの差分計算（min/max/avg の変化）
4. カラム構成が異なる場合の対応（和集合で比較）
5. エラーハンドリング（404/400）

**新規追加テスト**:
1. `testGetDatasetCompareSuccess` - 正常系
2. `testGetDatasetCompareReturns404ForMissingBase` - base が存在しない
3. `testGetDatasetCompareReturns404ForMissingTarget` - target が存在しない
4. `testGetDatasetCompareReturns400ForSameId` - 同一ID指定
5. `testGetDatasetCompareWithDifferentColumns` - カラム構成が異なる場合

---

#### E-0-3. LLM推移分析の実装

**目的**: 2つのデータセットの差分を入力として、LLMに「変化の要点」を分析させる

* [x] `GET /datasets/compare/analysis?base={dataset_id}&target={dataset_id}` エンドポイントを実装
  * [x] E-0-2 の比較結果を取得
  * [x] 推移分析用プロンプト（v1）を作成
    * [x] 基準データと比較対象データのメタ情報
    * [x] 統計差分（行数、数値カラムの変化、カテゴリの変化）
    * [x] 出力フォーマット指示（見出し：変化の概要、注目すべき変化、トレンド分析、前提・限界）
  
* [x] LLMクライアントで推移分析を実行
  * [x] B-2の実装を拡張（推移分析用プロンプトを追加）
  * [x] タイムアウト・エラーハンドリングは B-2 と同様
  
* [x] レスポンス形式を確定
  * [x] `base_dataset` / `target_dataset`（メタ情報）
  * [x] `comparison_summary`（差分サマリー）
  * [x] `analysis_text`（LLM生成テキスト）
  * [x] `generated_at`（生成日時）

* [x] プロンプト調整（品質改善）
  * [x] 代表データで手動評価（フェーズE-0-4で実施予定）
  * [x] 過度な断定を避ける指示
  * [x] 数値の変化率を具体的に指摘させる

* [x] ユニットテスト
  * [x] 正常系：LLMが推移分析テキストを返す
  * [x] LLM失敗時のエラーハンドリング
  * [x] プロンプトに差分情報が正しく埋め込まれること

**プロンプト例（v1草案）**:
```
あなたはデータアナリストです。以下の2つのデータセットの統計差分を分析し、
変化の要点を簡潔に報告してください。

【基準データ】
ファイル名: {base_filename}
作成日時: {base_created_at}
行数: {base_rows}

【比較対象データ】
ファイル名: {target_filename}
作成日時: {target_created_at}
行数: {target_rows}

【統計差分】
- 行数: {base_rows} → {target_rows} ({diff_percent}%変化)
- price（数値）: 平均 {base_avg} → {target_avg} ({diff_avg}変化)
- category（文字列）: 頻出値の変化 [...]

【出力フォーマット】
## 変化の概要
## 注目すべき変化
## トレンド分析
## 前提・限界
```

#### E-0-3 実装内容（完了 - 2026/01/12）

**変更ファイル**:
- `backend/app/analysis.py` - 推移分析用関数を追加
  - `build_comparison_prompt_v1()` - LLM用プロンプト生成
  - `generate_comparison_template_analysis()` - テンプレート分析（LLM無効時）
  - `generate_comparison_analysis_text()` - LLM推移分析テキスト生成
- `backend/app/main.py` - `GET /datasets/compare/analysis` エンドポイントを追加
  - 注意：`/datasets/compare/analysis` を `/datasets/compare` より前に配置（ルーティング順序）
- `backend/tests/test_comparison_analysis.py` - 新規作成（テスト7件）

**テスト結果**:
- 全44テスト通過（新規7件を含む）
- カバレッジ: 90.36%（目標80%以上達成）

**実装した機能**:
1. 2つのデータセットの差分を入力としたLLM推移分析
2. 推移分析用プロンプト（v1）の実装
   - メタ情報（ファイル名、作成日時、行数）の埋め込み
   - 統計差分の整形（行数変化、数値カラムの変化）
   - 出力フォーマット指示（4セクション構成）
3. テンプレート分析（LLM無効時のフォールバック）
4. エラーハンドリング（B-2と同様：504/503/413/502/404/400）
5. significant_changes の抽出（平均値が変化した数値カラム）

**新規追加テスト**:
1. `testGetComparisonAnalysisWithLlmDisabled` - LLM無効時のテンプレート分析
2. `testGetComparisonAnalysisWithLlmEnabled` - LLM有効時の推移分析（モック）
3. `testGetComparisonAnalysisReturns404ForMissingBase` - base が存在しない
4. `testGetComparisonAnalysisReturns404ForMissingTarget` - target が存在しない
5. `testGetComparisonAnalysisReturns400ForSameId` - 同一ID指定
6. `testGetComparisonAnalysisHandlesLlmTimeout` - LLMタイムアウト時のエラー
7. `testGetComparisonAnalysisHandlesLlmAuthError` - LLM認証エラー時のエラー

**プロンプト設計のポイント**:
- 統計差分を人間が読みやすい形式で整形
- 数値変化は絶対値と変化率の両方を表示
- 制約として「過度な断定を避ける」「推測は推測と明記する」を明示
- 出力フォーマットを厳格に指定（4セクション構成）

---

#### E-0-4. フロントエンド実装

**目的**: ユーザーが2つのデータセットを選択し、推移比較結果を閲覧できるUIを実装

* [x] データセット一覧画面（DatasetListPage.tsx）の拡張
  * [x] 各データセット行にチェックボックスを追加
  * [x] 2つのデータセットを選択した状態を管理（useState）
  * [x] 「推移比較を実行」ボタンを追加
  * [x] ボタンクリック時に比較ページへ遷移

* [x] 推移比較画面（DatasetComparePage.tsx）の新規作成
  * [x] `GET /datasets/compare` API 呼び出し
  * [x] `GET /datasets/compare/analysis` API 呼び出し
  * [x] レイアウト設計
    * [x] セクション1: 基準データと比較対象データのメタ情報（横並び）
    * [x] セクション2: 統計差分の表示（行数変化、カラムごとの変化）
    * [x] セクション3: LLM推移分析結果の表示
  * [x] ローディング状態とエラーハンドリング

* [x] API関数の追加（`frontend/src/api/datasets.ts`）
  * [x] `compareDatasets(baseId, targetId)`
  * [x] `getComparisonAnalysis(baseId, targetId)`

* [x] ルーティングの追加（React Router）
  * [x] `/datasets/compare?base={id}&target={id}` パスを追加

* [x] UIの調整
  * [x] 差分の可視化（増加は緑、減少は赤など）
  * [x] 変化率のハイライト表示

* [x] ユニットテスト
  * [x] API関数のテスト（正常系、エラー系）
  * [x] 合計18テストすべて通過

#### E-0-4 実装内容（完了 - 2026/01/13）

**変更ファイル**:
- `frontend/src/api/datasets.ts` - 型定義とAPI関数を追加
  - `DatasetComparisonResponse` 型
  - `ComparisonAnalysisResponse` 型
  - `compareDatasets(baseId, targetId)` 関数
  - `getComparisonAnalysis(baseId, targetId)` 関数
- `frontend/src/api/datasets.test.ts` - テスト6件を追加（合計18テスト）
- `frontend/src/pages/DatasetListPage.tsx` - チェックボックスと比較ボタンを追加
  - `selectedIds` 状態管理（最大2つまで選択可能）
  - `handleCheckboxChange` 関数
  - `handleCompare` 関数（比較ページへ遷移）
- `frontend/src/pages/DatasetComparePage.tsx` - 新規作成
  - URLパラメータから base と target のIDを取得
  - 2つのAPIを並行呼び出し（Promise.all）
  - 3セクション構成の実装
- `frontend/src/App.tsx` - ルーティング追加
  - `/datasets/compare` パスを追加

**テスト結果**:
- フロントエンドユニットテスト: 18件すべて通過 ✓
- ビルド: 成功 ✓
- Lintエラー: なし ✓

**実装した機能**:
1. データセット一覧画面のチェックボックス（2つまで選択可能）
2. 「推移比較を実行 (0/2)」ボタン（2つ選択時に有効化）
3. 推移比較画面の実装
   - セクション1: 基準データと比較対象データのメタ情報（色分け表示）
   - セクション2: 統計差分（行数変化、カラムごとの変化、増減の色分け）
   - セクション3: LLM推移分析結果
4. エラーハンドリングとローディング状態の表示

**注意事項（開発環境）**:
- Dockerコンテナの再ビルドが必要: `docker compose build --no-cache frontend`
- フロントエンドのソースコード変更時はコンテナの再起動が必要（E-5-1で改善予定）
- ブラウザのハードリロード（`Ctrl + Shift + R`）が必要な場合あり

---

#### E-0-5. テスト（unit/integration）

**目的**: 推移比較機能が期待通り動作することを確認

* [x] Backend ユニットテスト
  * [x] 比較API（E-0-2）のテスト追加
    * [x] `test_dataset_compare.py` - 5テスト追加
    * [x] 正常系、異常系、エッジケース
  * [x] LLM推移分析API（E-0-3）のテスト追加
    * [x] `test_comparison_analysis.py` - 7テスト追加
    * [x] LLMモック時の挙動確認

* [x] Frontend ユニットテスト
  * [x] API関数のテスト（`datasets.test.ts` に追加）
  * [x] `compareDatasets` のテスト3件
  * [x] `getComparisonAnalysis` のテスト3件

* [x] Integration テスト（手動）
  * [x] 2つのCSVをアップロード
  * [x] 推移比較APIを実行し、差分が正しく計算されることを確認
  * [x] LLM推移分析を実行し、妥当な分析テキストが返ることを確認
  * [x] フロントエンドで一連の操作が正常に動作することを確認

* [x] カバレッジ確認
  * [x] Backend カバレッジ 90.36%（目標80%以上達成）
  * [x] Frontend テスト 18件すべて通過

#### E-0-5 テスト結果（完了 - 2026/01/13）

**Backend テスト結果**:
- 全44テスト通過 ✓
- カバレッジ: 90.36%（目標80%以上達成）
- 新規追加テスト: 12件（E-0-2で5件、E-0-3で7件）

**Frontend テスト結果**:
- 全18テスト通過 ✓
- 新規追加テスト: 6件（`compareDatasets` 3件、`getComparisonAnalysis` 3件）

**Integration テスト結果**:

*テストデータ*:
- base: `test_base_2026-01-01.csv`（10件、電化製品の在庫データ）
- target: `test_target_2026-01-08.csv`（11件、1週間後のデータ）

*テスト手順*:
1. 2つのCSVをcurlコマンドでアップロード
   ```bash
   curl -X POST -F "file=@test_base_2026-01-01.csv" http://localhost:8001/datasets/upload
   curl -X POST -F "file=@test_target_2026-01-08.csv" http://localhost:8001/datasets/upload
   ```

2. 統計差分APIの動作確認
   ```bash
   curl -s "http://localhost:8001/datasets/compare?base=6&target=7"
   ```
   - 行数変化: 10件→11件（+10.0%）✓
   - 価格平均: 22280.0→21254.5（-4.6%）✓
   - 在庫平均: 42.2→42.6（+1.0%）✓

3. LLM推移分析APIの動作確認
   ```bash
   curl -s "http://localhost:8001/datasets/compare/analysis?base=6&target=7"
   ```
   - 4セクション構成（変化の概要、注目すべき変化、トレンド分析、前提・限界）✓
   - 統計差分を基にした適切な分析テキスト生成 ✓

4. フロントエンドでの動作確認
   - データセット一覧画面でチェックボックス表示 ✓
   - 2つのデータセットを選択して比較実行 ✓
   - 推移比較画面の表示
     - メタ情報の横並び表示（色分け）✓
     - 統計差分の表示（増減の色分け）✓
     - LLM推移分析結果の表示 ✓

**確認された問題と解決策**:

1. **Dockerビルドキャッシュの問題**
   - 現象: `docker compose build frontend` でコードが反映されない
   - 原因: Dockerの `COPY . .` ステップのキャッシュが効きすぎる
   - 解決策: `docker compose build --no-cache frontend` でキャッシュなしビルド
   - 恒久対策: E-5-1でボリュームマウント方式に変更予定

2. **ブラウザキャッシュの問題**
   - 現象: フロントエンド更新後もブラウザが古いJSを使用
   - 解決策: ハードリロード（`Ctrl + Shift + R`）

**テストで使用したコマンド集**:

```bash
# バックエンドのビルドと再起動
docker compose build --no-cache backend
docker compose up -d backend

# フロントエンドのビルドと再起動
docker compose build --no-cache frontend
docker compose up -d frontend

# CSVアップロード
curl -X POST -F "file=@test.csv" http://localhost:8001/datasets/upload

# 統計差分API
curl -s "http://localhost:8001/datasets/compare?base=6&target=7" | python -m json.tool

# LLM推移分析API
curl -s "http://localhost:8001/datasets/compare/analysis?base=6&target=7" | python -m json.tool
```

---

#### E-0 完了の定義

以下をすべて満たすこと：

* [x] 2つのデータセットを選択して比較できる
* [x] 統計情報の差分が表示される
* [x] LLMが変化の要点を的確に指摘できる
* [x] フロントエンドで推移比較の一連の操作ができる
* [x] すべてのテストが通過し、カバレッジ80%以上を維持
* [x] 実際のデータで動作確認済み（代表CSV2件で検証）

**E-0 完了確認（2026/01/13）**

推移比較機能（Prismの最重要機能）の実装が完了しました。

**実装したサブタスク**:
- E-0-1: データモデルの拡張（完了）
- E-0-2: 推移比較APIの実装（完了）
- E-0-3: LLM推移分析の実装（完了）
- E-0-4: フロントエンド実装（完了）
- E-0-5: テスト（unit/integration）（完了）

**達成した成果**:
- Backend: 44テスト通過、カバレッジ90.36%
- Frontend: 18テスト通過、ビルド成功
- Integration: 実データでの動作確認完了

**次のステップ**:
- E-1: 最小限の使いやすさ改善（実ユーザーテスト前）
- E-2: 実ユーザーテスト（自社テスト、2-3週間）

---

### E-1. 最小限の使いやすさ改善（実ユーザーテスト前）

* [x] E-1-1. データセット削除機能
  * [x] `DELETE /datasets/{dataset_id}` エンドポイントを実装
  * [x] CASCADE設定により `dataset_rows` も自動削除されることを確認
  * [x] フロントエンドに削除ボタンを追加（一覧画面または詳細画面）
  * [x] 削除確認ダイアログを実装（誤操作防止）
  * [x] ユニットテストを追加（正常系、異常系：存在しないIDで404）

#### E-1-1 実装内容（完了 - 2026/01/13）

**変更ファイル**:
- `backend/app/main.py` - `DELETE /datasets/{dataset_id}` エンドポイントを追加
  - 指定されたデータセットを物理削除（PoC段階では論理削除は不要と判断）
  - CASCADE設定により `dataset_rows` も自動削除
  - エラーハンドリング（404: Dataset not found）
- `backend/tests/test_dataset_delete.py` - 新規作成（テスト3件）
- `backend/tests/conftest.py` - `db` fixtureを追加（テストで直接DBクエリが必要なため）
- `frontend/src/api/datasets.ts` - `deleteDataset(datasetId)` 関数を追加
- `frontend/src/pages/DatasetDetailPage.tsx` - 削除ボタンとハンドラーを追加
  - 赤色の「このデータセットを削除」ボタン（右上配置）
  - `window.confirm()` による削除確認ダイアログ
  - 削除成功後、データセット一覧画面へ自動リダイレクト
- `frontend/src/api/datasets.test.ts` - テスト2件を追加

**テスト結果**:
- Backend: 47テスト通過（新規3件を含む）、カバレッジ90.09%（目標80%以上達成）✓
- Frontend: 20テスト通過（新規2件を含む）✓

**新規追加テスト（Backend）**:
1. `testDeleteDatasetSucceeds` - データセット削除成功（204 No Content）
2. `testDeleteDatasetReturns404ForNonExistent` - 存在しないIDで404エラー
3. `testDeleteDatasetCascadesRows` - CASCADE削除の確認（dataset_rowsも削除される）

**新規追加テスト（Frontend）**:
1. `deleteDataset` の正常系（204 No Content）
2. `deleteDataset` の異常系（404 Not Found）

**API動作確認**:
- 存在しないID（999）: 404エラー ✓
- データセット作成（dataset_id=8）: 成功 ✓
- データセット削除: 204 No Content ✓
- 削除後アクセス: 404エラー（削除確認）✓

**ブラウザ動作確認**:
- 詳細画面に赤い削除ボタンが表示される ✓
- ボタンクリック時に確認ダイアログが表示される ✓
- 「OK」押下で削除実行、一覧画面へリダイレクト ✓
- 削除されたデータセットが一覧から消える ✓

**設計上の決定事項**:
- **物理削除を採用**（論理削除ではない）
  - 理由: PoC段階では削除履歴の管理は不要。シンプルさを優先。
  - 将来的に必要なら、`deleted_at` カラムを追加して論理削除に変更可能。
- **削除確認ダイアログ**: `window.confirm()` を使用（シンプルで十分）
  - 将来的にはカスタムモーダルに変更可能。
- **CASCADE削除**: PostgreSQLの外部キー制約で自動削除
  - `dataset_rows.dataset_id` に `ON DELETE CASCADE` を設定済み。

**技術的な学び**:
- pytest の fixture について
  - `db` fixture がなかったため、`conftest.py` に追加
  - fixture名と関数の引数名が一致することでpytestが自動注入
  - 直接DBをクエリする必要があるテストで有用
- Docker環境でのテスト実行
  - `prism2-test` 環境でテスト専用DBを使用
  - `--no-cache` オプションでキャッシュ問題を回避

---

* [x] E-1-2. 分析結果のコピー/エクスポート機能
  * [x] 分析結果テキストのコピーボタンを追加（クリップボードAPI利用）
  * [x] 分析結果のMarkdownエクスポート機能を追加
    * [x] ファイル名：`analysis_{dataset_id}_{YYYYMMDD}.md`
    * [x] 内容：メタ情報 + 統計サマリー + LLM分析結果
  * [x] 統計情報のCSVエクスポート機能を追加（オプション）
  * [x] ユニットテストを追加（エクスポート処理の検証）

#### E-1-2 実装内容（完了 - 2026/01/13）

**変更ファイル**:
- `frontend/src/pages/DatasetDetailPage.tsx` - 3つのエクスポート機能を追加
  - `copyToClipboard()` - クリップボードAPIを使用した分析結果のコピー
  - `exportAnalysisAsMarkdown()` - Markdown形式でのエクスポート（メタ情報+統計+分析結果）
  - `exportStatsAsCsv()` - 統計情報のCSVエクスポート（BOM付きUTF-8）
- `frontend/src/pages/DatasetComparePage.tsx` - 推移比較画面に同様の機能を追加
  - `copyToClipboard()` - 推移分析結果のコピー
  - `exportComparisonAsMarkdown()` - 推移比較結果のMarkdownエクスポート

**テスト結果**:
- フロントエンドユニットテスト: 20件すべて通過 ✓
- ビルド: 成功 ✓
- Lintエラー: なし ✓

**ブラウザ動作確認**:
- データセット詳細画面での動作確認 ✓
  - 📋 コピーボタン: 分析結果がクリップボードにコピーされる ✓
  - 📄 Markdownエクスポートボタン: `.md` ファイルがダウンロードされる ✓
  - 📊 CSVエクスポートボタン: 統計情報が `.csv` ファイルでダウンロードされる ✓
- 推移比較画面での動作確認 ✓
  - 📋 コピーボタン: 推移分析結果がクリップボードにコピーされる ✓
  - 📄 Markdownエクスポートボタン: 推移比較結果が `.md` ファイルでダウンロードされる ✓
- ダウンロードされたファイルの確認 ✓
  - ファイル名形式が正しい（`analysis_{id}_{date}.md` 等）✓
  - ファイル内容が正しい（メタ情報+統計+分析結果）✓
  - CSV が Excel で正しく開ける（BOM付きUTF-8）✓

**実装した機能**:
1. **分析結果のコピーボタン**
   - クリップボードAPI (`navigator.clipboard.writeText`) を使用
   - ボタンクリックでワンクリックコピー
   - 成功時にアラート通知

2. **Markdownエクスポート機能**
   - ファイル名形式: `analysis_{dataset_id}_{YYYYMMDD}.md` / `comparison_{base}_{target}_{YYYYMMDD}.md`
   - 内容:
     - メタ情報（データセットID、ファイル名、作成日時、行数）
     - 統計サマリー（カラム情報、数値統計、頻出値）
     - LLM分析結果（全文）
   - Blob + URL.createObjectURL を使用してダウンロード

3. **統計情報のCSVエクスポート機能**
   - ファイル名形式: `stats_{dataset_id}_{YYYYMMDD}.csv`
   - BOM付きUTF-8で出力（Excel対応）
   - カラムごとの統計情報を表形式で出力
   - 数値統計（件数、最小、平均、最大）と頻出値（上位3つ）を含む

4. **UIの配置**
   - 各セクションの見出し横にボタンを配置
   - 色分け：コピー（青）、Markdownエクスポート（オレンジ）、CSVエクスポート（緑）
   - 絵文字アイコンで視認性向上

**技術的な実装ポイント**:
- クリップボードAPI: モダンブラウザの標準API、非同期処理
- Blob API: ファイル生成に使用、UTF-8エンコーディング
- BOM付きUTF-8: CSVをExcelで正しく開くために必要（`\uFEFF`）
- URL.createObjectURL: ダウンロード後にrevokeしてメモリリーク防止

**ユーザー体験の改善**:
- 分析結果を簡単にSlack、メール、ドキュメントに共有可能
- Markdown形式でバージョン管理（Git等）に保存可能
- CSV形式でExcelやBIツールでの二次分析が可能
- E2実ユーザーテストでのフィードバック収集に有効

**開発フローの学び（今回の反省点）**:

1. **ローカルビルドの冗長性**
   - 誤り: `npm test` の後に `npm run build` を実行していた
   - 理由: `npm test` で既に TypeScript のコンパイルチェックは完了している
   - 改善: ローカルでの `npm run build` は省略可能
   - ローカルビルドの成果物 (`frontend/dist/`) は Docker ビルドでは使われない
   - Docker コンテナ内で再度ビルドされるため、ローカルビルドは不要

2. **ドキュメント更新のタイミング**
   - 誤り: ブラウザでの動作確認前に `develop_process.md` を「完了」として更新してしまった
   - 理由: 実際にボタンを押して動作確認する前に記録してしまった
   - 改善: **必ずブラウザでの動作確認後にドキュメントを更新する**

3. **正しい開発フロー（フロントエンド機能追加時）**
   ```bash
   # 1. 実装
   # 2. ユニットテスト実行
   cd frontend && npm test
   
   # 3. Dockerビルド・起動
   docker compose build --no-cache frontend
   docker compose up -d frontend
   
   # 4. 【重要】ブラウザでの動作確認（必須！）
   # - http://localhost:3001 にアクセス
   # - 各機能を実際に操作
   # - 期待通りの動作をすることを確認
   # - エラーが出ないことを確認
   
   # 5. すべて確認できてから develop_process.md を更新
   ```

4. **テストの役割の理解**
   - ユニットテスト (`npm test`): ロジックの正しさ、型の整合性を確認
   - ブラウザテスト: 実際のUI動作、ユーザー体験を確認
   - **両方とも必要**。ユニットテストが通っても、実際の動作確認は必須

* [ ] E-1-3. UI/UXの微調整（任意）
  * [ ] ローディング中の表示改善（スピナー、プログレスバー）
  * [ ] エラーメッセージの改善（ユーザーフレンドリーな文言）
  * [ ] レスポンシブデザインの確認（モバイル対応は必要か検討）

#### E-1-3 実装判断（スキップ - 2026/01/13）

**スキップ理由**:
- E-1-3 は任意タスクであり、E-2実ユーザーテストの前提条件ではない
- 現状のUIでも基本的な操作は問題なく実施可能
- E-2のテスト中に実際の不便さが明らかになってから対応する方が効率的
- 早期にE-2（実ユーザーテスト）を開始し、推移比較機能の価値検証を優先

**今後の対応方針**:
- E-2テスト中に「これは改善すべき」という明確なフィードバックがあれば実施
- E-2完了後、Go判断になった場合はフェーズFで本格的なUI/UX改善を実施

---

### E-1 完了の確認（2026/01/13）

フェーズE-1「最小限の使いやすさ改善」が完了しました。

**完了したタスク**:
- ✅ E-1-1: データセット削除機能（完了）
- ✅ E-1-2: 分析結果のコピー/エクスポート機能（完了）
- ⏭️ E-1-3: UI/UXの微調整（スキップ、E-2後に再検討）

**達成した成果**:
- Backend: 47テスト通過、カバレッジ90.09%
- Frontend: 20テスト通過
- ブラウザ動作確認: すべて正常動作

**次のステップ**:
- E-2: 実ユーザーテスト（自社テスト）の準備に進む

---

### E-2. 実ユーザーテスト（自社テスト）

**前提**: E-0（推移比較機能）とE-1（使いやすさ改善）が完了していること

**期間**: 2-3週間（推移比較機能の検証を含む）

**実施方針**（2026/01/15決定）：
- ペルソナ3（推移比較機能）を最初から最重要確認テストとして実行
- ペルソナ1,2（単発分析）は並行して実行
- 実行結果は本ファイルの各タスク下に直接追記
- 詳細計画は `docs/E2_User_Test_Plan.md` を参照

* [x] E-2-1. テスト環境準備
  * [x] テスト計画の最終確認（`E2_User_Test_Plan.md`）
  * [x] ローカルDocker環境の動作確認
  * [x] 推移比較テストの対象選定
  * [x] 比較用データの確保（過去データ＋最新データ）
  * [x] 単発分析用サンプルCSVの準備（並行実施）

**実施記録（E-2-1）**：
- 実施日: 2026/01/15
- 選定した対象: ランサーズ開発案件リスト
- 確保したデータ:
  - 過去データ: dataset_id=4 (results_20251210084429.csv)
    - 収集日: 2025/12/10
    - 件数: 153件
  - 最新データ: dataset_id=9 (results_20260115015514.csv)
    - 収集日: 2026/01/15
    - 件数: 138件
  - データ期間: 約1ヶ月（2025/12/10 → 2026/01/15）
- 備考: 推移比較テストの準備完了。E-2-2の第1回比較から開始可能。

* [ ] E-2-2. 推移比較機能のテスト（ペルソナC・最重要・Week 1-3）

**目的**: E-2-1で準備したデータを使用し、推移比較機能の実用性を検証する。
第1回比較で課題を洗い出し、改善後に第2回以降の比較で効果を検証する。

**テスト項目**:
  * [ ] 同一対象を継続スクレイピング（週2-3回 × 2-3週間）
  * [ ] 推移比較機能を実際に使用
  * [x] E-2-2-1-0: 第1回比較の実施（初回テスト・課題の洗い出し）
  * [ ] E-2-2-1-1～8: 改善タスクの実施（第1回結果を受けた改善）
  * [ ] E-2-2-2-0～6-0: 第2～6回比較の実施（改善後の検証）
  * [ ] シナリオ3-1: 不動産価格の推移
  * [ ] シナリオ3-2: 競合商品の価格変動
  * [x] シナリオ3-3: 求人市場のトレンド変化（任意）- E-2-2-1-0で実施
  * [ ] シナリオ3-4: ECサイトの在庫状況の変化（任意）
  * [ ] LLM推移分析の精度・有用性を評価
  * [ ] **「キラー機能」として成立するか判断**
  * [ ] 継続利用意向を自己評価

**実施記録（E-2-2）**：

---

## E-2-2-1: 第1回比較（初回テスト）

### E-2-2-1-0: 比較テスト実施 ✅完了

**実施日**: 2026/01/15
**データ**: E-2-1で準備したデータ（dataset_id=4, 9）を使用

- base: dataset_id=9 results_20260115015514.csv　(2026/01/15収集)
- target: dataset_id=4　results_20251210084429.csv (2025/12/10収集)
- データ期間: 約1ヶ月（2025/12/10 → 2026/01/15）
- 対象: ランサーズ開発案件リスト

**統計差分（数値）**:
- 行数: 153件 → 138件　-15件 (-9.8%)
- No: 平均15.8 → 14.4 (-1.4)
- Page: 平均3.0 → 2.9 (-0.1)
- rowOrder: 平均77.0 → 69.5 (-7.5)
- 評価: そもそもこういう統計差分に分析評価論評の観点で価値は薄い

**LLM分析の評価**:

❌ **致命的な問題点**:
1. **ビジネス価値がゼロ**
   - 「行数が15件減った」「rowOrderが7.5減った」という技術的事実の報告のみ
   - 依頼者が知りたい「案件の傾向変化」「価格動向」「求められるスキルの変化」が一切ない
   - 現状は「データファイルの構造変化」を報告しているだけで、ビジネスインサイトが皆無

2. **重要なカラムが完全に無視されている**
   - **Title**（案件名）: どんな案件が増えた/減ったのか？ → 無視
   - **UnitPrice**（単価）: 価格帯はどう変わったのか？ → 無視
   - **SkillTags**（スキル）: 求められるスキルの変化は？ → 無視
   - **CategoryText**（カテゴリ）: どのカテゴリが増減したのか？ → 無視
   - 理由: これらが「string」扱いで分析対象外になっている

3. **アクションにつながらない**
   - 「今後のデータセットの変化を観察する必要があります」→ 当たり前すぎて無価値
   - 「次に何をすべきか」「どう対応すべきか」が一切提示されない
   - コンサルタントレポートとして機能していない

**本来あるべき分析内容**:
- 価格帯の変化: 高単価/中単価/低単価の増減トレンド
- 案件内容のトレンド: どんなキーワード（AI、機械学習等）が増減したか
- スキル需要の変化: Python、TypeScript等のスキル需要の変化
- カテゴリ別動向: Web開発、アプリ開発等の増減
- アクション推奨: 何をすべきかの具体的提案

**発見した変化（データ内容）**:
- 現状のLLM分析では発見できていない（技術的指標のみで、ビジネス的変化が不明）

**UI/UX改善点**:
- 一覧画面の比較対象選択: どちらがbaseか明示されていない
- コピーボタンとMarkdownエクスポートの出力内容が不統一
  - コピー: 統計情報を含まない
  - Markdownエクスポート: 統計情報を含む全比較結果
- プロンプト確認・編集機能がない: LLMに送信される内容が不明

**従来手法との比較**:
- 統計的な比較処理: Prismの方が圧倒的に速い（3分 vs 90分）
- 分析の質: 今のままでは手作業の方が有用
  - 手作業なら「価格帯の変化」「案件傾向」を自分で見て判断できる
  - Prismは「No, Page, rowOrder」という無意味な指標を報告するだけ
- 結論: 処理速度は速いが、分析の「内容」が役に立たない

**所要時間**:
- Prism: 3分（アップロード→比較実行→レポート確認）
- 手作業: 90分（想定）
  - サイトから案件コピペ
  - CSV2ファイルを比較
  - 統計差分を関数で計算
  - コメント記載
- 時間短縮率: 97%削減（3分 vs 90分）
- ただし、**分析の質が低すぎて使い物にならない**

**継続利用意向**:
❌ **継続利用しない**

理由:
- 統計的な差分比較や分析では価値がない
- 内容の中身の変化（案件内容、価格帯、スキル需要）を仮説や推察を含めて文脈の中で出力する必要がある
- 現状のプロンプトでは「データファイルの変化」しか見ておらず、「ビジネスの変化」が全く見えない
- 手作業の方が、時間はかかるが有用な示唆が得られる

**根本原因**:
- プロンプトが「統計差分」にフォーカスしすぎている
- 「No」「Page」「rowOrder」などの技術的項目を分析している
- ビジネス的に重要な**文字列カラム（Title, Price, Skillなど）を無視**している
- 「データの中身」ではなく「データの構造」を分析している

**備考**:
- 参照レポート: `samples/comparison_4_9_20260115.md`
- この第1回比較の結果が、改善タスクの優先順位を決定する


---

### 【改善タスク】E-2-2-1の結果から抽出

**実施期間**: YYYY/MM/DD ～ YYYY/MM/DD

**位置づけ**: 第1回比較（E-2-2-1-0）で判明した課題を改善し、第2回以降の比較で効果を検証する。
改善作業と並行して、週2-3回のデータ収集（スクレイピング）を継続する。

**改善の優先順位方針**:
- **Phase 1（最優先・実装必須）**: E-2-2-1-1～3 - ビジネス価値に直結する分析内容の改善
- **Phase 2（高優先）**: E-2-2-1-4～5 - 分析の深さを向上させる機能
- **Phase 3（中優先）**: E-2-2-1-6～8 - UI/UXの改善

---

#### Phase 1（最優先・実装必須）

**Phase 1完了の条件:**
- [x] E-2-2-1-1, 1-2, 1-3のすべてのDone定義を満たす
- [x] 全体のテストカバレッジが80%以上を維持
- [X] CI（GitHub Actions）がすべて通過
- [x] 実データ（dataset_id=4, 9）でレポートを生成
  - `samples/comparison_4_9_v2.md` として保存
- [x] v1とv2のレポートを比較し、改善効果を確認
  - ビジネス価値のある示唆が含まれている
  - アクションにつながる提案がある
  - 技術的指標の記述が削減されている

---

##### E-2-2-1-1: 価格帯の分析機能追加
**優先度**: ⭐⭐⭐ 最優先

- **問題**: UnitPriceが「string」として無視され、価格動向が全く分析されない
- **対応方針**: 
  - UnitPriceカラムから数値を抽出（例: "80万円/月" → 80）
  - 価格帯を分類（高単価: 80万円以上、中単価: 50-80万円、低単価: 50万円未満）
  - 各価格帯の件数と増減率を計算
  - LLMプロンプトに価格帯の変化を含める
- **実装判断**: ✅ 実装する
- **期待される効果**: 「価格帯が中単価にシフト」「高単価案件が減少」などの実用的な示唆

**Done定義**:
- [x] **1. 実装完了の基準**
  - [x] UnitPriceから数値を抽出する関数を実装（`extract_price_value()`）
    - 入力例: "80万円/月", "50-60万円", "¥800,000"
    - 出力例: 80, 55（中央値）, 80
    - 欠損値・解析不可値の処理を実装
  - [x] 価格帯分類ロジックを実装（`classify_price_range()`）
    - 高単価: 80万円以上
    - 中単価: 50-80万円
    - 低単価: 50万円未満
    - 不明: 解析不可
  - [x] base/targetの価格帯別集計関数を実装（`compare_price_ranges()`）
    - 各価格帯の件数と構成比を計算
    - 増減数と増減率を計算
  - [x] 統計差分レスポンスに価格帯情報を追加
    - `/datasets/compare` APIのレスポンスに `price_range_analysis` フィールドを追加

- [x] **2. テスト完了の基準**
  - [x] ユニットテストを追加（カバレッジ80%以上維持）
    - `test_extract_price_value_success()`: 正常系（各種フォーマット）
    - `test_extract_price_value_missing()`: 欠損値の処理
    - `test_extract_price_value_invalid()`: 解析不可値の処理
    - `test_classify_price_range()`: 価格帯分類
    - `test_compare_price_ranges()`: base/target比較
  - [x] 統合テストでAPIレスポンスを確認
    - 実データ（dataset_id=4, 9）で `/datasets/compare` を実行
    - レスポンスに `price_range_analysis` が含まれることを確認
    - 価格帯の件数・増減率が妥当であることを確認

- [x] **3. 出力サンプルの確認**
  - [x] 以下の形式でレスポンスが返ること
```json
{
  "price_range_analysis": {
    "base": {
      "high": 12,    // 80万円以上
      "mid": 45,     // 50-80万円
      "low": 96,     // 50万円未満
      "unknown": 0   // 解析不可
    },
    "target": {
      "high": 8,
      "mid": 52,
      "low": 78,
      "unknown": 0
    },
    "changes": {
      "high": {"diff": -4, "percent": -33.3},
      "mid": {"diff": 7, "percent": 15.6},
      "low": {"diff": -18, "percent": -18.8}
    }
  }
}
```

- [x] **4. ドキュメント更新**
  - [x] `backend/app/analysis.py` に関数の docstring を追加
  - [x] Swagger（`/docs`）で新しいレスポンス形式が確認できる

- **実施記録**:
  - 実施日: 2026/01/16
  - 変更内容:
    - `backend/app/analysis.py`: 3つの価格分析関数を追加
      - `extract_price_value()`: 価格文字列から数値抽出（正規表現による解析）
      - `classify_price_range()`: 価格帯分類（high/mid/low/unknown）
      - `compare_price_ranges()`: base/target の価格帯別集計と増減計算
    - `backend/app/main.py`: `/datasets/compare` エンドポイントの拡張
      - DatasetRow.data から JSONB 行データ取得
      - `compare_price_ranges()` 呼び出し
      - レスポンスに `price_range_analysis` フィールド追加
    - `backend/tests/test_price_analysis.py`: ユニットテスト19件追加
      - 価格抽出テスト: 10件（万円/範囲/カンマ/None/空文字/無効値等）
      - 価格帯分類テスト: 5件（high/mid/low/unknown/境界値）
      - 価格帯比較テスト: 4件（正常系/空データ/カスタムカラム等）
    - `backend/tests/test_dataset_compare.py`: 統合テスト1件追加
      - `testGetDatasetCompareIncludesPriceRangeAnalysis()`
  - テスト結果:
    - 全67テスト通過（既存47 + 新規20）
    - カバレッジ: 90.21%（目標80%以上達成）
    - `app/analysis.py`: 89%、`app/main.py`: 91%、`app/llm.py`: 87%
  - 実データでの動作確認（2026/01/16）:
    - dataset_id=9（2026/01/15収集、138件）vs dataset_id=4（2025/12/10収集、153件）
    - 価格帯分析結果:
      - 高単価案件: 15件 → 42件（+180.0%）
      - 中単価案件: 24件 → 34件（+41.7%）
      - 低単価案件: 82件 → 71件（-13.4%）
      - 不明: 17件 → 6件（-64.7%）
    - ビジネス価値のある示唆: 市場全体が高単価化のトレンド

---

##### E-2-2-1-2: 案件内容のキーワード分析
**優先度**: ⭐⭐⭐ 最優先

- **問題**: Titleが無視され、どんな案件が増減したか全く分からない
- **対応方針**:
  - Titleからキーワードを抽出（例: "AI", "機械学習", "Next.js", "PHP"等）
  - base/targetでキーワード出現頻度を比較
  - 増加キーワードTop5、減少キーワードTop5を抽出
  - LLMプロンプトにキーワード変化を含める
- **実装判断**: ✅ 実装する
- **期待される効果**: 「AI案件が増加」「PHP案件が減少」などの技術トレンドの把握

**Done定義**:
- [x] **1. 実装完了の基準**
  - [x] Titleからキーワードを抽出する関数を実装（`extract_keywords_from_titles()`）
    - 技術キーワードリスト（100-200語程度）を定義
      - 例: ["AI", "機械学習", "Python", "TypeScript", "Next.js", "PHP", "WordPress", ...]
    - 大文字小文字を区別しないマッチング
    - 複数のキーワードが1つのTitleに含まれる場合、すべて抽出
  - [x] キーワード頻度を集計する関数を実装（`extract_keywords_from_titles()`内で実装）
    - データセット内の各キーワードの出現回数をカウント
  - [x] base/targetのキーワード頻度を比較する関数を実装（`compare_keywords()`）
    - 増加キーワードTop10を抽出（増加数順）
    - 減少キーワードTop10を抽出（減少数順）
    - 新規出現キーワード、消失キーワードを抽出
  - [x] 統計差分レスポンスにキーワード情報を追加
    - `/datasets/compare` APIのレスポンスに `keyword_analysis` フィールドを追加

- [x] **2. テスト完了の基準**
  - [x] ユニットテストを追加（カバレッジ80%以上維持）
    - `testExtractKeywordsSuccess()`: キーワード抽出
    - `testExtractKeywordsCaseInsensitive()`: 大文字小文字の処理
    - `testExtractKeywordsMultipleInOneTitle()`: 複数キーワード抽出
    - `testCompareKeywordsIncreased/Decreased()`: base/target比較
  - [x] 統合テストでAPIレスポンスを確認
    - 実データ（dataset_id=4, 9）で `/datasets/compare` を実行
    - レスポンスに `keyword_analysis` が含まれることを確認
    - 増加/減少キーワードが妥当であることを確認

- [x] **3. 出力サンプルの確認**
  - [x] 以下の形式でレスポンスが返ること
```json
{
  "keyword_analysis": {
    "base_total": 153,
    "target_total": 138,
    "increased_keywords": [
      {"keyword": "AI", "base": 5, "target": 12, "diff": 7},
      {"keyword": "Next.js", "base": 8, "target": 14, "diff": 6},
      ...
    ],
    "decreased_keywords": [
      {"keyword": "PHP", "base": 25, "target": 18, "diff": -7},
      {"keyword": "WordPress", "base": 15, "target": 10, "diff": -5},
      ...
    ],
    "new_keywords": ["ChatGPT", "Stable Diffusion"],
    "disappeared_keywords": ["Flash"]
  }
}
```

- [x] **4. キーワードリストの作成**
  - [x] 技術キーワードリストを `backend/app/keywords.py` として作成
    - プログラミング言語: Python, Java, PHP, JavaScript, TypeScript, ...
    - フレームワーク: React, Vue.js, Next.js, Django, Laravel, ...
    - クラウド/インフラ: AWS, Azure, GCP, Docker, Kubernetes, ...
    - データベース: MySQL, PostgreSQL, MongoDB, Redis, ...
    - AI/ML: AI, 機械学習, ChatGPT, Gemini, LLM, 生成AI, ...
    - その他: ブロックチェーン, IoT, VR/AR, ...
    - ※PoC段階では直書き、本番リリース前にUI管理機能を追加予定

- [x] **5. ドキュメント更新**
  - [x] Swagger（`/docs`）で新しいレスポンス形式が確認できる
  - ※キーワードリストのメンテナンス方法のドキュメント化は次タスク以降で実施

- **実施記録**:
  - 実施日: 2026/01/16
  - 変更内容:
    - `backend/app/keywords.py`: 技術キーワードリスト作成（約150語）
      - プログラミング言語、フレームワーク、クラウド、DB、AI/ML、モバイル、ゲーム、ビジネスキーワード等
    - `backend/app/analysis.py`: 
      - `extract_keywords_from_titles()`: Titleからキーワード抽出・頻度集計
      - `compare_keywords()`: base/target間のキーワード増減比較
    - `backend/app/main.py`: `/datasets/compare` APIに `keyword_analysis` フィールド追加
    - `backend/tests/test_keyword_analysis.py`: ユニットテスト13件追加
    - `backend/tests/test_dataset_compare.py`: 統合テスト1件追加
  - テスト結果: 
    - 全81テスト成功（うちキーワード分析関連14テスト）
    - カバレッジ: 90.53%（目標80%を超過）
  - 実データ検証結果（dataset_id=4 vs 9）:
    - 増加キーワード検出: Java +4件（7→11）、VBA +3件（1→4）
    - 新規キーワード検出: TypeScript、C++、AWS、生成AI、Gemini等
    - ビジネス的示唆: 高単価案件の増加（前タスク結果）とJava/AWS需要増が相関

---

##### E-2-2-1-3: プロンプトv2の実装（ビジネス文脈重視）
**優先度**: ⭐⭐⭐ 最優先

- **問題**: 
  - 現在のプロンプトは「統計差分」にフォーカスしすぎ
  - 「No, Page, rowOrder」などの無意味な指標を分析
  - ビジネス的な示唆が一切ない
- **対応方針**:
  - タスク1, 2の結果を統合し、新しいプロンプト構造を設計
  - **入力データの優先順位**:
    1. 価格帯の変化（高/中/低単価の増減）
    2. 案件内容のキーワード変化（増加/減少Top5）
    3. スキル需要の変化（タスク4の結果）
    4. カテゴリ別動向（タスク5の結果）
    5. 行数変化（参考情報として最後）
  - **出力フォーマット**:
    ```
    ## ビジネス動向サマリー
    [1-2文で全体像]
    
    ## 価格動向
    [高/中/低単価の変化と示唆]
    
    ## 案件内容のトレンド
    [増加キーワード、減少キーワード、技術トレンド]
    
    ## スキル需要の変化
    [求められるスキルの変化]
    
    ## カテゴリ別動向
    [カテゴリの増減]
    
    ## 推奨アクション
    [具体的な次のアクション3-5つ]
    
    ## 前提・限界
    [分析の前提条件、注意点]
    ```
- **実装判断**: ✅ 実装する

**Done定義**:
- [x] **1. 実装完了の基準**
  - [x] `build_comparison_prompt_v2()` 関数を実装
    - タスク1の価格帯分析結果を入力として受け取る
    - タスク2のキーワード分析結果を入力として受け取る
    - 既存の統計差分情報も受け取る（優先度低く配置）
  - [x] 新しいプロンプトテンプレートを実装
    - ビジネス動向サマリー、価格動向、案件内容のトレンド、推奨アクション、前提・限界の各セクションを含む
    - 統計的指標（No, Page, rowOrder）を**削除または最小化**
    - ビジネス指標を**最優先で配置**
  - [x] `/datasets/compare/analysis` APIを更新
    - プロンプトv1からv2に切り替え
    - または、クエリパラメータ `?version=v2` で選択可能にする（推奨）

- [x] **2. テスト完了の基準**
  - [x] ユニットテストを追加（カバレッジ80%以上維持）
    - `test_build_comparison_prompt_v2_structure()`: プロンプト構造の検証
    - `test_build_comparison_prompt_v2_price_inclusion()`: 価格帯情報の埋め込み確認
    - `test_build_comparison_prompt_v2_keyword_inclusion()`: キーワード情報の埋め込み確認
    - `test_build_comparison_prompt_v2_no_technical_metrics()`: No, Page等が含まれないことを確認
  - [x] LLMモック時のテスト
    - プロンプトv2を使用した際のレスポンス構造を確認
    - 期待される出力フォーマット（5セクション）が生成されることを確認

- [x] **3. 実データでの動作確認**
  - [x] 実データ（dataset_id=4, 9）で `/datasets/compare/analysis?version=v2` を実行
  - [x] 生成されたレポートが以下を満たすこと:
    - ✅ **ビジネス動向サマリー**: 1-2文で全体像が述べられている
    - ✅ **価格動向**: 高/中/低単価の変化と示唆が記載されている
    - ✅ **案件内容のトレンド**: 増加/減少キーワードが記載されている
    - ✅ **推奨アクション**: 具体的な次のアクション3-5つが提示されている
    - ✅ **前提・限界**: 分析の前提条件、注意点が記載されている
    - ✅ **技術的指標（No, Page, rowOrder）が主題として扱われていない**

- [x] **4. プロンプトの品質確認**
  - [x] 生成されたプロンプトをファイル出力し、レビュー
    - `samples/prompt_v2_example.txt` として保存
    - プロンプトのトークン数を確認（1538文字、9000文字以内）
    - 価格帯情報、キーワード情報が適切に整形されていることを確認

- [x] **5. v1との比較**
  - [x] 同じデータで v1 と v2 を実行し、出力を比較
    - v1: `samples/comparison_4_9_v1.md`
    - v2: `samples/comparison_4_9_v2.md`
  - [x] v2がv1と比較して以下を満たすこと:
    - ✅ ビジネス価値のある示唆が含まれている
    - ✅ アクションにつながる提案がある
    - ✅ 技術的指標の記述が削減されている
    - ✅ 読みやすく、依頼者にとって有用である

- [x] **6. ドキュメント更新**
  - [x] プロンプトv2の設計思想を `docs/prompt_design.md` に記載
  - [x] v1とv2の違いを `docs/prompt_design.md` に記載
  - [x] Swagger（`/docs`）でバージョンパラメータの使い方を説明

- **実施記録**:
  - 実施日: 2026/01/18
  - 変更内容:
    - `backend/app/analysis.py`: `build_comparison_prompt_v2()` の実装（212行追加）
    - `backend/app/main.py`: `version` パラメータ追加、v2呼び出し対応
    - `backend/tests/test_prompt_v2.py`: 8テストケース追加
    - `docs/prompt_design.md`: プロンプト設計ドキュメント新規作成
    - `samples/prompt_v2_example.txt`: プロンプト例
    - `samples/comparison_4_9_v1.md`, `samples/comparison_4_9_v2.md`: v1/v2比較用出力
  - テスト結果: 88テスト成功、カバレッジ91.21%

---

#### Phase 2（高優先）

##### E-2-2-1-4: スキル需要の分析
**優先度**: ⭐⭐ 高優先

- **問題**: SkillTagsが無視され、求められるスキルの変化が分からない
- **対応方針**:
  - SkillTagsから個別スキルを抽出
  - base/targetでスキル出現頻度を比較
  - 需要増スキルTop5、需要減スキルTop5を抽出
  - LLMプロンプトにスキル需要の変化を含める
- **実装判断**: ✅ 実装する（タスク3と統合可能）
- **実施記録**:
  - 実施日: YYYY/MM/DD
  - 変更内容: [...]
  - テスト結果: [...]

---

##### E-2-2-1-5: カテゴリ別動向の分析
**優先度**: ⭐⭐ 高優先

- **問題**: CategoryTextが無視され、カテゴリ別の増減が分からない
- **対応方針**:
  - CategoryTextの値を集計
  - base/targetでカテゴリ別件数を比較
  - 増減率Top5のカテゴリを抽出
  - LLMプロンプトにカテゴリ動向を含める
- **実装判断**: ✅ 実装する（タスク3と統合可能）
- **実施記録**:
  - 実施日: YYYY/MM/DD
  - 変更内容: [...]
  - テスト結果: [...]

---

#### Phase 3（中優先・後回し可）

##### E-2-2-1-6: プロンプト確認・編集機能の追加
**優先度**: ⭐ 中優先

- **問題**: LLMに送信されるプロンプトの内容が確認できない
- **対応方針**: 
  - 比較分析画面に「プロンプト表示」ボタンを追加
  - モーダルでプロンプト全文を表示
  - （オプション）プロンプト編集機能
- **実装判断**: 後回し（タスク1-5の効果を確認してから判断）
- **実施記録**:
  - 実施日: YYYY/MM/DD
  - 変更内容: [...]
  - テスト結果: [...]

---

##### E-2-2-1-7: base/target選択UIの改善
**優先度**: ⭐ 中優先

- **問題**: チェックボックスでどちらがbaseか分からない
- **対応方針**: 
  - チェックボックス方式からドロップダウン方式に変更
  - 「基準データ (base)」「比較対象データ (target)」を明示
- **実装判断**: 後回し（機能的には動作しているため）
- **実施記録**:
  - 実施日: YYYY/MM/DD
  - 変更内容: [...]
  - テスト結果: [...]

---

##### E-2-2-1-8: コピーボタンの出力内容統一
**優先度**: ⭐ 中優先（低）

- **問題**: コピーは統計情報を含まないが、Markdownエクスポートは含む
- **対応方針**: コピーボタンも統計情報を含むように修正
- **実装判断**: 後回し（優先度低い）
- **実施記録**:
  - 実施日: YYYY/MM/DD
  - 変更内容: [...]
  - テスト結果: [...]

---

#### 実装スケジュール案

**Phase 1（最優先・1週間以内）**:
1. ✅ E-2-2-1-1: 価格帯の分析機能（完了: 2026/01/13）
2. ✅ E-2-2-1-2: 案件内容のキーワード分析（完了: 2026/01/16）
3. ✅ E-2-2-1-3: プロンプトv2の実装（完了: 2026/01/18）

**Phase 2（高優先・1週間以内）**:
4. E-2-2-1-4: スキル需要の分析
5. E-2-2-1-5: カテゴリ別動向の分析
6. プロンプトv2の調整（Phase 1の結果を反映）

**Phase 3（中優先・後回し可）**:
7. E-2-2-1-6: プロンプト確認機能
8. E-2-2-1-7: base/target選択UI改善
9. E-2-2-1-8: コピーボタン改善

---

**改善完了後の確認**:
- 改善タスク実施中も、週2-3回のデータ収集（スクレイピング）は継続
- Phase 1完了後、E-2-2-2-0（第2回比較）を実施（最優先タスクの効果検証）
- Phase 2完了後、E-2-2-3-0（第3回比較）を実施（全改善の効果検証）

---

## E-2-2-2: 第2回比較（Phase 1完了後の検証）

### E-2-2-2-0: 比較テスト実施

**実施日**: YYYY/MM/DD
**前提**: Phase 1（E-2-2-1-1～3）の改善完了後
**データ**: 新たに収集したデータを使用

- base: dataset_id=X (YYYY/MM/DD収集)
- target: dataset_id=Y (YYYY/MM/DD収集)
- 統計差分（数値）: [行数変化、価格変化等の数値的な要点]
  - [詳細]
- 発見した変化（データ内容）: [案件内容の傾向、価格帯、カテゴリ等のビジネス的な変化]
  - [具体例]
- LLM分析の評価: [有用だったか、的外れだったか等]
  - [詳細]
- UI/UX改善点: [使いにくかった点、バグ、欲しい機能]
  - [具体的な改善要望]
- 従来手法との比較: [Excel等で同じことをやる場合と比較]
  - [詳細]
- 所要時間:
  - Prism=X分 vs 手作業=Y分
- 継続利用意向:
  - [この回の実感]
- 備考:
  - [その他]


---

## E-2-2-3: 第3回比較（Phase 2完了後の検証）

### E-2-2-3-0: 比較テスト実施

**実施日**: YYYY/MM/DD
**前提**: Phase 2（E-2-2-1-4～5）の改善完了後
**データ**: 継続収集データを使用

- base: dataset_id=X (YYYY/MM/DD収集)
- target: dataset_id=Y (YYYY/MM/DD収集)
- 統計差分（数値）: [行数変化、価格変化等の数値的な要点]
  - [詳細]
- 発見した変化（データ内容）: [案件内容の傾向、価格帯、カテゴリ等のビジネス的な変化]
  - [具体例]
- LLM分析の評価: [有用だったか、的外れだったか等]
  - [詳細]
- UI/UX改善点: [使いにくかった点、バグ、欲しい機能]
  - [具体的な改善要望]
- 従来手法との比較: [Excel等で同じことをやる場合と比較]
  - [詳細]
- 所要時間:
  - Prism=X分 vs 手作業=Y分
- 継続利用意向:
  - [この回の実感]
- 備考:
  - [その他]


---

## E-2-2-4: 第4回比較

### E-2-2-4-0: 比較テスト実施

**実施日**: YYYY/MM/DD
**データ**: 継続収集データを使用

- base: dataset_id=X (YYYY/MM/DD収集)
- target: dataset_id=Y (YYYY/MM/DD収集)
- 統計差分（数値）: [行数変化、価格変化等の数値的な要点]
  - [詳細]
- 発見した変化（データ内容）: [案件内容の傾向、価格帯、カテゴリ等のビジネス的な変化]
  - [具体例]
- LLM分析の評価: [有用だったか、的外れだったか等]
  - [詳細]
- UI/UX改善点: [使いにくかった点、バグ、欲しい機能]
  - [具体的な改善要望]
- 従来手法との比較: [Excel等で同じことをやる場合と比較]
  - [詳細]
- 所要時間:
  - Prism=X分 vs 手作業=Y分
- 継続利用意向:
  - [この回の実感]
- 備考:
  - [その他]


---

## E-2-2-5: 第5回比較

### E-2-2-5-0: 比較テスト実施

**実施日**: YYYY/MM/DD
**データ**: 継続収集データを使用

- base: dataset_id=X (YYYY/MM/DD収集)
- target: dataset_id=Y (YYYY/MM/DD収集)
- 統計差分（数値）: [行数変化、価格変化等の数値的な要点]
  - [詳細]
- 発見した変化（データ内容）: [案件内容の傾向、価格帯、カテゴリ等のビジネス的な変化]
  - [具体例]
- LLM分析の評価: [有用だったか、的外れだったか等]
  - [詳細]
- UI/UX改善点: [使いにくかった点、バグ、欲しい機能]
  - [具体的な改善要望]
- 従来手法との比較: [Excel等で同じことをやる場合と比較]
  - [詳細]
- 所要時間:
  - Prism=X分 vs 手作業=Y分
- 継続利用意向:
  - [この回の実感]
- 備考:
  - [その他]


---

## E-2-2-6: 第6回比較

### E-2-2-6-0: 比較テスト実施

**実施日**: YYYY/MM/DD
**データ**: 継続収集データを使用

- base: dataset_id=X (YYYY/MM/DD収集)
- target: dataset_id=Y (YYYY/MM/DD収集)
- 統計差分（数値）: [行数変化、価格変化等の数値的な要点]
  - [詳細]
- 発見した変化（データ内容）: [案件内容の傾向、価格帯、カテゴリ等のビジネス的な変化]
  - [具体例]
- LLM分析の評価: [有用だったか、的外れだったか等]
  - [詳細]
- UI/UX改善点: [使いにくかった点、バグ、欲しい機能]
  - [具体的な改善要望]
- 従来手法との比較: [Excel等で同じことをやる場合と比較]
  - [詳細]
- 所要時間:
  - Prism=X分 vs 手作業=Y分
- 継続利用意向:
  - [この回の実感]
- 備考:
  - [その他]

---

## 総合評価（E-2-2完了時）

**位置づけ**: E-2-2の全比較テスト（E-2-2-1～6）と改善タスク（E-2-2-1-1～8）の総括

- 実施回数: N回（改善前1回、改善後M回）
- 改善タスクの実施状況:
  - 実施した改善: [E-2-2-1-1～8のどれを実施したか]
  - 実施しなかった項目とその理由: [...]
- 改善前後での変化:
  - 改善前（E-2-2-1-0）: 継続利用しない。統計差分に偏り、価値なし
  - 改善後（E-2-2-2-0以降）: [評価がどう変わったか]
- 時間短縮効果: 平均X%削減
- 最も価値を感じた点: [...]
- 改善が必要な点: [残っている課題]
- 「キラー機能」として成立するか: Yes/No、理由: [...]
  - 改善前の評価（E-2-2-1-0）: No（統計差分では価値なし）
  - 改善後の評価: [Yes/No、理由]
- 継続利用意向: [最終的な判断]

---

* [ ] E-2-3. 単発分析機能のテスト（ペルソナA, B・並行実施）
  * [ ] シナリオ1: データ販売者の納品業務
  * [ ] シナリオ2: せどり実践者の価格差分析
  * [ ] 不便な点、欲しい機能をメモ
  * [ ] 従来手法との時間比較を記録

**実施記録（E-2-3）**：

【シナリオ1】実施日: YYYY/MM/DD
- データ: [...]
- 所要時間: Prism=X分 vs 手作業=Y分
- 評価: [...]
- 欲しい機能: [...]


【シナリオ2】実施日: YYYY/MM/DD
- データ: [...]
- 所要時間: Prism=X分 vs 手作業=Y分
- 評価: [...]
- 欲しい機能: [...]

* [ ] E-2-4. フィードバックの最終まとめ
  * [ ] 定量データの集計
  * [ ] 定性データのまとめ
  * [ ] 支払い意向の評価

**最終フィードバック（E-2完了時）**：

【定量データ】
- テスト期間: YYYY/MM/DD ～ YYYY/MM/DD (N日間)
- 推移比較実施回数: N回
- 単発分析実施回数: M回
- 平均時間短縮率: X%
- エラー・不具合発生回数: Y回


【定性データ】
- 最も便利だった機能: [...]
- 最も不便だった点: [...]
- 欲しい機能（優先度順）:
  1. [...]
  2. [...]
  3. [...]
- 推移比較機能の価値評価: [5段階評価]
- 継続利用意向: [5段階評価]
- 支払い意向: 月額 ¥X まで払える理由: [...]


【総合所感】
[自由記述]

---

### E-3. 収益化可能性の検証（自己評価ベース）

**前提**: E-2のテスト完了後、自分の実感をもとに評価する

* [ ] E-3-1. ターゲット顧客の再評価
  * [ ] どのペルソナ（A/B/C）に最も刺さったか
  * [ ] 個人開発者 vs 企業チーム（どちらがメインか）
  * [ ] 業種・職種の絞り込み（マーケター、データアナリスト、スクレイピング実践者など）
  * [ ] 推移比較機能の価値を最も感じるユーザー層の特定

* [ ] E-3-2. 価値提案の明確化
  * [ ] 本ツールが解決する問題は何か（自分の実感ベースで記述）
  * [ ] 既存の代替手段（Excel、手作業）との差別化
  * [ ] **推移比較機能がなぜ差別化要因になるか**（最重要）
  * [ ] 時間短縮効果の定量化（従来手法 vs Prism）
  * [ ] 分析の質の向上（気づき・発見が増えたか）

* [ ] E-3-3. 収益モデルの検討
  * [ ] 自分が払える金額の検討
    * [ ] 月額いくらまで払ってもよいか？
    * [ ] どの機能に最も価値を感じるか？
  * [ ] 課金対象の候補
    * [ ] 分析回数（月10回まで無料、それ以上は有料など）
    * [ ] データ量（行数、ファイルサイズ制限）
    * [ ] 推移比較回数（無制限は有料など）
    * [ ] LLM分析の品質（高性能モデルは有料など）
  * [ ] 価格帯の仮説
    * [ ] 個人向け：月額 ¥500-2,000 程度？
    * [ ] 企業向け：月額 ¥5,000-20,000 程度？
  * [ ] 競合調査（類似ツールの価格帯を調査）

* [ ] E-3-4. 継続利用意向の自己評価
  * [ ] 自分自身が実際の業務で使い続けたいか？
  * [ ] 推移比較機能があれば、定期的に使いたいと思えるか？
  * [ ] 他人に勧めたいと思えるか？
  * [ ] サブスク型（月額課金）が妥当か、従量課金が良いか？

---

### E-4. 次フェーズへの判断（Go/No-Go/Pivot）

**詳細**: `docs/E2_User_Test_Plan.md` の「8. 成功基準」を参照

* [ ] E-4-1. 定量・定性データの整理
  * [ ] 定量データのまとめ
    * [ ] 時間短縮効果（従来手法との比較）
    * [ ] 推移比較の実施回数と発見数
    * [ ] エラー・不具合の発生状況
  * [ ] 定性データのまとめ
    * [ ] 最も価値を感じた機能
    * [ ] 推移比較機能の評価
    * [ ] 継続利用意向
    * [ ] 支払い意向

* [ ] E-4-2. Go/No-Go/Pivot判断

**Goの基準（本格開発へ進む）** - 以下の4つすべてを満たすこと：
  * [ ] 1. **推移比較機能の価値**: 「これこそが求めていた機能だ」と実感できる
  * [ ] 2. **時間短縮**: 従来手法と比べて **30%以上の時間短縮** を実感
  * [ ] 3. **継続利用意向**: 自分自身が **実際の業務で使い続けたい** と思える
  * [ ] 4. **支払い意向**: もし有料サービスなら **月額1,000円以上払ってもよい** と思える
  * [ ] 5. **技術的成立**: 大きな技術的問題（パフォーマンス、バグ等）がない

**Pivotの基準（方向転換）** - 以下のような場合：
  * [ ] 単発分析は便利だが、推移比較はそこまで重要でない → ターゲット顧客を再検討
  * [ ] 統計情報は好評だが、LLM分析が不要 → LLMなしの軽量版を検討
  * [ ] ペルソナA, Bは刺さらないが、ペルソナCには強く刺さる → ターゲットを絞る
  * [ ] 推移比較は良いが、手動選択が面倒 → 自動比較機能を優先実装

**No-Goの基準（中止またはロングスリープ）** - 以下の場合：
  * [ ] 推移比較機能を使っても「手作業の方が良い」と感じる
  * [ ] 技術的に解決困難な問題が多発（LLMコスト、パフォーマンス等）
  * [ ] 自分自身が使い続けたいと思えない
  * [ ] 支払い意向が **月額500円未満**（事業化困難）

* [ ] E-4-3. 判断結果の記録
  * [ ] 判断（Go / Pivot / No-Go）を明記
  * [ ] 判断理由の明文化（定量・定性データを根拠に）
  * [ ] 推移比較機能の評価（最重要）
  * [ ] 次フェーズのスコープ確定（Goの場合）
  * [ ] Pivot内容の明確化（Pivotの場合）
  * [ ] 得られた知見のまとめ（No-Goの場合も記録）

---

## フェーズE-5：開発効率化（フェーズF前の準備）

**目的**: フェーズFの本格開発に向けて、開発環境を効率化します。

### E-5-1. フロントエンド開発環境のボリュームマウント化

**背景**: 現在の開発環境では、ソースコード変更のたびにDockerコンテナの再ビルドが必要で、開発サイクルが遅い。

* [ ] E-5-1-1. docker-compose.ymlの更新
  * [ ] frontend サービスにボリュームマウント設定を追加
    * [ ] `./frontend/src:/app/src:ro` - ソースコードをマウント
    * [ ] `./frontend/public:/app/public:ro` - 公開ファイルをマウント
    * [ ] `/app/node_modules` - node_modulesは除外
  * [ ] Windows対応の環境変数を追加
    * [ ] `CHOKIDAR_USEPOLLING=true` - ホットリロード対応

* [ ] E-5-1-2. 動作確認
  * [ ] ソースコード変更が即座に反映されることを確認
  * [ ] Viteのホットリロードが正常に動作することを確認
  * [ ] package.json変更時は再ビルドが必要なことを確認

* [ ] E-5-1-3. ドキュメント更新
  * [ ] `docs/setup_guide.md` に開発環境と本番ビルドの違いを記載
  * [ ] `README.md` に開発時の注意事項を追記

**期待される効果**:
- コード変更→確認のサイクルが 1-2分 → 1-2秒 に短縮
- Dockerキャッシュの問題を回避
- 開発体験の大幅な向上

**注意事項**:
- 本番ビルド時は従来どおり Dockerfile の COPY 方式を使用
- package.json 変更時のみ `docker compose build frontend` が必要

**関連Issue**: [開発効率化] フロントエンド開発環境をボリュームマウント方式に変更

---

## フェーズF：実用化のための追加機能（フェーズE後に必要に応じて実施）

**前提**：フェーズEの結果「本格開発に進む」と判断した場合のみ実施します。

### F-0. 実用化の土台（先に整備）

* [ ] F-0-1. 認証・認可の実装（最低限）
  * [ ] ユーザー登録・ログイン機能
  * [ ] データセットの所有権管理（他人のデータセットは見れない）
  * [ ] セッション管理またはJWT認証

* [ ] F-0-2. デプロイ環境の整備
  * [ ] 本番環境の選定（AWS/GCP/Azure/Heroku/Render等）
  * [ ] HTTPS対応
  * [ ] 環境変数の管理（Secrets Manager等）
  * [ ] バックアップ戦略の策定

* [ ] F-0-3. 監視・ログの整備
  * [ ] エラー通知（Sentry等）
  * [ ] メトリクス収集（レスポンスタイム、エラー率）
  * [ ] コスト監視（LLM API使用量）

---

### F-1. データ管理の改善

* [ ] F-1-1. データセットのメタ情報編集
  * [ ] データセット名の変更機能
  * [ ] 説明文の追加機能
  * [ ] タグ付け機能（検索用）

* [ ] F-1-2. 検索・フィルタリング機能
  * [ ] データセット一覧の検索（ファイル名、タグ）
  * [ ] 並び替え（作成日、ファイル名、行数）
  * [ ] ページネーション（大量データセット対応）

* [ ] F-1-3. データ保持ポリシー
  * [ ] 古いデータセットの自動削除（30日後など）
  * [ ] データ保持期限の通知

---

### F-2. 分析の高度化

* [ ] F-2-1. カスタムプロンプト機能
  * [ ] ユーザーが分析観点を指定できるようにする
    * [ ] 例：「売上に影響する要因を見つけて」
    * [ ] 例：「異常値を指摘して」
  * [ ] プロンプトテンプレートの提供（初心者向け）

* [ ] F-2-2. 分析履歴の保存
  * [ ] 同じデータセットに対する複数回の分析を保存
  * [ ] 過去の分析結果との比較
  * [ ] 分析結果へのメモ追加機能

* [ ] F-2-3. 推移比較機能の高度化（E-0で基本機能は実装済み）
  * [ ] 3つ以上のデータセットを並べて比較（時系列グラフ化）
  * [ ] 自動比較機能（同一ファイル名パターンを自動検出して比較候補を提示）
  * [ ] 比較履歴の保存・管理
  * [ ] 定期比較のスケジュール設定（週次・月次での自動比較）
  * [ ] 変化の閾値設定（例：価格が10%以上変化したら通知）

* [ ] F-2-4. グラフのカスタマイズ
  * [ ] 表示するカラムの選択
  * [ ] グラフ種類の切替（棒グラフ、折れ線グラフ、散布図）
  * [ ] グラフの画像エクスポート

---

### F-3. ワークフロー改善

* [ ] F-3-1. エクスポート機能の拡充
  * [ ] PDF形式でのレポート出力
  * [ ] Excel形式での統計情報出力
  * [ ] PowerPoint形式でのプレゼン資料生成（オプション）

* [ ] F-3-2. 共有機能
  * [ ] 分析結果の共有リンク生成（閲覧専用）
  * [ ] チームメンバーとのデータセット共有
  * [ ] コメント・レビュー機能

* [ ] F-3-3. スケジュール実行（高度）
  * [ ] 定期的なCSVアップロード（API連携）
  * [ ] 自動分析の実行
  * [ ] 結果のメール通知

---

### F-4. パフォーマンス・スケーラビリティ

* [ ] F-4-1. 大容量CSV対応
  * [ ] ストリーミング処理の導入
  * [ ] チャンク単位での読み込み・保存
  * [ ] 100MB以上のファイル対応

* [ ] F-4-2. 統計処理の最適化
  * [ ] 集計結果のキャッシュ
  * [ ] バックグラウンドジョブ化（Celery等）
  * [ ] インデックスの最適化

* [ ] F-4-3. フロントエンドの最適化
  * [ ] 仮想スクロール（大量行の表示）
  * [ ] 遅延ロード（グラフ、画像）
  * [ ] ビルドサイズの削減

---

### F-5. セキュリティ強化

* [ ] F-5-1. 入力バリデーション強化
  * [ ] CSVヘッダーの厳密な検証
  * [ ] カラム名のサニタイゼーション
  * [ ] 悪意のあるファイルの検出

* [ ] F-5-2. レート制限
  * [ ] API呼び出しの制限（1時間あたり100回など）
  * [ ] アップロードサイズの厳格化
  * [ ] LLM呼び出しの上限設定

* [ ] F-5-3. 個人情報検出
  * [ ] PII（Personally Identifiable Information）の検出
  * [ ] 機微情報を含む場合の警告表示
  * [ ] LLMへの送信前のマスキング処理

---

### F-6. 収益化機能の実装

* [ ] F-6-1. 課金システムの導入
  * [ ] Stripe等の決済システム連携
  * [ ] プラン管理（Free / Pro / Enterprise等）
  * [ ] 使用量の計測（分析回数、データ量）

* [ ] F-6-2. プラン別機能制限
  * [ ] Freeプラン：月10回まで、100MB以下
  * [ ] Proプラン：月100回まで、1GB以下、カスタムプロンプト可能
  * [ ] Enterpriseプラン：無制限、共有機能、優先サポート

* [ ] F-6-3. ユーザーダッシュボード
  * [ ] 使用量の可視化
  * [ ] プランのアップグレード/ダウングレード
  * [ ] 請求書・領収書の発行

---

## 補足：フェーズE完了後の振り返り（予定地）

フェーズEの実施後、以下を記録してください：

* [ ] テスト期間と実施内容のサマリー
* [ ] 推移比較機能の評価（最重要）
  * [ ] 「キラー機能」として成立したか
  * [ ] LLM推移分析の精度・有用性
  * [ ] 継続利用意向
* [ ] 定量データ
  * [ ] 時間短縮効果（従来手法との比較）
  * [ ] 推移比較の実施回数と発見数
  * [ ] エラー・不具合の発生状況
* [ ] 定性データ
  * [ ] 最も価値を感じた機能
  * [ ] 不便だった点、欲しい機能
  * [ ] 支払い意向（月額いくらまで？）
* [ ] Go/No-Go/Pivot判断の結果と理由
* [ ] フェーズFで優先する機能（Goの場合）
* [ ] 得られた知見のまとめ

---
