import io

import pytest


def testGetDatasetStatsSummarizesNumericStringMixedAndEmpty(client):
    """目的: GET /datasets/{dataset_id}/stats が数値/文字列/混在/空カラムを要約して返すことを確認する。"""
    csvText = (
        "project,amount,score,mixed,empty\n"
        "案件A,100,1.5,1,\n"
        "案件B,200,2.5,x,\n"
        "案件A,,3.0,2,\n"
        ",300,,3,\n"
    )
    files = {"file": ("sample.csv", io.BytesIO(csvText.encode("utf-8")), "text/csv")}
    uploadResponse = client.post("/datasets/upload", files=files)
    assert uploadResponse.status_code == 200
    datasetId = uploadResponse.json()["dataset_id"]

    response = client.get(f"/datasets/{datasetId}/stats")
    assert response.status_code == 200
    body = response.json()

    assert body["dataset_id"] == datasetId
    assert body["rows"] == 4

    columns = body["columns"]
    assert isinstance(columns, list)
    colsByName = {c["name"]: c for c in columns}

    # project: 文字列（案件名）
    project = colsByName["project"]
    assert project["kind"] == "string"
    assert project["non_empty_count"] == 3
    assert project["numeric"] is None
    top = project["top_values"]
    assert {"value": "案件A", "count": 2} in top
    assert {"value": "案件B", "count": 1} in top

    # amount: 数値（空は無視される）
    amount = colsByName["amount"]
    assert amount["kind"] == "number"
    assert amount["non_empty_count"] == 3
    assert amount["numeric"]["count"] == 3
    assert amount["numeric"]["min"] == 100.0
    assert amount["numeric"]["max"] == 300.0
    assert amount["numeric"]["avg"] == pytest.approx(200.0)
    assert amount["top_values"] is None

    # score: 数値（欠損あり）
    score = colsByName["score"]
    assert score["kind"] == "number"
    assert score["non_empty_count"] == 3
    assert score["numeric"]["count"] == 3
    assert score["numeric"]["min"] == 1.5
    assert score["numeric"]["max"] == 3.0
    assert score["numeric"]["avg"] == pytest.approx((1.5 + 2.5 + 3.0) / 3)

    # mixed: 混在（数値と文字列）
    mixed = colsByName["mixed"]
    assert mixed["kind"] == "mixed"
    assert mixed["non_empty_count"] == 4
    assert mixed["numeric"]["count"] == 3
    assert mixed["numeric"]["min"] == 1.0
    assert mixed["numeric"]["max"] == 3.0
    assert mixed["numeric"]["avg"] == pytest.approx(2.0)
    assert {"value": "x", "count": 1} in mixed["top_values"]

    # empty: 全行空
    empty = colsByName["empty"]
    assert empty["kind"] == "empty"
    assert empty["non_empty_count"] == 0
    assert empty["numeric"] is None
    assert empty["top_values"] is None


def testGetDatasetStatsReturns404ForMissingDataset(client):
    """目的: 存在しないdataset_idを指定した場合に 404 が返ることを確認する。"""
    response = client.get("/datasets/999999/stats")
    assert response.status_code == 404
    assert response.json()["detail"] == "Dataset not found"


