import io


def testGetDatasetsReturnsEmptyList(client):
    """目的: データセットが0件のとき、GET /datasets が空配列を返すことを確認する。"""
    response = client.get("/datasets")

    assert response.status_code == 200
    assert response.json() == []


def testGetDatasetsReturnsMultipleWithRowCounts(client):
    """目的: 複数データセットが存在する場合に、行数COUNT付きで一覧が返ることを確認する。"""
    firstCsvText = "colA,colB\n1,hello\n2,world\n"
    firstFiles = {"file": ("first.csv", io.BytesIO(firstCsvText.encode("utf-8")), "text/csv")}
    firstUploadResponse = client.post("/datasets/upload", files=firstFiles)
    assert firstUploadResponse.status_code == 200
    firstDatasetId = firstUploadResponse.json()["dataset_id"]

    secondCsvText = "colA\n10\n"
    secondFiles = {"file": ("second.csv", io.BytesIO(secondCsvText.encode("utf-8")), "text/csv")}
    secondUploadResponse = client.post("/datasets/upload", files=secondFiles)
    assert secondUploadResponse.status_code == 200
    secondDatasetId = secondUploadResponse.json()["dataset_id"]

    response = client.get("/datasets")

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert len(body) == 2

    assert body[0]["dataset_id"] == min(firstDatasetId, secondDatasetId)
    assert body[1]["dataset_id"] == max(firstDatasetId, secondDatasetId)

    itemsById = {item["dataset_id"]: item for item in body}

    firstItem = itemsById[firstDatasetId]
    assert firstItem["filename"] == "first.csv"
    assert firstItem["rows"] == 2
    assert isinstance(firstItem["created_at"], str)
    assert firstItem["created_at"] != ""

    secondItem = itemsById[secondDatasetId]
    assert secondItem["filename"] == "second.csv"
    assert secondItem["rows"] == 1
    assert isinstance(secondItem["created_at"], str)
    assert secondItem["created_at"] != ""


