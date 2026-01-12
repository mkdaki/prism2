import csv
import io
import logging
import os
from datetime import datetime, timezone
from functools import lru_cache

from fastapi import Depends, FastAPI, UploadFile, File, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select, text
from sqlalchemy.exc import SQLAlchemyError

from .db import SessionLocal
from .analysis import calculate_stats_diff, generate_llm_analysis_text, generate_template_analysis
from .llm import (
    LLMAuthError,
    LLMClient,
    LLMConfig,
    LLMError,
    LLMInputTooLargeError,
    LLMProviderError,
    LLMRateLimitError,
    LLMTimeoutError,
    build_llm_client,
)
from .models import Dataset, DatasetRow

# D-3: ログ設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("prism.backend")

app = FastAPI(title="Prism Backend", version="0.1.0")

# A-2: データセット詳細で返すサンプル行数（固定）
SAMPLE_ROWS_LIMIT = 10

# B-1: statsで文字列カラムの上位値を返す件数（固定）
STRING_TOP_VALUES_LIMIT = 5

# B-1: 数値判定（CSV取り込み値は基本文字列のため、数値として扱えるものだけ集計）
# 例: "1", "-1", "1.2", ".5", "1e3", "-1.2E-3"
NUMERIC_REGEX = r"^[+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?$"

# CORS（ブラウザアクセス向け）
# 例: "http://localhost:3001,http://127.0.0.1:3001" のようにカンマ区切り
originsEnv = os.getenv("CORS_ALLOW_ORIGINS", "http://localhost:3001,http://127.0.0.1:3001")
allowOrigins = [o.strip() for o in originsEnv.split(",") if o.strip()]


@lru_cache
def getLlmConfig() -> LLMConfig:
    return LLMConfig.from_env()


def getLlmClient(config: LLMConfig = Depends(getLlmConfig)) -> LLMClient:
    return build_llm_client(config)


