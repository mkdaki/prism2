import io

from app.main import app

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


def testGetDatasetAnalysisCanOverrideLlmClient(client, monkeypatch):
    """目的: LLMクライアントをoverrideでき、/analysis がその結果を使えることを確認する。"""

    class FakeLlm:
        def __init__(self):
            self.last_prompt: str | None = None

        def generate(self, prompt: str) -> str:
            self.last_prompt = prompt
            return "FAKE_LLM_OUTPUT"

    monkeypatch.setenv("ANALYSIS_USE_LLM", "1")

    from app.main import getLlmClient

    fake = FakeLlm()
    app.dependency_overrides[getLlmClient] = lambda: fake
    try:
        csvText = "colA,colB\n1,hello\n2,world\n"
        files = {"file": ("sample.csv", io.BytesIO(csvText.encode("utf-8")), "text/csv")}
        uploadResponse = client.post("/datasets/upload", files=files)
        assert uploadResponse.status_code == 200
        datasetId = uploadResponse.json()["dataset_id"]

        response = client.get(f"/datasets/{datasetId}/analysis")
        assert response.status_code == 200
        body = response.json()
        assert body["analysis_text"] == "FAKE_LLM_OUTPUT"

        # B-2-2: prompt v1 が組み立てられて渡っていること（フォーマット指示＋stats埋め込み）
        assert fake.last_prompt is not None
        assert "## 注目点" in fake.last_prompt
        assert "stats_summary_json:" in fake.last_prompt
    finally:
        app.dependency_overrides.clear()


def testGetDatasetAnalysisReturnsLlmErrorDetails(client, monkeypatch):
    """目的: LLM例外時に、HTTPステータスとエラーJSONが一貫した形で返ることを確認する（B-2-3）。"""

    from app.llm import (
        LLMAuthError,
        LLMInputTooLargeError,
        LLMProviderError,
        LLMRateLimitError,
        LLMTimeoutError,
    )
    from app.main import getLlmClient

    class FakeLlm:
        def __init__(self, exc: Exception):
            self.exc = exc

        def generate(self, prompt: str) -> str:
            raise self.exc

    monkeypatch.setenv("ANALYSIS_USE_LLM", "1")

    csvText = "colA,colB\n1,hello\n2,world\n"
    files = {"file": ("sample.csv", io.BytesIO(csvText.encode("utf-8")), "text/csv")}
    uploadResponse = client.post("/datasets/upload", files=files)
    assert uploadResponse.status_code == 200
    datasetId = uploadResponse.json()["dataset_id"]

    cases = [
        (LLMTimeoutError("timeout"), 504, "LLM_TIMEOUT", True),
        (LLMRateLimitError("rate limit"), 503, "LLM_RATE_LIMIT", True),
        (LLMAuthError("auth"), 503, "LLM_AUTH_ERROR", False),
        (LLMInputTooLargeError("too large"), 413, "LLM_INPUT_TOO_LARGE", False),
        (LLMProviderError("upstream"), 502, "LLM_PROVIDER_ERROR", True),
    ]

    for exc, expected_status, expected_code, expected_retryable in cases:
        app.dependency_overrides[getLlmClient] = lambda exc=exc: FakeLlm(exc)
        response = client.get(f"/datasets/{datasetId}/analysis")
        assert response.status_code == expected_status
        body = response.json()
        assert body["detail"]["error"]["code"] == expected_code
        assert body["detail"]["error"]["retryable"] == expected_retryable
        assert isinstance(body["detail"]["error"]["message"], str)


def testGetDatasetAnalysisReturns404ForMissingDataset(client):
    """目的: 存在しないdataset_idを指定した場合に 404 が返ることを確認する。"""
    response = client.get("/datasets/999999/analysis")
    assert response.status_code == 404
    assert response.json()["detail"] == "Dataset not found"


