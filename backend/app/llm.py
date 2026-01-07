import os
from dataclasses import dataclass
from typing import Protocol


class LLMError(RuntimeError):
    pass


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

    # B-2-1時点では外部プロバイダ実装は導入しない（B-2-2/2-3で段階導入）
    raise LLMError(f"Unsupported LLM_PROVIDER for now: {config.provider}")


