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
    detail = response.json()["detail"]
    assert "encoding is not supported" in detail
    assert "UTF-8" in detail


def testPostDatasetsUploadRejectsEmptyCsv(client):
    """目的: データ行が存在しないCSVの場合に 400 が返ることを確認する。"""
    csvText = "colA,colB\n"
    files = {"file": ("empty.csv", io.BytesIO(csvText.encode("utf-8")), "text/csv")}

    response = client.post("/datasets/upload", files=files)

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert "no data rows" in detail


def testPostDatasetsUploadRejectsCompletelyEmptyFile(client):
    """目的: 完全に空のファイルの場合に 400 が返ることを確認する（D-2）。"""
    files = {"file": ("empty.csv", io.BytesIO(b""), "text/csv")}

    response = client.post("/datasets/upload", files=files)

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert "empty" in detail.lower()


def testPostDatasetsUploadAcceptsShiftJis(client):
    """目的: Shift_JIS（CP932）エンコードのCSVを受け付けることを確認する（D-1）。"""
    csvText = "名前,年齢\nたろう,25\nはなこ,30\n"
    files = {"file": ("sample.csv", io.BytesIO(csvText.encode("cp932")), "text/csv")}

    response = client.post("/datasets/upload", files=files)

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body["dataset_id"], int)
    assert body["rows"] == 2


def testPostDatasetsUploadRejectsEmptyColumnName(client):
    """目的: 空のカラム名を持つCSVの場合に 400 が返ることを確認する（D-2）。"""
    csvText = "colA,,colC\n1,2,3\n"
    files = {"file": ("sample.csv", io.BytesIO(csvText.encode("utf-8")), "text/csv")}

    response = client.post("/datasets/upload", files=files)

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert "empty column name" in detail.lower()


