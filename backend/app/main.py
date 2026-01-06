import csv
import io
import os
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select, text
from sqlalchemy.exc import SQLAlchemyError

from .db import SessionLocal
from .models import Dataset, DatasetRow

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
    db = SessionLocal()
    try:
        statement = (
            select(
                Dataset.id.label("dataset_id"),
                Dataset.filename,
                Dataset.created_at,
                func.count(DatasetRow.id).label("rows"),
            )
            .select_from(Dataset)
            .outerjoin(DatasetRow, DatasetRow.dataset_id == Dataset.id)
            .group_by(Dataset.id, Dataset.filename, Dataset.created_at)
            .order_by(Dataset.id.asc())
        )

        results = db.execute(statement).all()
        return [
            {
                "dataset_id": row.dataset_id,
                "filename": row.filename,
                "created_at": row.created_at,
                "rows": row.rows,
            }
            for row in results
        ]
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"DB error: {type(e).__name__}")
    finally:
        db.close()

@app.get("/datasets/{dataset_id}")
def getDatasetDetail(dataset_id: int):
    """目的: 指定データセットのメタ情報・行数・先頭N行サンプルを返す。"""
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

        return {
            "dataset_id": datasetRow.id,
            "filename": datasetRow.filename,
            "created_at": datasetRow.created_at,
            "rows": totalRows,
            "samples": [{"row_index": r.row_index, "data": r.data} for r in sampleRows],
        }
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"DB error: {type(e).__name__}")
    finally:
        db.close()

@app.get("/datasets/{dataset_id}/stats")
def getDatasetStats(dataset_id: int):
    """目的: 指定データセットの行数・カラム一覧・各カラムの簡易要約（数値/文字列/混在）を返す。"""
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

        return {"dataset_id": dataset_id, "rows": totalRows, "columns": results}
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"DB error: {type(e).__name__}")
    finally:
        db.close()

@app.post("/datasets/upload")
async def upload_dataset(file: UploadFile = File(...)):
    """目的: CSVを受け取り、DBへ保存してdataset_idと行数を返す。"""
    # 1) 拡張子ざっくりチェック（PoC）
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv is supported")

    # 2) バイト列取得 → 文字列化（UTF-8前提。必要ならcp932等に拡張）
    raw = await file.read()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="CSV must be UTF-8 encoded for now")

    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)
    if not rows:
        raise HTTPException(status_code=400, detail="CSV is empty or has no data rows")

    db = SessionLocal()
    try:
        ds = Dataset(filename=file.filename)
        db.add(ds)
        db.flush()  # ds.id を確定させる

        for i, row in enumerate(rows):
            db.add(DatasetRow(dataset_id=ds.id, row_index=i, data=row))

        db.commit()
        return {"dataset_id": ds.id, "rows": len(rows), "filename": file.filename}
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"DB error: {type(e).__name__}")
    finally:
        db.close()
