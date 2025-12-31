import io


def testPostDatasetsUploadSucceeds(client):
    """目的: 正常なCSVアップロードで dataset_id と行数が返ることを確認する。"""
    csvText = "colA,colB\n1,hello\n2,world\n"
    files = {"file": ("sample.csv", io.BytesIO(csvText.encode("utf-8")), "text/csv")}

    response = client.post("/datasets/upload", files=files)

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body["dataset_id"], int)
    assert body["rows"] == 2
    assert body["filename"] == "sample.csv"


def testPostDatasetsUploadRejectsNonCsvExtension(client):
    """目的: 拡張子が.csv以外の場合に 400 が返ることを確認する。"""
    files = {"file": ("sample.txt", io.BytesIO(b"colA\n1\n"), "text/plain")}

    response = client.post("/datasets/upload", files=files)

    assert response.status_code == 400
    assert response.json()["detail"] == "Only .csv is supported"


def testPostDatasetsUploadRejectsNonUtf8(client):
    """目的: UTF-8以外（デコード不能）なCSVの場合に 400 が返ることを確認する。"""
    files = {"file": ("sample.csv", io.BytesIO(b"\xff\xfe\xfa"), "text/csv")}

    response = client.post("/datasets/upload", files=files)

    assert response.status_code == 400
    assert response.json()["detail"] == "CSV must be UTF-8 encoded for now"


def testPostDatasetsUploadRejectsEmptyCsv(client):
    """目的: データ行が存在しないCSVの場合に 400 が返ることを確認する。"""
    csvText = "colA,colB\n"
    files = {"file": ("empty.csv", io.BytesIO(csvText.encode("utf-8")), "text/csv")}

    response = client.post("/datasets/upload", files=files)

    assert response.status_code == 400
    assert response.json()["detail"] == "CSV is empty or has no data rows"


