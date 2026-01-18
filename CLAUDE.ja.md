# CLAUDE.md - AIアシスタント向けプロジェクトガイド


> このドキュメントは、Claude等のAIアシスタントがPrismプロジェクトを理解し、効果的な開発支援を行うための情報をまとめたものです。

**最終更新**: 2026/01/18  
**プロジェクトバージョン**: PoC v0.1.0  
**現在のフェーズ**: E-2（実ユーザーテスト）Phase 1実装中

---

## このドキュメントの使い方（AI向け重要指示）

- 本ドキュメントは事実の唯一の正とする
- 記載されていない仕様・設計は推測しないこと
- 既存コード・モデル・テストを必ず確認してから提案すること
- PoC段階で「意図的にやらないこと」は提案対象外とする
- 最重要機能は「推移比較機能」であり、他機能より常に優先する


## AIに期待する主な支援内容

- 新機能実装時の影響範囲整理
- 既存設計を壊さない改善案の提示
- テストケースの網羅性チェック
- プロンプト改善案のレビュー
- ビジネス視点での分析結果評価



---

## 目次

1. [プロジェクト概要](#1-プロジェクト概要)
2. [技術スタック](#2-技術スタック)
3. [プロジェクト構造](#3-プロジェクト構造)
4. [開発環境](#4-開発環境)
5. [開発フロー](#5-開発フロー)
6. [テスト戦略](#6-テスト戦略)
7. [コーディング規約](#7-コーディング規約)
8. [重要な設計判断](#8-重要な設計判断)
9. [現在の進捗状況](#9-現在の進捗状況)
10. [よくあるタスクの手順](#10-よくあるタスクの手順)
11. [注意事項](#11-注意事項)

---

## 1. プロジェクト概要

### プロジェクト名
**Prism** - スクレイピングデータ分析基盤

### 目的
スクレイピングで取得したCSVデータに対して、統計分析とLLM（Gemini）による自動分析を提供し、データからビジネスインサイトを得るための基盤。

### 最重要機能（キラー機能）
**推移比較機能**: 同一対象を継続的にスクレイピングしたデータセットを比較し、変化・トレンドを自動分析する機能。これがPrismの差別化要因であり、継続利用（サブスク化）の根拠となる。

### 位置づけ
- **PoC（Proof of Concept）段階**: 技術的実現性と価値検証を同時に実施
- **失敗してもよいPoC**: 判断材料と学習が残ることを唯一の成功条件とする
- **自社テスト中心**: 外部ユーザーテストは不要、自分自身が使って価値を検証する

### 主要機能
1. CSVアップロード（UTF-8 / Shift_JIS対応）
2. PostgreSQLへのデータ格納（JSONB形式）
3. 基本統計情報の算出（数値/文字列カラムの要約）
4. LLM（Gemini）による分析コメント生成
5. **推移比較機能**（2つのデータセット比較）
6. **価格帯分析**（UnitPriceからの価格帯分類と増減分析）
7. **キーワード分析**（Titleからの技術キーワード抽出と増減分析）
8. Webブラウザでの閲覧（一覧/詳細/グラフ表示/比較画面）
9. データセット削除機能
10. 分析結果のエクスポート（Markdown, CSV, クリップボードコピー）

---

## 2. 技術スタック

### Backend
- **言語**: Python 3.x
- **フレームワーク**: FastAPI 0.115.6
- **Webサーバー**: Uvicorn 0.32.1
- **ORM**: SQLAlchemy 2.0.36
- **DB接続**: psycopg 3.2.3（PostgreSQL用、v3のBinary版）
- **マイグレーション**: Alembic 1.13.1
- **LLM**: Google Gemini API（gemini-2.0-flash）
- **テスト**: pytest 8.3.4, pytest-cov 6.0.0
- **HTTPクライアント**: httpx 0.28.1

### Frontend
- **言語**: TypeScript 5.6.3
- **フレームワーク**: React 18.3.1
- **ルーティング**: react-router-dom 7.12.0
- **ビルドツール**: Vite 5.4.10
- **グラフ**: Recharts 2.13.3
- **テスト**: Vitest 2.1.9

### Database
- **RDBMS**: PostgreSQL 16
- **特徴**: JSONB型を使用したスキーマレスデータ格納

### Infrastructure
- **コンテナ**: Docker + Docker Compose V2
- **CI/CD**: GitHub Actions
- **開発環境**: Windows 11 + Git Bash
- **本番環境**: 未定（AWS/GCP/Azure等を検討）

---

## 3. プロジェクト構造

```
prism2/
├── .github/
│   └── workflows/
│       └── ci.yml                # GitHub Actions CI設定
├── backend/
│   ├── alembic/
│   │   ├── versions/             # マイグレーションファイル
│   │   └── env.py                # Alembic設定
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py               # FastAPIアプリケーション本体
│   │   ├── analysis.py           # 統計分析・LLM分析ロジック
│   │   ├── db.py                 # DB接続設定
│   │   ├── keywords.py           # 技術キーワードリスト（約150語）
│   │   ├── llm.py                # LLMクライアント抽象化
│   │   └── models.py             # SQLAlchemyモデル定義
│   ├── tests/
│   │   ├── conftest.py           # pytestフィクスチャ
│   │   ├── test_*.py             # ユニットテスト（15ファイル、81テスト）
│   │   └── ...
│   ├── Dockerfile                # Backend Dockerイメージ
│   ├── entrypoint.sh             # コンテナ起動スクリプト
│   ├── requirements.txt          # Python依存パッケージ
│   ├── alembic.ini               # Alembic設定
│   └── pytest.ini                # pytest設定（カバレッジ80%以上）
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   │   ├── datasets.ts       # API呼び出し関数
│   │   │   └── datasets.test.ts  # APIテスト（20テスト）
│   │   ├── pages/
│   │   │   ├── DatasetListPage.tsx        # 一覧画面
│   │   │   ├── DatasetDetailPage.tsx      # 詳細画面
│   │   │   ├── DatasetComparePage.tsx     # 推移比較画面
│   │   │   └── UploadPage.tsx             # アップロード画面
│   │   ├── App.tsx               # ルーティング定義
│   │   └── main.tsx              # エントリポイント
│   ├── Dockerfile                # Frontend Dockerイメージ
│   ├── package.json              # Node.js依存パッケージ
│   ├── tsconfig.json             # TypeScript設定
│   └── vite.config.ts            # Vite設定
├── docs/
│   ├── develop_process.md        # 開発プロセス・タスク進捗（2412行）
│   ├── Requirements Definition.md # 要件定義書
│   ├── E2_User_Test_Plan.md      # 実ユーザーテスト計画
│   ├── setup_guide.md            # セットアップガイド
│   └── env.example               # 環境変数サンプル
├── samples/
│   ├── comparison_4_9_20260115.md # 推移比較レポートサンプル
│   ├── playwright_scrape_sample.csv # サンプルCSV
│   └── README.md                 # サンプルファイルの説明
├── docker-compose.yml            # 3サービス構成（frontend/backend/db）
├── .gitignore                    # Git管理除外設定
├── README.md                     # プロジェクト概要・起動手順
└── CLAUDE.md                     # 本ファイル（AI向けガイド）
```

### データベーススキーマ

```sql
-- datasets: データセットのメタ情報
CREATE TABLE datasets (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

-- dataset_rows: データセットの行データ（JSONB）
CREATE TABLE dataset_rows (
    id SERIAL PRIMARY KEY,
    dataset_id INTEGER NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
    row_index INTEGER NOT NULL,
    data JSONB NOT NULL,  -- カラム名と値をJSON形式で格納
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);
```

**重要**: 
- `data`カラムは`JSONB`型で、CSVの1行がJSON形式で格納される
- 例: `{"Title": "Python案件", "UnitPrice": "50万円/月", "SkillTags": "Python,Django"}`
- `ON DELETE CASCADE`により、データセット削除時に関連行も自動削除

---

## 4. 開発環境

### 必須ソフトウェア
- Docker Desktop（Windows 11）
- Git for Windows（Git Bash）
- テキストエディタ（VS Code推奨）

### 環境変数
`.env`ファイルをリポジトリルートに作成（`docs/env.example`を参照）

```env
# LLM機能（使わない場合は0）
ANALYSIS_USE_LLM=1
LLM_PROVIDER=gemini
LLM_API_KEY=YOUR_GEMINI_API_KEY_HERE
LLM_MODEL=gemini-2.0-flash
LLM_TIMEOUT_SECONDS=20
GEMINI_API_BASE_URL=https://generativelanguage.googleapis.com

# DB設定（デフォルトで問題なければ不要）
POSTGRES_DB=prism
POSTGRES_USER=prism
POSTGRES_PASSWORD=prism_password

# CORS設定
CORS_ALLOW_ORIGINS=http://localhost:3001,http://127.0.0.1:3001
```

**注意**: APIキーは絶対にコミットしないこと（`.gitignore`で除外済み）

### 起動手順

```bash
# 1. イメージビルド（初回のみ）
docker compose build

# 2. サービス起動
docker compose up -d

# 3. 動作確認
curl http://localhost:8001/health
# {"status":"ok"}

# 4. ブラウザで確認
# Frontend: http://localhost:3001/
# API Docs: http://localhost:8001/docs
```

### ポート構成
- Frontend: `http://localhost:3001` (ホスト) → 3000 (コンテナ)
- Backend: `http://localhost:8001` (ホスト) → 8000 (コンテナ)
- Database: 外部公開なし（内部ネットワークのみ）

---

## 5. 開発フロー

### 重要な原則
1. **ローカル環境を汚さない**: Python/Node.jsは一切インストールせず、全てDockerコンテナ内で実行
2. **テストファースト**: 機能追加時は必ずテストを作成し、カバレッジ80%以上を維持
3. **コミット前の確認**: テスト実行、Lintチェック、ビルド成功を確認してからコミット

### ブランチ戦略
- `main`: 本番リリース用（現在未使用）
- `develop`: 開発ブランチ（デフォルト）
- 機能ブランチ: 必要に応じて作成（現状は直接developにコミット）

### コードを変更した場合

#### Backend（Python）
```bash
# コード変更後は再ビルドが必要（COPY型のため）
docker compose build backend
docker compose up -d backend

# ログ確認
docker compose logs -f backend
```

#### Frontend（TypeScript/React）
```bash
# コード変更後は再ビルドが必要（COPY型のため）
docker compose build --no-cache frontend
docker compose up -d frontend

# ブラウザでハードリロード（Ctrl+Shift+R）
```

**注意**: 現在の開発環境ではホットリロードが効かないため、コード変更のたびに再ビルドが必要。E-5-1でボリュームマウント方式に変更予定。

---

## 6. テスト戦略

### Backend テスト

#### テスト実行
```bash
# テスト用DBを起動（開発用DBと分離）
docker compose -p prism2-test up -d db

# Backend再ビルド（ソースコード変更時）
docker compose -p prism2-test build backend

# スキーマ適用
docker compose -p prism2-test run --rm -e RUN_MIGRATIONS=0 backend alembic upgrade head

# テスト実行
docker compose -p prism2-test run --rm -e RUN_MIGRATIONS=0 backend pytest

# カバレッジ付きテスト
docker compose -p prism2-test run --rm -e RUN_MIGRATIONS=0 backend pytest --cov=app --cov-report=term-missing

# クリーンアップ
docker compose -p prism2-test down -v
```

#### テストカバレッジ
- **目標**: 80%以上（`pytest.ini`で強制）
- **現状**: 90.53%（81テスト）
- **重要**: 新機能実装時は必ずテストを追加し、カバレッジを維持すること

#### テストファイル構成
```
backend/tests/
├── conftest.py                      # Fixture定義
├── test_health.py                   # ヘルスチェックAPI
├── test_datasets_upload.py          # CSVアップロード
├── test_datasets_list.py            # データセット一覧
├── test_dataset_detail.py           # データセット詳細
├── test_dataset_stats.py            # 統計情報API
├── test_dataset_analysis.py         # LLM分析API
├── test_dataset_compare.py          # 推移比較API
├── test_comparison_analysis.py      # 推移比較LLM分析API
├── test_dataset_delete.py           # データセット削除
├── test_price_analysis.py           # 価格帯分析（19テスト）
├── test_keyword_analysis.py         # キーワード分析（13テスト）
├── test_llm_client.py               # LLM抽象化層
├── test_gemini_client.py            # Geminiクライアント
├── test_prompt_v1.py                # プロンプトv1
└── test_prompt_v2.py                # プロンプトv2（実装予定）
```

### Frontend テスト

#### テスト実行
```bash
cd frontend
npm test  # Vitest実行
```

#### テストカバレッジ
- **現状**: 20テスト（`src/api/datasets.test.ts`）
- **対象**: API呼び出し関数のロジック
- **今後**: コンポーネントのレンダリングテストも追加予定


### テスト完了の定義（非常に重要）

  **ユニットテストが通過しただけでは実装完了ではない。**

  #### 完了の条件
  1. ✅ **ユニットテスト通過** - pytest実行、カバレッジ80%以上
  2. ✅ **実際の動作確認** - ブラウザで実際のデータを使って動作確認
  3. ✅ **ビジネス価値の検証** - 特にLLM分析結果が実用的か人間の目で判断

  #### プロンプト変更時の必須確認事項
  - プロンプトv1→v2のような変更では、**LLM出力の品質が最重要**
  - ユニットテストはプロンプト構造のみを検証（品質は検証しない）
  - **必ずブラウザで実行し、生成された分析コメントを人間が読んで評価する**

  #### 例：プロンプトv2実装時の完了チェックリスト
  - [ ] ユニットテスト通過（test_prompt_v2.py）
  - [ ] 全体カバレッジ80%以上維持
  - [ ] 開発環境起動（docker compose up -d）
  - [ ] ブラウザで推移比較画面を開く
  - [ ] 実際のデータセットで比較実行
  - [ ] LLM分析結果を確認：ビジネス価値があるか？
  - [ ] 問題があれば修正してループ、良ければ完了

  ### テスト用データの保護（重要）

  #### E2Eテスト用DBの扱い

  **現在のフェーズ（E-2）では、テスト用DBに蓄積データが含まれる可能性がある。**

  E2_User_Test_Plan.mdに記載の通り：
  - Week 2-3: 同一対象を週2-3回スクレイピング（計4-6回分のデータセット）
  - 各回のデータを蓄積し、継続的に比較する
  - **データセットは保持し続ける必要がある**

  #### 絶対にやってはいけないこと
  - ❌ `docker compose -p prism2-test down -v` （`-v`フラグでボリューム=DBデータが削除される）

  #### 正しいクリーンアップ
  - ✅ `docker compose -p prism2-test down` （コンテナのみ停止、データは保持）
  - ✅ または、起動したまま放置（次回テスト時にそのまま使える）

  #### データ削除が許可される場合
  - ユニットテストのみの実行後（E2Eテストデータが入っていない場合）
  - ユーザーが明示的に「データをリセットしたい」と指示した場合のみ

  **原則**: データ削除は慎重に。迷ったら削除しない。

  ### AI実行時の必須確認事項

  #### コマンド提案時のルール

  **全てのコマンド提案時に、以下を必ず含める：**

  1. **コマンドの各パラメータの意味**
  2. **コマンドの目的** - 何をするためのコマンドか、なぜ今実行する必要があるのか
  3. **影響範囲** - データが削除されるか、復元可能か

  #### 関連ドキュメントの確認必須

  **新しいタスクに着手する前に、必ず以下を確認：**

  1. `docs/develop_process.md` - タスクの詳細仕様と背景
  2. `docs/E2_User_Test_Plan.md` - 現在のフェーズ（E-2）の目的と制約
  3. `backend/app/models.py` - データベース定義（推測禁止）
  4. 既存の類似実装 - パターンの確認

  **「読んだと思う」ではなく、実際に読む。**

  #### プロジェクト文脈の理解

  **現在のフェーズ（E-2）の目的を常に意識：**
  - **ビジネス価値の検証**が最優先
  - 技術的に動作する ≠ ビジネス価値がある
  - 特にLLM分析は、人間が読んで「使える」と思えるかが重要
  - ユニットテストだけで完了と判断しない

---

## 7. コーディング規約

### Python（Backend）
- **変数名**: キャメルケース（例: `datasetId`, `rowCount`）
- **関数名**: 動詞から始める（例: `getDataset`, `calculateStats`, `buildPrompt`）
- **インデント**: スペース4つ
- **コメント**: 関数の冒頭にdocstringで目的を記述
- **型ヒント**: SQLAlchemy 2.xの`Mapped`型を使用
- **例外処理**: FastAPIの`HTTPException`を使用、適切なステータスコードを設定

```python
def calculateStats(datasetId: int) -> dict:
    """目的: データセットの統計情報を計算する"""
    # 実装
    pass
```

### TypeScript（Frontend）
- **変数名**: キャメルケース（例: `datasetId`, `rowCount`）
- **関数名**: 動詞から始める（例: `fetchDatasets`, `uploadFile`）
- **インデント**: スペース4つ
- **型定義**: 全ての関数・変数に型を明示
- **API呼び出し**: `src/api/datasets.ts`に集約

```typescript
export async function getDatasetDetail(datasetId: number): Promise<DatasetDetailResponse> {
    const response = await fetch(`${API_BASE_URL}/datasets/${datasetId}`);
    if (!response.ok) {
        throw new Error(`Failed to fetch dataset detail: ${response.status}`);
    }
    return response.json();
}
```

### コメントのルール
- **複雑なロジック**: 適宜コメントを追加（「なぜ」を書く）
- **TODO**: `# TODO: [内容]` または `// TODO: [内容]`
- **FIXME**: `# FIXME: [内容]` または `// FIXME: [内容]`
- **HACK**: 一時的な対処の場合は `# HACK: [理由]` と明記

---

## 8. 重要な設計判断

### 8.1 データベース設計

#### JSONB採用の理由
- CSVのカラム構成が可変（スクレイピング対象により異なる）
- スキーマレスでデータを格納できる
- PostgreSQLのJSONB型は高速で、インデックスも張れる

#### CASCADE削除
- データセット削除時に`dataset_rows`も自動削除
- 理由: 行データだけが残っても意味がない

### 8.2 LLM統合

#### プロバイダ抽象化
- `LLMClient`インターフェースを定義し、実装を差し替え可能に
- 現在はGeminiのみ実装（将来的にOpenAI等も追加可能）
- テスト時はモックで差し替え

#### エラーハンドリング
```python
LLMTimeoutError      → 504 Gateway Timeout (retryable)
LLMAuthError         → 503 Service Unavailable (non-retryable)
LLMRateLimitError    → 503 Service Unavailable (retryable)
LLMInputTooLargeError → 413 Payload Too Large (non-retryable)
LLMProviderError     → 502 Bad Gateway (retryable)
```

#### プロンプト設計
- **v1（現行）**: 統計差分にフォーカス、技術的指標を分析
- **v2（実装中）**: ビジネス文脈重視、価格帯・キーワード・スキル・カテゴリの変化を優先

### 8.3 推移比較機能の設計

#### 比較データの永続化
- **現在**: APIレベルのみで比較、DB保存なし（案C採用）
- **理由**: PoC段階では「動く」ことが最優先、比較履歴の価値は未検証
- **将来**: 価値が確認できたら`dataset_comparisons`テーブルで永続化（案A）

#### 価格帯分析
- **高単価**: 80万円以上
- **中単価**: 50-80万円
- **低単価**: 50万円未満
- **不明**: 解析不可

価格文字列（例: "80万円/月", "50-60万円"）から数値を抽出し、分類する。

#### キーワード分析
- 技術キーワードリスト（約150語）を`backend/app/keywords.py`に定義
- Titleからキーワードを抽出し、base/targetで増減を比較
- 大文字小文字を区別しないマッチング

### 8.4 PoCで意図的にやらないこと

**セキュリティ**:
- 認証・認可なし
- SQLインジェクション対策は最小限（SQLAlchemyのパラメータ化のみ）
- XSS対策はReactのデフォルト機能のみ
- CSRF対策なし
- レート制限なし

**データの永続性**:
- バックアップ機能なし
- データ保持期限なし

**パフォーマンス**:
- 大容量CSV未対応（100MB以上は失敗する可能性）
- ページネーションなし（全件取得）
- キャッシュなし

**理由**: これらは本番運用時に必要だが、PoC段階では価値検証を優先し、実装を先送りする。

---

## 9. 現在の進捗状況

### 完了フェーズ
- ✅ **フェーズA**: PoCを「操作可能」にする必須タスク
- ✅ **フェーズB**: 分析PoCとしての中核機能
- ✅ **フェーズC**: 管理画面として最低限成立させる
- ✅ **フェーズD**: 安定性・PoC品質の底上げ
- ✅ **フェーズE-0**: 推移比較機能の実装（最重要機能）
- ✅ **フェーズE-1**: 最小限の使いやすさ改善

### 現在のフェーズ
**フェーズE-2: 実ユーザーテスト（自社テスト）Phase 1実装中**

#### Phase 1完了の条件
- [ ] E-2-2-1-1: 価格帯の分析機能追加（✅ 完了 2026/01/16）
- [ ] E-2-2-1-2: 案件内容のキーワード分析（✅ 完了 2026/01/16）
- [ ] E-2-2-1-3: プロンプトv2の実装（ビジネス文脈重視）← **現在ここ**
- [ ] Phase 1完了後、第2回比較テスト（E-2-2-2-0）を実施

#### 第1回比較テスト（E-2-2-1-0）の結果
- 実施日: 2026/01/15
- データ: ランサーズ開発案件リスト（2025/12/10 vs 2026/01/15、約1ヶ月）
- **致命的な問題点**: LLM分析がビジネス価値ゼロ
  - 行数やrowOrderなどの技術的指標のみを報告
  - 価格帯、案件内容、スキル需要の変化が完全に無視されている
  - アクションにつながる示唆が一切ない
- **継続利用意向**: ❌ 継続利用しない（改善前）

#### Phase 1の改善方針
1. ✅ **E-2-2-1-1**: 価格帯分析機能追加（完了）
   - 高/中/低単価の増減を分析
   - 実装結果: 高単価案件+180.0%、中単価+41.7%、低単価-13.4%というビジネス価値のある示唆を得られた
   
2. ✅ **E-2-2-1-2**: キーワード分析機能追加（完了）
   - 技術キーワードの増減を分析
   - 実装結果: Java+4件、TypeScript新規出現など、技術トレンドの把握が可能に
   
3. **E-2-2-1-3**: プロンプトv2実装（次のタスク）
   - 価格帯・キーワード情報を最優先で配置
   - 技術的指標を削除または最小化
   - ビジネス動向サマリー、推奨アクションを追加

### テスト実行状況
- Backend: 81テスト通過、カバレッジ90.53%（目標80%以上達成）
- Frontend: 20テスト通過
- CI: GitHub Actions で自動実行（全てグリーン）

---

## 10. よくあるタスクの手順

### 10.1 新しいAPIエンドポイントの追加

#### 手順
1. **仕様確認**: `docs/develop_process.md`で該当タスクの仕様を確認
2. **モデル確認**: `backend/app/models.py`で既存定義を確認（推測しない！）
3. **エンドポイント実装**: `backend/app/main.py`に追加
4. **ビジネスロジック実装**: `backend/app/analysis.py`に関数を追加
5. **テスト作成**: `backend/tests/test_*.py`に追加
6. **テスト実行**: カバレッジ80%以上を維持
7. **動作確認**: `curl`または`http://localhost:8001/docs`で確認

#### 例: 新しい統計情報エンドポイント
```python
# backend/app/main.py
@app.get("/datasets/{dataset_id}/custom-stats")
def getCustomStats(dataset_id: int):
    """目的: カスタム統計情報を返す"""
    logger.info(f"GET /datasets/{dataset_id}/custom-stats")
    db = SessionLocal()
    try:
        # 実装
        pass
    finally:
        db.close()

# backend/tests/test_custom_stats.py
def testGetCustomStatsSuccess(client, createDataset):
    datasetId = createDataset("test.csv", [{"col": "value"}])
    response = client.get(f"/datasets/{datasetId}/custom-stats")
    assert response.status_code == 200
```

### 10.2 プロンプトの変更・追加

#### 手順
1. **プロンプトテンプレート実装**: `backend/app/analysis.py`に`build_*_prompt_v*`関数を追加
2. **圧縮・整形関数**: 入力データを整形する関数を追加
3. **テスト作成**: `backend/tests/test_prompt_v*.py`に追加
4. **実データ検証**: `samples/`にテスト結果を保存
5. **品質確認**: 生成されたプロンプトとLLM出力をレビュー

#### 例: プロンプトv2実装
```python
# backend/app/analysis.py
def build_comparison_prompt_v2(
    base_meta: dict,
    target_meta: dict,
    price_analysis: dict,
    keyword_analysis: dict,
    stats_diff: dict
) -> str:
    """目的: ビジネス文脈重視のプロンプトv2を生成"""
    prompt = f"""あなたはデータアナリストです。以下の2つのデータセットの比較から、ビジネス上の変化を分析してください。

## 基準データ
ファイル名: {base_meta['filename']}
作成日時: {base_meta['created_at']}
行数: {base_meta['rows']}

## 比較対象データ
ファイル名: {target_meta['filename']}
作成日時: {target_meta['created_at']}
行数: {target_meta['rows']}

## 価格帯の変化
{format_price_analysis(price_analysis)}

## 案件内容のキーワード変化
{format_keyword_analysis(keyword_analysis)}

## 出力フォーマット
以下の形式で出力してください：

### ビジネス動向サマリー
[1-2文で全体像]

### 価格動向
[高/中/低単価の変化と示唆]

### 案件内容のトレンド
[増加キーワード、減少キーワード、技術トレンド]

### 推奨アクション
[具体的な次のアクション3-5つ]

### 前提・限界
[分析の前提条件、注意点]
"""
    return prompt
```

### 10.3 マイグレーションファイルの作成

#### 手順
1. **モデル変更**: `backend/app/models.py`を編集
2. **マイグレーション生成**: 
```bash
docker compose run --rm -e RUN_MIGRATIONS=0 backend alembic revision --autogenerate -m "変更内容の説明"
```
3. **ファイル確認**: `backend/alembic/versions/`に生成されたファイルを確認
4. **テスト実行**: マイグレーション適用後にテストを実行
5. **コミット**: マイグレーションファイルをコミット

#### 注意
- 自動生成されたファイルは必ず内容を確認すること
- 意図しない変更が含まれていないかチェック

### 10.4 Frontendコンポーネントの追加

#### 手順
1. **コンポーネント作成**: `frontend/src/pages/`または`frontend/src/components/`に追加
2. **API呼び出し**: `frontend/src/api/datasets.ts`に関数を追加
3. **ルーティング**: `frontend/src/App.tsx`にルートを追加
4. **テスト作成**: `frontend/src/api/datasets.test.ts`に追加
5. **ビルド・動作確認**: 
```bash
docker compose build --no-cache frontend
docker compose up -d frontend
# ブラウザで確認（ハードリロード: Ctrl+Shift+R）
```

### 10.5 CI/CDの確認

#### ローカルでCIと同じテストを実行
```bash
# Backend
docker compose -p prism2-test up -d db
docker compose -p prism2-test build backend
docker compose -p prism2-test run --rm -e RUN_MIGRATIONS=0 backend alembic upgrade head
docker compose -p prism2-test run --rm -e RUN_MIGRATIONS=0 backend pytest
docker compose -p prism2-test down -v

# Frontend
cd frontend
npm ci
npm test
npm run build
```

---

## 11. 注意事項

### 11.1 実装前の必須確認（非常に重要！）

**新機能実装時は、推測ではなく確認を優先する。特にデータベースモデルやAPIのような基盤部分は必ず既存定義を確認すること。**

#### 実装前の確認事項
1. **モデル定義の確認**: 使用するテーブル・カラムの実際の定義を`backend/app/models.py`で確認
2. **既存パターンの確認**: 類似機能の既存コードを`grep`検索して実装パターンを確認
```bash
# 例: DatasetRowのカラム名を確認
grep -r "DatasetRow\." backend/app/
```
3. **命名規則の確認**: プロジェクト内の命名規則を既存コードから確認

#### よくあるミス事例
```python
# ❌ 間違い（推測）
select(DatasetRow.jsonb)  # JSONBカラムだから"jsonb"だろう

# ✅ 正しい（models.pyで確認済み）
select(DatasetRow.data)   # 実際の定義は"data"
```

### 11.2 Dockerの注意事項

#### キャッシュの問題
- Dockerは`COPY . .`ステップをキャッシュするため、ソースコード変更が反映されない場合がある
- **解決策**: `docker compose build --no-cache <service>`でキャッシュなしビルド

#### ブラウザキャッシュ
- フロントエンド更新後もブラウザが古いJSを使用する場合がある
- **解決策**: ハードリロード（`Ctrl + Shift + R`）

#### テスト用DBの分離
- 開発用DBとテスト用DBは必ず分離すること（`-p prism2-test`を使用）
- 理由: テストはテーブルをTRUNCATEするため、開発データが消える

### 11.3 LLMの注意事項

#### APIキーの管理
- APIキーは`.env`ファイルに記載し、**絶対にコミットしない**
- Git履歴に残った場合はキーを無効化し、新しいキーを発行

#### コスト管理
- LLM呼び出しのたびにトークンが消費される
- 開発時は`ANALYSIS_USE_LLM=0`にしてモックで動作確認することを推奨

#### タイムアウト設定
- `LLM_TIMEOUT_SECONDS=20`がデフォルト
- 長いプロンプトの場合はタイムアウトする可能性があるため、プロンプトサイズに注意

### 11.4 テストの注意事項

#### カバレッジ80%以上の維持
- `pytest.ini`で`--cov-fail-under=80`を設定済み
- 80%未満の場合はCIが失敗する
- 新機能追加時は必ずテストを作成

#### モック/スタブの使用
- LLM呼び出しはテストでモックする
- 理由: 実際のAPI呼び出しはコストがかかり、テストが不安定になる

#### Fixtureの活用
- `backend/tests/conftest.py`に共通Fixtureを定義済み
- `createDataset`などのヘルパー関数を活用

### 11.5 Git運用の注意事項

#### コミット前の確認
1. テスト実行（Backend + Frontend）
2. Lintチェック（TypeScript）
3. ビルド成功確認
4. CI通過確認（プッシュ後）

#### コミットメッセージ
- 日本語OK（プロジェクト内は日本語が標準）
- 形式: `[機能名] 変更内容の要約`
- 例: `[推移比較] 価格帯分析機能を追加`

#### ブランチ戦略
- 現在は`develop`ブランチに直接コミット
- 大きな機能追加の場合はフィーチャーブランチを作成してもOK

### 11.6 ドキュメント更新

#### 開発プロセスの記録
- `docs/develop_process.md`は開発の履歴を残すドキュメント
- 実装完了後、実施記録を追記すること
- 失敗や課題も記録すること（将来の判断材料になる）

#### CLAUDE.mdの更新
- プロジェクトの構成や設計判断が変わった場合は本ファイルも更新
- 最終更新日を更新すること

---

## 付録A: 用語集

| 用語 | 説明 |
|------|------|
| PoC | Proof of Concept。技術的実現性と価値検証を同時に実施する段階。 |
| キラー機能 | 推移比較機能。Prismの最重要機能で差別化要因。 |
| JSONB | PostgreSQLのJSON型。バイナリ形式で高速、インデックス可能。 |
| Alembic | PythonのDBマイグレーションツール。SQLAlchemyと統合。 |
| Gemini | GoogleのLLM API。無料枠があり、速度も十分。 |
| プロンプトv1 | 統計差分にフォーカスした現行のプロンプト設計。 |
| プロンプトv2 | ビジネス文脈重視の新しいプロンプト設計（実装中）。 |
| 価格帯分析 | UnitPriceから価格帯（高/中/低）を分類し、増減を分析する機能。 |
| キーワード分析 | Titleから技術キーワードを抽出し、増減を分析する機能。 |
| 案C | 推移比較をAPIレベルのみで実装し、DB保存しない設計（現行）。 |

---

## 付録B: トラブルシューティング

### 問題1: テストが失敗する

**症状**: `pytest`実行時にテストが失敗する

**確認事項**:
1. テスト用DBが起動しているか: `docker compose -p prism2-test ps`
2. マイグレーション適用済みか: `docker compose -p prism2-test run --rm -e RUN_MIGRATIONS=0 backend alembic current`
3. Backendイメージが最新か: `docker compose -p prism2-test build backend`

### 問題2: LLM分析が動かない

**症状**: `/datasets/{id}/analysis`が503エラーを返す

**確認事項**:
1. `.env`ファイルが存在するか
2. `ANALYSIS_USE_LLM=1`になっているか
3. `LLM_API_KEY`が正しいか（[Google AI Studio](https://makersuite.google.com/app/apikey)で確認）
4. Backendログで詳細を確認: `docker compose logs backend`

### 問題3: Frontendが更新されない

**症状**: コード変更したのにブラウザで反映されない

**解決策**:
1. Dockerイメージを再ビルド: `docker compose build --no-cache frontend`
2. コンテナを再起動: `docker compose up -d frontend`
3. ブラウザでハードリロード: `Ctrl + Shift + R`

### 問題4: DBがリセットされた

**症状**: テスト実行後に開発用DBのデータが消えた

**原因**: テスト用DBと開発用DBを混同している

**解決策**:
- テスト実行時は必ず`-p prism2-test`を付けること
- 開発用DBは`docker compose up -d`で起動（プロジェクト名なし）
- テスト用DBは`docker compose -p prism2-test up -d db`で起動

---

## 付録C: 参考リンク

### 公式ドキュメント
- [FastAPI](https://fastapi.tiangolo.com/)
- [SQLAlchemy 2.0](https://docs.sqlalchemy.org/en/20/)
- [Alembic](https://alembic.sqlalchemy.org/)
- [React](https://react.dev/)
- [Vite](https://vitejs.dev/)
- [Recharts](https://recharts.org/)
- [Google Gemini API](https://ai.google.dev/)

### 内部ドキュメント
- `README.md`: プロジェクト概要と起動手順
- `docs/develop_process.md`: 開発プロセスとタスク進捗（最重要）
- `docs/Requirements Definition.md`: 要件定義書
- `docs/E2_User_Test_Plan.md`: 実ユーザーテスト計画
- `docs/setup_guide.md`: セットアップガイド

---

**最終更新**: 2026/01/18  
**次回更新予定**: Phase 1完了時（E-2-2-1-3実装後）
