import io


def testGetDatasetAnalysisReturnsSummaryText(client):
    """目的: GET /datasets/{dataset_id}/analysis がPoC用の簡易テキスト要約を返すことを確認する。"""
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

    response = client.get(f"/datasets/{datasetId}/analysis")
    assert response.status_code == 200
    body = response.json()

    assert body["dataset_id"] == datasetId
    assert isinstance(body["generated_at"], str)
    assert body["generated_at"].endswith("Z")
    assert isinstance(body["analysis_text"], str)
    assert "行数: 4" in body["analysis_text"]
    assert "カラム数: 5" in body["analysis_text"]


def testGetDatasetAnalysisReturns404ForMissingDataset(client):
    """目的: 存在しないdataset_idを指定した場合に 404 が返ることを確認する。"""
    response = client.get("/datasets/999999/analysis")
    assert response.status_code == 404
    assert response.json()["detail"] == "Dataset not found"


