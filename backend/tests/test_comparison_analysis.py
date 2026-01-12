import io
import os
from unittest.mock import Mock, patch

import pytest


def testGetComparisonAnalysisWithLlmDisabled(client):
    """目的: LLM無効時にテンプレート分析が返ることを確認する。"""
    # 2つのCSVをアップロード
    csv1 = (
        "price,stock\n"
        "100,10\n"
        "200,20\n"
    )
    files1 = {"file": ("data1.csv", io.BytesIO(csv1.encode("utf-8")), "text/csv")}
    upload1 = client.post("/datasets/upload", files=files1)
    assert upload1.status_code == 200
    base_id = upload1.json()["dataset_id"]
    
    csv2 = (
        "price,stock\n"
        "150,15\n"
        "250,25\n"
        "300,30\n"
    )
    files2 = {"file": ("data2.csv", io.BytesIO(csv2.encode("utf-8")), "text/csv")}
    upload2 = client.post("/datasets/upload", files=files2)
    assert upload2.status_code == 200
    target_id = upload2.json()["dataset_id"]
    
    # LLM無効で推移分析を実行
    with patch.dict(os.environ, {"ANALYSIS_USE_LLM": "0"}):
        response = client.get(f"/datasets/compare/analysis?base={base_id}&target={target_id}")
    
    assert response.status_code == 200
    body = response.json()
    
    # レスポンス構造の確認
    assert "base_dataset" in body
    assert "target_dataset" in body
    assert "comparison_summary" in body
    assert "analysis_text" in body
    assert "generated_at" in body
    
    # テンプレート分析であることを確認
    assert "簡易要約です（LLM未接続）" in body["analysis_text"]
    assert "## 変化の概要" in body["analysis_text"]
    assert "## 注目すべき変化" in body["analysis_text"]
    assert "## トレンド分析" in body["analysis_text"]
    assert "## 前提・限界" in body["analysis_text"]
    
    # comparison_summary の確認
    summary = body["comparison_summary"]
    assert "rows_change" in summary
    assert summary["rows_change"]["base"] == 2
    assert summary["rows_change"]["target"] == 3
    assert summary["rows_change"]["diff"] == 1


def testGetComparisonAnalysisWithLlmEnabled(client, monkeypatch):
    """目的: LLM有効時に推移分析が返ることを確認する（モック使用）"""
    # 2つのCSVをアップロード
    csv1 = (
        "price\n"
        "100\n"
        "200\n"
    )
    files1 = {"file": ("data1.csv", io.BytesIO(csv1.encode("utf-8")), "text/csv")}
    upload1 = client.post("/datasets/upload", files=files1)
    assert upload1.status_code == 200
    base_id = upload1.json()["dataset_id"]
    
    csv2 = (
        "price\n"
        "150\n"
        "250\n"
        "350\n"
    )
    files2 = {"file": ("data2.csv", io.BytesIO(csv2.encode("utf-8")), "text/csv")}
    upload2 = client.post("/datasets/upload", files=files2)
    assert upload2.status_code == 200
    target_id = upload2.json()["dataset_id"]
    
    # LLMクライアントをモック化
    mock_llm = Mock()
    mock_llm.generate.return_value = (
        "## 変化の概要\n"
        "- 価格が上昇傾向にあります\n"
        "## 注目すべき変化\n"
        "- 平均価格が50.0上昇しました\n"
        "## トレンド分析\n"
        "- 継続的な上昇トレンドが見られます\n"
        "## 前提・限界\n"
        "- データ期間が短いため、長期トレンドは不明です\n"
    )
    
    # LLM有効で推移分析を実行（build_llm_client を直接パッチ）
    with patch.dict(os.environ, {"ANALYSIS_USE_LLM": "1"}):
        with patch("app.main.build_llm_client", return_value=mock_llm):
            response = client.get(f"/datasets/compare/analysis?base={base_id}&target={target_id}")
    
    assert response.status_code == 200
    body = response.json()
    
    # レスポンス構造の確認
    assert "base_dataset" in body
    assert "target_dataset" in body
    assert "comparison_summary" in body
    assert "analysis_text" in body
    assert "generated_at" in body
    
    # LLM生成テキストであることを確認
    assert "価格が上昇傾向にあります" in body["analysis_text"]
    assert "## 変化の概要" in body["analysis_text"]
    
    # LLMが呼ばれたことを確認
    assert mock_llm.generate.called
    call_args = mock_llm.generate.call_args[0][0]
    assert "あなたはデータアナリストです" in call_args
    assert "【基準データ】" in call_args
    assert "【比較対象データ】" in call_args
    assert "【統計差分】" in call_args


