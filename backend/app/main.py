import csv
import io
import os
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import SQLAlchemyError

from .db import SessionLocal, engine
from .models import Base, Dataset, DatasetRow

app = FastAPI(title="Prism Backend", version="0.1.0")

# CORS（ブラウザアクセス向け）
# 例: "http://localhost:3001,http://127.0.0.1:3001" のようにカンマ区切り
originsEnv = os.getenv("CORS_ALLOW_ORIGINS", "http://localhost:3001")
allowOrigins = [o.strip() for o in originsEnv.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowOrigins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# PoC：起動時にテーブルが無ければ作る（後でAlembicに置き換え可能）
Base.metadata.create_all(bind=engine)

@app.get("/health")
def health():
    """目的: 稼働確認用のヘルスチェック結果を返す。"""
    return {"status": "ok"}

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
