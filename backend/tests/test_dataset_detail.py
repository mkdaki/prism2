import io


def testGetDatasetDetailReturnsMetaRowsAndSamples(client):
    """目的: GET /datasets/{dataset_id} がメタ情報・行数・先頭N行サンプルを返すことを確認する。"""
    csvText = "colA,colB\n1,hello\n2,world\n"
    files = {"file": ("sample.csv", io.BytesIO(csvText.encode("utf-8")), "text/csv")}
    uploadResponse = client.post("/datasets/upload", files=files)
    assert uploadResponse.status_code == 200
    datasetId = uploadResponse.json()["dataset_id"]

    response = client.get(f"/datasets/{datasetId}")

    assert response.status_code == 200
    body = response.json()
    assert body["dataset_id"] == datasetId
    assert body["filename"] == "sample.csv"
    assert isinstance(body["created_at"], str)
    assert body["created_at"] != ""
    assert body["rows"] == 2

    assert isinstance(body["samples"], list)
    assert len(body["samples"]) == 2
    assert body["samples"][0]["row_index"] == 0
    assert body["samples"][0]["data"] == {"colA": "1", "colB": "hello"}
    assert body["samples"][1]["row_index"] == 1
    assert body["samples"][1]["data"] == {"colA": "2", "colB": "world"}


def testGetDatasetDetailReturns404ForMissingDataset(client):
    """目的: 存在しないdataset_idを指定した場合に 404 が返ることを確認する。"""
    response = client.get("/datasets/999999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Dataset not found"


