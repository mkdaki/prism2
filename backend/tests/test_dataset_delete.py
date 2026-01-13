import io
from sqlalchemy import select, func
from app.models import Dataset, DatasetRow


def testDeleteDatasetSucceeds(client, db):
    """目的: 存在するデータセットを削除すると204が返り、データベースから削除されることを確認する。"""
    # 準備: データセットを作成
    csvText = "colA,colB\n1,hello\n2,world\n"
    files = {"file": ("sample.csv", io.BytesIO(csvText.encode("utf-8")), "text/csv")}
    uploadResponse = client.post("/datasets/upload", files=files)
    assert uploadResponse.status_code == 200
    datasetId = uploadResponse.json()["dataset_id"]
    
    # データセットと行が存在することを確認
    datasetCount = db.execute(select(func.count(Dataset.id)).where(Dataset.id == datasetId)).scalar_one()
    assert datasetCount == 1
    rowCount = db.execute(select(func.count(DatasetRow.id)).where(DatasetRow.dataset_id == datasetId)).scalar_one()
    assert rowCount == 2
    
    # 削除実行
    response = client.delete(f"/datasets/{datasetId}")
    
    # 検証
    assert response.status_code == 204
    assert response.content == b""  # 204は本文なし
    
    # データセットが削除されていることを確認
    datasetCountAfter = db.execute(select(func.count(Dataset.id)).where(Dataset.id == datasetId)).scalar_one()
    assert datasetCountAfter == 0
    
    # CASCADE設定により dataset_rows も削除されていることを確認
    rowCountAfter = db.execute(select(func.count(DatasetRow.id)).where(DatasetRow.dataset_id == datasetId)).scalar_one()
    assert rowCountAfter == 0


def testDeleteDatasetReturns404ForNonExistent(client):
    """目的: 存在しないデータセットIDで削除を試みると404が返ることを確認する。"""
    response = client.delete("/datasets/99999")
    
    assert response.status_code == 404
    assert response.json()["detail"] == "Dataset not found"


def testDeleteDatasetCascadesRows(client, db):
    """目的: データセット削除時に、関連する dataset_rows も CASCADE により削除されることを確認する。"""
    # 準備: 複数行を持つデータセットを作成
    csvText = "colA,colB\n1,a\n2,b\n3,c\n4,d\n5,e\n"
    files = {"file": ("test.csv", io.BytesIO(csvText.encode("utf-8")), "text/csv")}
    uploadResponse = client.post("/datasets/upload", files=files)
    assert uploadResponse.status_code == 200
    datasetId = uploadResponse.json()["dataset_id"]
    
    # 5行存在することを確認
    rowCount = db.execute(select(func.count(DatasetRow.id)).where(DatasetRow.dataset_id == datasetId)).scalar_one()
    assert rowCount == 5
    
    # 削除実行
    response = client.delete(f"/datasets/{datasetId}")
    assert response.status_code == 204
    
    # すべての行が削除されていることを確認
    rowCountAfter = db.execute(select(func.count(DatasetRow.id)).where(DatasetRow.dataset_id == datasetId)).scalar_one()
    assert rowCountAfter == 0
