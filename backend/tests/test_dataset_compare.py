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


def testGetDatasetCompareIncludesPriceRangeAnalysis(client):
    """目的: GET /datasets/compare が price_range_analysis を含むことを確認する（E-2-2改善タスク1）"""
    # 1つ目のCSV（UnitPrice カラムを含む）
    csv1 = (
        "Title,UnitPrice\n"
        "案件A,80万円/月\n"       # high
        "案件B,100万円\n"         # high
        "案件C,60万円\n"          # mid
        "案件D,70万円\n"          # mid
        "案件E,30万円\n"          # low
        "案件F,40万円\n"          # low
        "案件G,応相談\n"          # unknown
    )
    files1 = {"file": ("data1.csv", io.BytesIO(csv1.encode("utf-8")), "text/csv")}
    upload1 = client.post("/datasets/upload", files=files1)
    assert upload1.status_code == 200
    base_id = upload1.json()["dataset_id"]
    
    # 2つ目のCSV（価格帯が変化）
    csv2 = (
        "Title,UnitPrice\n"
        "案件H,90万円\n"          # high
        "案件I,65万円\n"          # mid
        "案件J,55万円\n"          # mid
        "案件K,75万円\n"          # mid
        "案件L,52万円\n"          # mid
        "案件M,35万円\n"          # low
        "案件N,要相談\n"          # unknown
    )
    files2 = {"file": ("data2.csv", io.BytesIO(csv2.encode("utf-8")), "text/csv")}
    upload2 = client.post("/datasets/upload", files=files2)
    assert upload2.status_code == 200
    target_id = upload2.json()["dataset_id"]
    
    # 比較API呼び出し
    response = client.get(f"/datasets/compare?base={base_id}&target={target_id}")
    assert response.status_code == 200
    body = response.json()
    
    # price_range_analysis フィールドの存在確認
    assert "price_range_analysis" in body
    pra = body["price_range_analysis"]
    
    # base の価格帯集計確認
    assert "base" in pra
    assert pra["base"]["high"] == 2     # 80万円, 100万円
    assert pra["base"]["mid"] == 2      # 60万円, 70万円
    assert pra["base"]["low"] == 2      # 30万円, 40万円
    assert pra["base"]["unknown"] == 1  # 応相談
    
    # target の価格帯集計確認
    assert "target" in pra
    assert pra["target"]["high"] == 1   # 90万円
    assert pra["target"]["mid"] == 4    # 65万円, 55万円, 75万円, 52万円
    assert pra["target"]["low"] == 1    # 35万円
    assert pra["target"]["unknown"] == 1  # 要相談
    
    # 増減の確認
    assert "changes" in pra
    changes = pra["changes"]
    
    # high: 2 → 1 （-1件、-50%）
    assert changes["high"]["diff"] == -1
    assert changes["high"]["percent"] == pytest.approx(-50.0)
    
    # mid: 2 → 4 （+2件、+100%）
    assert changes["mid"]["diff"] == 2
    assert changes["mid"]["percent"] == pytest.approx(100.0)
    
    # low: 2 → 1 （-1件、-50%）
    assert changes["low"]["diff"] == -1
    assert changes["low"]["percent"] == pytest.approx(-50.0)
    
    # unknown: 1 → 1 （±0件、0%）
    assert changes["unknown"]["diff"] == 0
    assert changes["unknown"]["percent"] == pytest.approx(0.0)


def testGetDatasetCompareIncludesKeywordAnalysis(client):
    """
    目的: /datasets/compare APIがキーワード分析結果を含むことを確認（E-2-2-1-2）
    """
    # 1. Base用CSVを作成（Titleカラム含む）
    base_csv = (
        "Title,UnitPrice\n"
        "Pythonエンジニア募集,80万円/月\n"
        "Python/Django開発,85万円\n"
        "PHP案件,60万円\n"
        "PHP/Laravel案件,55万円\n"
    )
    base_files = {"file": ("base.csv", io.BytesIO(base_csv.encode("utf-8")), "text/csv")}
    base_response = client.post("/datasets/upload", files=base_files)
    assert base_response.status_code == 200
    base_id = base_response.json()["dataset_id"]
    
    # 2. Target用CSVを作成（Titleカラム含む、キーワードに変化あり）
    target_csv = (
        "Title,UnitPrice\n"
        "Pythonエンジニア募集,90万円/月\n"
        "Python/Django開発,85万円\n"
        "Python/AI案件,95万円\n"  # AI追加
        "TypeScript/Next.js案件,75万円\n"  # TypeScript, Next.js追加
        "React開発,70万円\n"  # React追加
    )
    target_files = {"file": ("target.csv", io.BytesIO(target_csv.encode("utf-8")), "text/csv")}
    target_response = client.post("/datasets/upload", files=target_files)
    assert target_response.status_code == 200
    target_id = target_response.json()["dataset_id"]
    
    # 3. /datasets/compare APIを呼び出し
    compare_response = client.get(f"/datasets/compare?base={base_id}&target={target_id}")
    assert compare_response.status_code == 200
    
    result = compare_response.json()
    
    # 4. keyword_analysis フィールドが含まれることを確認
    assert "keyword_analysis" in result
    ka = result["keyword_analysis"]
    
    # 5. 必須フィールドの存在確認
    assert "base_total" in ka
    assert "target_total" in ka
    assert "increased_keywords" in ka
    assert "decreased_keywords" in ka
    assert "new_keywords" in ka
    assert "disappeared_keywords" in ka
    
    # 6. 件数の確認
    assert ka["base_total"] == 4
    assert ka["target_total"] == 5
    
    # 7. 増加キーワードの確認（Pythonが増加: 2→3）
    increased = ka["increased_keywords"]
    python_increase = next((k for k in increased if k["keyword"] == "Python"), None)
    assert python_increase is not None
    assert python_increase["base"] == 2
    assert python_increase["target"] == 3
    assert python_increase["diff"] == 1
    
    # 8. 減少キーワードの確認（PHPが減少: 2→0）
    decreased = ka["decreased_keywords"]
    php_decrease = next((k for k in decreased if k["keyword"] == "PHP"), None)
    assert php_decrease is not None
    assert php_decrease["base"] == 2
    assert php_decrease["target"] == 0
    assert php_decrease["diff"] == -2
    
    # 9. 新規キーワードの確認
    new_keywords = ka["new_keywords"]
    assert "AI" in new_keywords
    assert "TypeScript" in new_keywords
    assert "Next.js" in new_keywords
    assert "React" in new_keywords
    
    # 10. 消失キーワードの確認
    disappeared = ka["disappeared_keywords"]
    assert "PHP" in disappeared
    assert "Laravel" in disappeared
