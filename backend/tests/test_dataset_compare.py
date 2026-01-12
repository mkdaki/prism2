import io

import pytest


def testGetDatasetCompareSuccess(client):
    """目的: GET /datasets/compare が2つのデータセットを比較して差分を返すことを確認する。"""
    # 1つ目のCSV（基準データ）
    csv1 = (
        "price,category,stock\n"
        "100,A,10\n"
        "200,B,20\n"
        "300,A,30\n"
    )
    files1 = {"file": ("data1.csv", io.BytesIO(csv1.encode("utf-8")), "text/csv")}
    upload1 = client.post("/datasets/upload", files=files1)
    assert upload1.status_code == 200
    base_id = upload1.json()["dataset_id"]
    
    # 2つ目のCSV（比較対象データ）
    csv2 = (
        "price,category,stock\n"
        "150,A,15\n"
        "250,B,25\n"
        "350,A,35\n"
        "400,C,40\n"
    )
    files2 = {"file": ("data2.csv", io.BytesIO(csv2.encode("utf-8")), "text/csv")}
    upload2 = client.post("/datasets/upload", files=files2)
    assert upload2.status_code == 200
    target_id = upload2.json()["dataset_id"]
    
    # 比較API呼び出し
    response = client.get(f"/datasets/compare?base={base_id}&target={target_id}")
    assert response.status_code == 200
    body = response.json()
    
    # レスポンス構造の確認
    assert "base_dataset" in body
    assert "target_dataset" in body
    assert "comparison" in body
    
    # base_dataset の確認
    assert body["base_dataset"]["dataset_id"] == base_id
    assert body["base_dataset"]["filename"] == "data1.csv"
    assert body["base_dataset"]["rows"] == 3
    
    # target_dataset の確認
    assert body["target_dataset"]["dataset_id"] == target_id
    assert body["target_dataset"]["filename"] == "data2.csv"
    assert body["target_dataset"]["rows"] == 4
    
    # comparison の確認
    comparison = body["comparison"]
    
    # 行数の変化
    assert comparison["rows_change"]["base"] == 3
    assert comparison["rows_change"]["target"] == 4
    assert comparison["rows_change"]["diff"] == 1
    assert comparison["rows_change"]["percent"] == pytest.approx(33.33, abs=0.01)
    
    # カラムの変化
    columns_change = comparison["columns_change"]
    assert isinstance(columns_change, list)
    
    # price カラムの確認
    price_col = next((c for c in columns_change if c["name"] == "price"), None)
    assert price_col is not None
    assert price_col["kind"] == "number"
    assert price_col["base"] is not None
    assert price_col["target"] is not None
    assert price_col["diff"] is not None
    
    # base: [100, 200, 300] → avg=200, min=100, max=300
    # target: [150, 250, 350, 400] → avg=287.5, min=150, max=400
    assert price_col["base"]["min"] == 100.0
    assert price_col["base"]["max"] == 300.0
    assert price_col["base"]["avg"] == 200.0
    
    assert price_col["target"]["min"] == 150.0
    assert price_col["target"]["max"] == 400.0
    assert price_col["target"]["avg"] == pytest.approx(287.5)
    
    assert price_col["diff"]["min"] == 50.0
    assert price_col["diff"]["max"] == 100.0
    assert price_col["diff"]["avg"] == pytest.approx(87.5)


def testGetDatasetCompareReturns404ForMissingBase(client):
    """目的: base が存在しない場合に 404 が返ることを確認する。"""
    # 1つだけデータセットを作成
    csv = "col1,col2\n1,a\n2,b\n"
    files = {"file": ("data.csv", io.BytesIO(csv.encode("utf-8")), "text/csv")}
    upload = client.post("/datasets/upload", files=files)
    assert upload.status_code == 200
    target_id = upload.json()["dataset_id"]
    
    # 存在しない base で比較
    response = client.get(f"/datasets/compare?base=999999&target={target_id}")
    assert response.status_code == 404
    assert "base=999999" in response.json()["detail"]


def testGetDatasetCompareReturns404ForMissingTarget(client):
    """目的: target が存在しない場合に 404 が返ることを確認する。"""
    # 1つだけデータセットを作成
    csv = "col1,col2\n1,a\n2,b\n"
    files = {"file": ("data.csv", io.BytesIO(csv.encode("utf-8")), "text/csv")}
    upload = client.post("/datasets/upload", files=files)
    assert upload.status_code == 200
    base_id = upload.json()["dataset_id"]
    
    # 存在しない target で比較
    response = client.get(f"/datasets/compare?base={base_id}&target=999999")
    assert response.status_code == 404
    assert "target=999999" in response.json()["detail"]


def testGetDatasetCompareReturns400ForSameId(client):
    """目的: base と target が同じ場合に 400 が返ることを確認する。"""
    # 1つだけデータセットを作成
    csv = "col1,col2\n1,a\n2,b\n"
    files = {"file": ("data.csv", io.BytesIO(csv.encode("utf-8")), "text/csv")}
    upload = client.post("/datasets/upload", files=files)
    assert upload.status_code == 200
    dataset_id = upload.json()["dataset_id"]
    
    # 同じIDで比較
    response = client.get(f"/datasets/compare?base={dataset_id}&target={dataset_id}")
    assert response.status_code == 400
    assert "Cannot compare dataset with itself" in response.json()["detail"]


def testGetDatasetCompareWithDifferentColumns(client):
    """目的: カラム構成が異なる場合でも比較できることを確認する。"""
    # 1つ目のCSV（price, category）
    csv1 = (
        "price,category\n"
        "100,A\n"
        "200,B\n"
    )
    files1 = {"file": ("data1.csv", io.BytesIO(csv1.encode("utf-8")), "text/csv")}
    upload1 = client.post("/datasets/upload", files=files1)
    assert upload1.status_code == 200
    base_id = upload1.json()["dataset_id"]
    
    # 2つ目のCSV（price, stock）- category がなく stock がある
    csv2 = (
        "price,stock\n"
        "150,10\n"
        "250,20\n"
    )
    files2 = {"file": ("data2.csv", io.BytesIO(csv2.encode("utf-8")), "text/csv")}
    upload2 = client.post("/datasets/upload", files=files2)
    assert upload2.status_code == 200
    target_id = upload2.json()["dataset_id"]
    
    # 比較API呼び出し
    response = client.get(f"/datasets/compare?base={base_id}&target={target_id}")
    assert response.status_code == 200
    body = response.json()
    
    columns_change = body["comparison"]["columns_change"]
    col_names = {c["name"] for c in columns_change}
    
    # すべてのカラムが含まれることを確認（和集合）
    assert "price" in col_names
    assert "category" in col_names
    assert "stock" in col_names
    
    # category は base にのみ存在
    category_col = next((c for c in columns_change if c["name"] == "category"), None)
    assert category_col is not None
    assert category_col["base"] is None  # 文字列カラムなので base は None
    assert category_col["target"] is None  # target に存在しないので None
    
    # stock は target にのみ存在
    stock_col = next((c for c in columns_change if c["name"] == "stock"), None)
    assert stock_col is not None
    assert stock_col["base"] is None  # base に存在しないので None
    assert stock_col["target"] is not None  # target には存在
    
    # price は両方に存在
    price_col = next((c for c in columns_change if c["name"] == "price"), None)
    assert price_col is not None
    assert price_col["base"] is not None
    assert price_col["target"] is not None