def testGetComparisonAnalysisReturns404ForMissingBase(client):
    """目的: baseが存在しない場合に404が返ることを確認する。"""
    # 1つだけデータセットを作成
    csv = "col1\n1\n2\n"
    files = {"file": ("data.csv", io.BytesIO(csv.encode("utf-8")), "text/csv")}
    upload = client.post("/datasets/upload", files=files)
    assert upload.status_code == 200
    target_id = upload.json()["dataset_id"]
    
    # 存在しないbaseで比較分析
    with patch.dict(os.environ, {"ANALYSIS_USE_LLM": "0"}):
        response = client.get(f"/datasets/compare/analysis?base=999999&target={target_id}")
    
    assert response.status_code == 404
    assert "base=999999" in response.json()["detail"]


def testGetComparisonAnalysisReturns404ForMissingTarget(client):
    """目的: targetが存在しない場合に404が返ることを確認する。"""
    # 1つだけデータセットを作成
    csv = "col1\n1\n2\n"
    files = {"file": ("data.csv", io.BytesIO(csv.encode("utf-8")), "text/csv")}
    upload = client.post("/datasets/upload", files=files)
    assert upload.status_code == 200
    base_id = upload.json()["dataset_id"]
    
    # 存在しないtargetで比較分析
    with patch.dict(os.environ, {"ANALYSIS_USE_LLM": "0"}):
        response = client.get(f"/datasets/compare/analysis?base={base_id}&target=999999")
    
    assert response.status_code == 404
    assert "target=999999" in response.json()["detail"]


def testGetComparisonAnalysisReturns400ForSameId(client):
    """目的: baseとtargetが同じ場合に400が返ることを確認する。"""
    # 1つだけデータセットを作成
    csv = "col1\n1\n2\n"
    files = {"file": ("data.csv", io.BytesIO(csv.encode("utf-8")), "text/csv")}
    upload = client.post("/datasets/upload", files=files)
    assert upload.status_code == 200
    dataset_id = upload.json()["dataset_id"]
    
    # 同じIDで比較分析
    with patch.dict(os.environ, {"ANALYSIS_USE_LLM": "0"}):
        response = client.get(f"/datasets/compare/analysis?base={dataset_id}&target={dataset_id}")
    
    assert response.status_code == 400
    assert "Cannot compare dataset with itself" in response.json()["detail"]


def testGetComparisonAnalysisHandlesLlmTimeout(client, monkeypatch):
    """目的: LLMタイムアウト時に504が返ることを確認する。"""
    # 2つのCSVをアップロード
    csv1 = "col1\n1\n"
    files1 = {"file": ("data1.csv", io.BytesIO(csv1.encode("utf-8")), "text/csv")}
    upload1 = client.post("/datasets/upload", files=files1)
    assert upload1.status_code == 200
    base_id = upload1.json()["dataset_id"]
    
    csv2 = "col1\n2\n"
    files2 = {"file": ("data2.csv", io.BytesIO(csv2.encode("utf-8")), "text/csv")}
    upload2 = client.post("/datasets/upload", files=files2)
    assert upload2.status_code == 200
    target_id = upload2.json()["dataset_id"]
    
    # LLMクライアントがタイムアウトするようにモック化
    from app.llm import LLMTimeoutError
    
    mock_llm = Mock()
    mock_llm.generate.side_effect = LLMTimeoutError("Request timed out")
    
    # LLM有効で推移分析を実行
    with patch.dict(os.environ, {"ANALYSIS_USE_LLM": "1"}):
        with patch("app.main.build_llm_client", return_value=mock_llm):
            response = client.get(f"/datasets/compare/analysis?base={base_id}&target={target_id}")
    
    assert response.status_code == 504
    body = response.json()
    assert "error" in body["detail"]
    assert body["detail"]["error"]["retryable"] is True


def testGetComparisonAnalysisHandlesLlmAuthError(client, monkeypatch):
    """目的: LLM認証エラー時に503が返ることを確認する。"""
    # 2つのCSVをアップロード
    csv1 = "col1\n1\n"
    files1 = {"file": ("data1.csv", io.BytesIO(csv1.encode("utf-8")), "text/csv")}
    upload1 = client.post("/datasets/upload", files=files1)
    assert upload1.status_code == 200
    base_id = upload1.json()["dataset_id"]
    
    csv2 = "col1\n2\n"
    files2 = {"file": ("data2.csv", io.BytesIO(csv2.encode("utf-8")), "text/csv")}
    upload2 = client.post("/datasets/upload", files=files2)
    assert upload2.status_code == 200
    target_id = upload2.json()["dataset_id"]
    
    # LLMクライアントが認証エラーになるようにモック化
    from app.llm import LLMAuthError
    
    mock_llm = Mock()
    mock_llm.generate.side_effect = LLMAuthError("Invalid API key")
    
    # LLM有効で推移分析を実行
    with patch.dict(os.environ, {"ANALYSIS_USE_LLM": "1"}):
        with patch("app.main.build_llm_client", return_value=mock_llm):
            response = client.get(f"/datasets/compare/analysis?base={base_id}&target={target_id}")
    
    assert response.status_code == 503
    body = response.json()
    assert "error" in body["detail"]
    assert body["detail"]["error"]["retryable"] is False
