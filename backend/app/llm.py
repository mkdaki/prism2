import os
from dataclasses import dataclass
from typing import Protocol

import httpx


class LLMError(RuntimeError):
    """
    LLM呼び出しに関する例外の基底。
    - code/retryable を持たせ、API側で一貫したエラーレスポンスにマップできるようにする（B-2-3）。
    """

    code: str = "LLM_ERROR"
    retryable: bool = False

    def __init__(
        self,
        message: str = "LLM error",
        *,
        code: str | None = None,
        retryable: bool | None = None,
    ):
        super().__init__(message)
        if code is not None:
            self.code = code
        if retryable is not None:
            self.retryable = retryable


class LLMTimeoutError(LLMError):
    code = "LLM_TIMEOUT"
    retryable = True


class LLMAuthError(LLMError):
    code = "LLM_AUTH_ERROR"
    retryable = False


class LLMRateLimitError(LLMError):
    code = "LLM_RATE_LIMIT"
    retryable = True


class LLMInputTooLargeError(LLMError):
    code = "LLM_INPUT_TOO_LARGE"
    retryable = False


class LLMProviderError(LLMError):
    code = "LLM_PROVIDER_ERROR"
    retryable = True


class LLMClient(Protocol):
    """LLM呼び出しのインターフェース（実装差し替え可能にするための境界）。"""

    def generate(self, prompt: str) -> str:  # pragma: no cover (実装側で検証する)
        """prompt を入力に、LLMの生成結果テキストを返す。"""


@dataclass(frozen=True)
class LLMConfig:
    provider: str
    api_key: str | None
    model: str
    timeout_seconds: float

    @staticmethod
    def from_env() -> "LLMConfig":
        provider = os.getenv("LLM_PROVIDER", "stub").strip().lower()
        api_key = os.getenv("LLM_API_KEY")
        model = os.getenv("LLM_MODEL", "stub").strip()
        timeout_seconds = float(os.getenv("LLM_TIMEOUT_SECONDS", "20"))
        return LLMConfig(
            provider=provider,
            api_key=api_key,
            model=model,
            timeout_seconds=timeout_seconds,
        )


class StubLLMClient:
    """外部APIに接続しないスタブ実装（テスト/開発用）。"""

    def __init__(self, config: LLMConfig):
        self.config = config

    def generate(self, prompt: str) -> str:
        # ここでは prompt を評価せず、決まった文言を返す（PoC用）。
        # 具体的なプロンプト設計は B-2-2 で詰める。
        return "STUB_LLM_RESPONSE"


def build_llm_client(config: LLMConfig) -> LLMClient:
    provider = (config.provider or "").strip().lower()
    if provider in ("stub", "none", "disabled"):
        return StubLLMClient(config)

    if provider in ("gemini", "google_ai_studio", "google-ai-studio"):
        return GeminiAiStudioClient(config)

    raise LLMError(f"Unsupported LLM_PROVIDER: {config.provider}")


class GeminiAiStudioClient:
    """
    Google AI Studio (Gemini API) 用の最小クライアント。
    - 外部SDKに依存せず、Generative Language API を httpx で叩く（PoC向け）
    - 行データは送らず、prompt（stats要約）だけを送る前提
    """

    def __init__(self, config: LLMConfig):
        if not config.api_key:
            raise LLMAuthError("LLM_API_KEY is required for Gemini (Google AI Studio)")
        self.config = config

        # AI Studio Gemini API (Generative Language) base URL
        self.base_url = os.getenv(
            "GEMINI_API_BASE_URL", "https://generativelanguage.googleapis.com"
        ).rstrip("/")

    def generate(self, prompt: str) -> str:
        model = (self.config.model or "").strip() or "gemini-2.0-flash"
        if not model.startswith("models/"):
            model = f"models/{model}"

        url = f"{self.base_url}/v1beta/{model}:generateContent"
        params = {"key": self.config.api_key}
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt}],
                }
            ]
        }

        timeout = httpx.Timeout(self.config.timeout_seconds)
        try:
            with httpx.Client(timeout=timeout) as client:
                resp = client.post(url, params=params, json=payload)
        except httpx.TimeoutException as e:
            raise LLMTimeoutError("Gemini request timed out") from e
        except httpx.RequestError as e:
            # DNS/connection reset etc.
            raise LLMProviderError(f"Gemini request failed: {type(e).__name__}") from e

        # エラー時はB-2-3の分類に寄せる
        if resp.status_code >= 400:
            msg = None
            try:
                j = resp.json()
                if isinstance(j, dict) and isinstance(j.get("error"), dict):
                    msg = j["error"].get("message")
            except Exception:
                msg = None

            message = msg or f"Gemini API error (status={resp.status_code})"
            if resp.status_code in (401, 403):
                raise LLMAuthError(message)
            if resp.status_code == 429:
                raise LLMRateLimitError(message)
            if resp.status_code == 413:
                raise LLMInputTooLargeError(message)
            if resp.status_code == 400 and any(
                k in message.lower()
                for k in ("too large", "too long", "exceed", "exceeded", "maximum", "limit")
            ):
                raise LLMInputTooLargeError(message)
            if 500 <= resp.status_code <= 599:
                raise LLMProviderError(message)
            raise LLMError(message)

        try:
            data = resp.json()
        except Exception as e:
            raise LLMProviderError("Gemini API returned non-JSON response") from e

        try:
            candidates = data.get("candidates") or []
            if not candidates:
                raise LLMProviderError("Gemini API returned no candidates")
            content = candidates[0].get("content") or {}
            parts = content.get("parts") or []
            texts = []
            for p in parts:
                if isinstance(p, dict) and isinstance(p.get("text"), str):
                    texts.append(p["text"])
            out = "\n".join([t for t in texts if t.strip()])
            if not out:
                raise LLMProviderError("Gemini API returned empty text")
            return out
        except LLMError:
            raise
        except Exception as e:
            raise LLMProviderError("Failed to parse Gemini response") from e