app.add_middleware(
    CORSMiddleware,
    allow_origins=allowOrigins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    """目的: 稼働確認用のヘルスチェック結果を返す。"""
    return {"status": "ok"}

@app.get("/datasets")
def listDatasets():
    """目的: データセット一覧（行数付き）を返す。"""
    logger.info("GET /datasets - Fetching dataset list")
    db = SessionLocal()
    try:
        statement = (
            select(
                Dataset.id.label("dataset_id"),
                Dataset.filename,
                Dataset.created_at,
                func.count(DatasetRow.id).label("row_count"),
            )
            .select_from(Dataset)
            .outerjoin(DatasetRow, DatasetRow.dataset_id == Dataset.id)
            .group_by(Dataset.id, Dataset.filename, Dataset.created_at)
            .order_by(Dataset.id.asc())
        )

        results = db.execute(statement).all()
        datasets = [
            {
                "dataset_id": row.dataset_id,
                "filename": row.filename,
                "created_at": row.created_at,
                "row_count": row.row_count,
            }
            for row in results
        ]
        logger.info(f"GET /datasets - Returning {len(datasets)} dataset(s)")
        return {"datasets": datasets}
    except SQLAlchemyError as e:
        logger.error(f"GET /datasets - DB error: {type(e).__name__}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"DB error: {type(e).__name__}")
    finally:
        db.close()

@app.get("/datasets/compare")
def compareDatasets(base: int, target: int):
    """目的: 2つのデータセットの統計情報を比較し、差分を返す（E-0-2）。"""
    logger.info(f"GET /datasets/compare?base={base}&target={target} - Comparing datasets")
    
    # 1. クエリパラメータの検証（同一ID指定はエラー）
    if base == target:
        logger.warning(f"GET /datasets/compare - Same ID specified: base={base}, target={target}")
        raise HTTPException(
            status_code=400,
            detail="Cannot compare dataset with itself. Please specify different dataset IDs."
        )
    
    db = SessionLocal()
    try:
        # 2. 両データセットの存在チェック
        base_dataset_statement = select(Dataset.id, Dataset.filename, Dataset.created_at).where(Dataset.id == base)
        base_dataset_row = db.execute(base_dataset_statement).first()
        if base_dataset_row is None:
            logger.warning(f"GET /datasets/compare - Base dataset not found: {base}")
            raise HTTPException(status_code=404, detail=f"Dataset not found: base={base}")
        
        target_dataset_statement = select(Dataset.id, Dataset.filename, Dataset.created_at).where(Dataset.id == target)
        target_dataset_row = db.execute(target_dataset_statement).first()
        if target_dataset_row is None:
            logger.warning(f"GET /datasets/compare - Target dataset not found: {target}")
            raise HTTPException(status_code=404, detail=f"Dataset not found: target={target}")
        
        # 3. 行数を取得
        base_rows_statement = (
            select(func.count(DatasetRow.id))
            .select_from(DatasetRow)
            .where(DatasetRow.dataset_id == base)
        )
        base_rows = db.execute(base_rows_statement).scalar_one()
        
        target_rows_statement = (
            select(func.count(DatasetRow.id))
            .select_from(DatasetRow)
            .where(DatasetRow.dataset_id == target)
        )
        target_rows = db.execute(target_rows_statement).scalar_one()
        
    except SQLAlchemyError as e:
        logger.error(f"GET /datasets/compare - DB error: {type(e).__name__}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"DB error: {type(e).__name__}")
    finally:
        db.close()
    
    # 4. getDatasetStats() を2回呼び出して統計を取得
    base_stats = getDatasetStats(base)
    target_stats = getDatasetStats(target)
    
    # 5. 差分を計算
    comparison = calculate_stats_diff(base_stats, target_stats)
    
    # 6. レスポンスを返す
    logger.info(f"GET /datasets/compare - Success: base={base}, target={target}")
    return {
        "base_dataset": {
            "dataset_id": base_dataset_row.id,
            "filename": base_dataset_row.filename,
            "created_at": base_dataset_row.created_at,
            "rows": base_rows
        },
        "target_dataset": {
            "dataset_id": target_dataset_row.id,
            "filename": target_dataset_row.filename,
            "created_at": target_dataset_row.created_at,
            "rows": target_rows
        },
        "comparison": comparison
    }

@app.get("/datasets/{dataset_id}")
def getDatasetDetail(dataset_id: int):
    """目的: 指定データセットのメタ情報・行数・先頭N行サンプルを返す。"""
    logger.info(f"GET /datasets/{dataset_id} - Fetching dataset detail")
    db = SessionLocal()
    try:
        datasetStatement = (
            select(Dataset.id, Dataset.filename, Dataset.created_at)
            .where(Dataset.id == dataset_id)
        )
        datasetRow = db.execute(datasetStatement).first()
        if datasetRow is None:
            raise HTTPException(status_code=404, detail="Dataset not found")

        rowsStatement = (
            select(func.count(DatasetRow.id))
            .select_from(DatasetRow)
            .where(DatasetRow.dataset_id == dataset_id)
        )
        totalRows = db.execute(rowsStatement).scalar_one()

        samplesStatement = (
            select(DatasetRow.row_index, DatasetRow.data)
            .select_from(DatasetRow)
            .where(DatasetRow.dataset_id == dataset_id)
            .order_by(DatasetRow.row_index.asc())
            .limit(SAMPLE_ROWS_LIMIT)
        )
        sampleRows = db.execute(samplesStatement).all()

        logger.info(f"GET /datasets/{dataset_id} - Returning detail (rows={totalRows}, samples={len(sampleRows)})")
        return {
            "dataset_id": datasetRow.id,
            "filename": datasetRow.filename,
            "created_at": datasetRow.created_at,
            "rows": totalRows,
            "samples": [{"row_index": r.row_index, "data": r.data} for r in sampleRows],
        }
    except SQLAlchemyError as e:
        logger.error(f"GET /datasets/{dataset_id} - DB error: {type(e).__name__}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"DB error: {type(e).__name__}")
    finally:
        db.close()

@app.get("/datasets/{dataset_id}/stats")
def getDatasetStats(dataset_id: int):
    """目的: 指定データセットの行数・カラム一覧・各カラムの簡易要約（数値/文字列/混在）を返す。"""
    logger.info(f"GET /datasets/{dataset_id}/stats - Computing statistics")
    db = SessionLocal()
    try:
        # 1) dataset存在チェック
        datasetStatement = select(Dataset.id).where(Dataset.id == dataset_id)
        datasetRow = db.execute(datasetStatement).first()
        if datasetRow is None:
            raise HTTPException(status_code=404, detail="Dataset not found")

        # 2) 行数
        rowsStatement = (
            select(func.count(DatasetRow.id))
            .select_from(DatasetRow)
            .where(DatasetRow.dataset_id == dataset_id)
        )
        totalRows = db.execute(rowsStatement).scalar_one()

        # 3) カラム一覧（JSONBキーのdistinct）
        columnsStatement = text(
            """
            SELECT DISTINCT jsonb_object_keys(data) AS col
            FROM dataset_rows
            WHERE dataset_id = :dataset_id
            ORDER BY col ASC
            """
        )
        columnRows = db.execute(columnsStatement, {"dataset_id": dataset_id}).all()
        columns = [r.col for r in columnRows]

        # 4) 各カラムの要約
        results = []
        for col in columns:
            summaryStatement = text(
                """
                WITH extracted AS (
                  SELECT
                    (data ? :col) AS present,
                    nullif(btrim(data ->> :col), '') AS v
                  FROM dataset_rows
                  WHERE dataset_id = :dataset_id
                )
                SELECT
                  count(*) FILTER (WHERE present) AS present_count,
                  count(*) FILTER (WHERE v IS NOT NULL) AS non_empty_count,
                  count(*) FILTER (WHERE v ~ :numeric_regex) AS numeric_count,
                  min(CASE WHEN v ~ :numeric_regex THEN v::double precision END) AS min,
                  max(CASE WHEN v ~ :numeric_regex THEN v::double precision END) AS max,
                  avg(CASE WHEN v ~ :numeric_regex THEN v::double precision END) AS avg
                FROM extracted
                """
            )
            summary = db.execute(
                summaryStatement,
                {"dataset_id": dataset_id, "col": col, "numeric_regex": NUMERIC_REGEX},
            ).mappings().one()

            presentCount = int(summary["present_count"] or 0)
            nonEmptyCount = int(summary["non_empty_count"] or 0)
            numericCount = int(summary["numeric_count"] or 0)

            if nonEmptyCount == 0:
                kind = "empty"
            elif numericCount == nonEmptyCount:
                kind = "number"
            elif numericCount == 0:
                kind = "string"
            else:
                kind = "mixed"

            item = {
                "name": col,
                "kind": kind,
                "present_count": presentCount,
                "non_empty_count": nonEmptyCount,
                "numeric": {
                    "count": numericCount,
                    "min": summary["min"],
                    "max": summary["max"],
                    "avg": summary["avg"],
                }
                if numericCount > 0
                else None,
                "top_values": None,
            }

            # 文字列（および混在）の場合は、非数値の上位頻出値を返す
            if kind in ("string", "mixed"):
                topValuesStatement = text(
                    """
                    WITH extracted AS (
                      SELECT nullif(btrim(data ->> :col), '') AS v
                      FROM dataset_rows
                      WHERE dataset_id = :dataset_id
                    )
                    SELECT v AS value, count(*) AS count
                    FROM extracted
                    WHERE v IS NOT NULL
                      AND NOT (v ~ :numeric_regex)
                    GROUP BY v
                    ORDER BY count DESC, v ASC
                    LIMIT :limit
                    """
                )
                topRows = db.execute(
                    topValuesStatement,
                    {
                        "dataset_id": dataset_id,
                        "col": col,
                        "numeric_regex": NUMERIC_REGEX,
                        "limit": STRING_TOP_VALUES_LIMIT,
                    },
                ).all()
                item["top_values"] = [{"value": r.value, "count": int(r.count)} for r in topRows]

            results.append(item)

        logger.info(f"GET /datasets/{dataset_id}/stats - Returning stats (rows={totalRows}, columns={len(results)})")
        return {"dataset_id": dataset_id, "rows": totalRows, "columns": results}
    except SQLAlchemyError as e:
        logger.error(f"GET /datasets/{dataset_id}/stats - DB error: {type(e).__name__}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"DB error: {type(e).__name__}")
    finally:
        db.close()


@app.get("/datasets/{dataset_id}/analysis")
def getDatasetAnalysis(dataset_id: int, llm: LLMClient = Depends(getLlmClient)):
    """目的: B-1の集計結果を入力として、PoC用の簡易テキスト要約（LLMなし）を返す。"""
    logger.info(f"GET /datasets/{dataset_id}/analysis - Generating analysis")
    stats = getDatasetStats(dataset_id)
    useLlm = os.getenv("ANALYSIS_USE_LLM", "0").strip() in ("1", "true", "yes", "on")

    if not useLlm:
        logger.info(f"GET /datasets/{dataset_id}/analysis - Using template analysis (LLM disabled)")
        template = generate_template_analysis(stats)
        return {"dataset_id": dataset_id, **template}

    # B-2-1: 配線確認のため、LLM呼び出しの境界だけ用意する（品質/エラー処理はB-2-2/2-3で改善）
    generatedAt = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    try:
        logger.info(f"GET /datasets/{dataset_id}/analysis - Calling LLM")
        text = generate_llm_analysis_text(stats, llm)
        logger.info(f"GET /datasets/{dataset_id}/analysis - LLM call succeeded (text_length={len(text)})")
    except LLMError as e:
        logger.error(
            f"GET /datasets/{dataset_id}/analysis - LLM error: {type(e).__name__} - {str(e)}",
            exc_info=True
        )
        # B-2-3: エラーハンドリング（PoCでも最低限）
        status_code = 500
        if isinstance(e, LLMTimeoutError):
            status_code = 504
        elif isinstance(e, LLMRateLimitError):
            status_code = 503
        elif isinstance(e, LLMAuthError):
            status_code = 503
        elif isinstance(e, LLMInputTooLargeError):
            status_code = 413
        elif isinstance(e, LLMProviderError):
            status_code = 502

        raise HTTPException(
            status_code=status_code,
            detail={
                "error": {
                    "code": getattr(e, "code", "LLM_ERROR"),
                    "message": str(e),
                    "retryable": bool(getattr(e, "retryable", False)),
                }
            },
        )
    return {"dataset_id": dataset_id, "generated_at": generatedAt, "analysis_text": text}

@app.post("/datasets/upload")
async def upload_dataset(file: UploadFile = File(...)):
    """目的: CSVを受け取り、DBへ保存してdataset_idと行数を返す。"""
    logger.info(f"POST /datasets/upload - Uploading file: {file.filename}")
    
    # 1) 拡張子ざっくりチェック（PoC）
    if not file.filename.lower().endswith(".csv"):
        logger.warning(f"POST /datasets/upload - Invalid file extension: {file.filename}")
        raise HTTPException(status_code=400, detail="Only .csv is supported")

    # 2) バイト列取得 → 文字列化（UTF-8優先、Shift_JIS/CP932をフォールバック）
    raw = await file.read()
    
    # 完全な空ファイルチェック（D-2）
    if len(raw) == 0:
        logger.warning(f"POST /datasets/upload - Empty file: {file.filename}")
        raise HTTPException(
            status_code=400,
            detail="File is empty. Please upload a CSV file with at least a header row."
        )
    
    # エンコーディング検出と変換（D-1）
    text: str | None = None
    detected_encoding: str | None = None
    
    # まずUTF-8で試行
    try:
        text = raw.decode("utf-8")
        detected_encoding = "utf-8"
    except UnicodeDecodeError:
        pass
    
    # UTF-8で失敗した場合、Shift_JIS（CP932）で試行
    if text is None:
        try:
            text = raw.decode("cp932")
            detected_encoding = "cp932"
        except UnicodeDecodeError:
            pass
    
    # どちらも失敗した場合はエラー
    if text is None:
        logger.warning(f"POST /datasets/upload - Unsupported encoding: {file.filename}")
        raise HTTPException(
            status_code=400,
            detail="CSV encoding is not supported. Please use UTF-8 or Shift_JIS (CP932) encoding. "
                   "You can convert your file using a text editor or save it as UTF-8 in Excel."
        )
    
    logger.info(f"POST /datasets/upload - Detected encoding: {detected_encoding}")

    # 3) CSV解析とバリデーション（D-2）
    reader = csv.DictReader(io.StringIO(text))
    
    # ヘッダー行の検証
    if reader.fieldnames is None or len(reader.fieldnames) == 0:
        logger.warning(f"POST /datasets/upload - No header row: {file.filename}")
        raise HTTPException(
            status_code=400,
            detail="CSV has no header row. Please ensure the first row contains column names."
        )
    
    # 空のカラム名をチェック
    emptyColumns = [i for i, name in enumerate(reader.fieldnames) if not name or not name.strip()]
    if emptyColumns:
        logger.warning(f"POST /datasets/upload - Empty column names at positions {emptyColumns}: {file.filename}")
        raise HTTPException(
            status_code=400,
            detail=f"CSV has empty column name(s) at position(s): {emptyColumns}. "
                   "All columns must have names."
        )
    
    rows = list(reader)
    if not rows:
        logger.warning(f"POST /datasets/upload - No data rows: {file.filename}")
        raise HTTPException(
            status_code=400,
            detail="CSV has no data rows. Please ensure there is at least one data row after the header."
        )

    db = SessionLocal()
    try:
        ds = Dataset(filename=file.filename)
        db.add(ds)
        db.flush()  # ds.id を確定させる

        for i, row in enumerate(rows):
            db.add(DatasetRow(dataset_id=ds.id, row_index=i, data=row))

        db.commit()
        logger.info(f"POST /datasets/upload - Success: dataset_id={ds.id}, rows={len(rows)}, filename={file.filename}")
        return {"dataset_id": ds.id, "rows": len(rows), "filename": file.filename}
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"POST /datasets/upload - DB error: {type(e).__name__}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"DB error: {type(e).__name__}")
    finally:
        db.close()
