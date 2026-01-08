import pytest


def testGeminiClientParsesSuccessResponse(monkeypatch):
    """目的: Gemini（AI Studio）の正常レスポンスを parse して文字列を返せることを確認する。"""
    from app.llm import GeminiAiStudioClient, LLMConfig

    class FakeResponse:
        status_code = 200

        def json(self):
            return {
                "candidates": [
                    {"content": {"parts": [{"text": "hello"}, {"text": "world"}]}}
                ]
            }

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def post(self, url, params=None, json=None):
            # URL/params/json はここでは最小限の確認のみ（詳細はPoC割り切り）
            assert ":generateContent" in url
            assert params and "key" in params
            assert json and "contents" in json
            return FakeResponse()

    import app.llm as llm_mod

    monkeypatch.setattr(llm_mod.httpx, "Client", FakeClient)

    client = GeminiAiStudioClient(
        LLMConfig(provider="gemini", api_key="dummy", model="gemini-2.0-flash", timeout_seconds=1)
    )
    out = client.generate("prompt")
    assert out == "hello\nworld"


@pytest.mark.parametrize(
    "status_code, message, expected_exc",
    [
        (401, "unauthorized", "LLMAuthError"),
        (403, "forbidden", "LLMAuthError"),
        (429, "rate limit", "LLMRateLimitError"),
        (413, "payload too large", "LLMInputTooLargeError"),
        (500, "server error", "LLMProviderError"),
    ],
)
def testGeminiClientMapsHttpErrors(monkeypatch, status_code, message, expected_exc):
    """目的: Gemini APIのHTTPエラーを B-2-3 の分類例外へマップできることを確認する。"""
    from app.llm import GeminiAiStudioClient, LLMConfig

    class FakeResponse:
        def __init__(self):
            self.status_code = status_code

        def json(self):
            return {"error": {"message": message}}

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def post(self, url, params=None, json=None):
            return FakeResponse()

    import app.llm as llm_mod

    monkeypatch.setattr(llm_mod.httpx, "Client", FakeClient)

    client = GeminiAiStudioClient(
        LLMConfig(provider="gemini", api_key="dummy", model="gemini-2.0-flash", timeout_seconds=1)
    )
    exc_type = getattr(__import__("app.llm", fromlist=[expected_exc]), expected_exc)
    with pytest.raises(exc_type):
        client.generate("prompt")


def testGeminiClientMapsTimeout(monkeypatch):
    """目的: httpx の timeout を LLMTimeoutError にマップできることを確認する。"""
    from app.llm import GeminiAiStudioClient, LLMConfig, LLMTimeoutError

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def post(self, url, params=None, json=None):
            import httpx

            raise httpx.TimeoutException("timeout")

    import app.llm as llm_mod

    monkeypatch.setattr(llm_mod.httpx, "Client", FakeClient)

    client = GeminiAiStudioClient(
        LLMConfig(provider="gemini", api_key="dummy", model="gemini-2.0-flash", timeout_seconds=0.01)
    )
    with pytest.raises(LLMTimeoutError):
        client.generate("prompt")


def testGeminiClientDetectsTooLargeFrom400Message(monkeypatch):
    """目的: 400でもメッセージから 'too large' 系を検出して LLMInputTooLargeError にできることを確認する。"""
    from app.llm import GeminiAiStudioClient, LLMConfig, LLMInputTooLargeError

    class FakeResponse:
        status_code = 400

        def json(self):
            return {"error": {"message": "Request payload size exceeded the limit"}}

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def post(self, url, params=None, json=None):
            return FakeResponse()

    import app.llm as llm_mod

    monkeypatch.setattr(llm_mod.httpx, "Client", FakeClient)

    client = GeminiAiStudioClient(
        LLMConfig(provider="gemini", api_key="dummy", model="gemini-2.0-flash", timeout_seconds=1)
    )
    with pytest.raises(LLMInputTooLargeError):
        client.generate("prompt")


