import pytest

from app.llm import LLMAuthError, LLMConfig, LLMError, build_llm_client


def testBuildLlmClientReturnsStubByDefault(monkeypatch):
    """目的: LLM_PROVIDER未設定時にスタブ実装が使われることを確認する。"""
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)
    monkeypatch.delenv("LLM_TIMEOUT_SECONDS", raising=False)
    config = LLMConfig.from_env()
    client = build_llm_client(config)
    assert client.generate("x") == "STUB_LLM_RESPONSE"


def testBuildLlmClientRejectsUnsupportedProvider():
    """目的: 未対応のLLM_PROVIDERを指定した場合に例外となることを確認する。"""
    config = LLMConfig(provider="openai", api_key="dummy", model="gpt", timeout_seconds=1)
    with pytest.raises(LLMError):
        build_llm_client(config)


def testBuildLlmClientGeminiRequiresApiKey():
    """目的: Gemini（AI Studio）利用時はAPIキーが必須であることを確認する。"""
    config = LLMConfig(provider="gemini", api_key=None, model="gemini-1.5-flash", timeout_seconds=1)
    with pytest.raises(LLMAuthError):
        build_llm_client(config)


def testBuildLlmClientReturnsGeminiClientWhenConfigured():
    """目的: LLM_PROVIDER=gemini の場合にクライアントが構築できること（ネットワーク呼び出しはしない）。"""
    config = LLMConfig(provider="gemini", api_key="dummy", model="gemini-1.5-flash", timeout_seconds=1)
    client = build_llm_client(config)
    assert hasattr(client, "generate")


