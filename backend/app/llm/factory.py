from __future__ import annotations

from app.core.config import LLM_PROVIDER
from app.llm.base import LLMProvider
from app.llm.providers.gemini import GeminiProvider
from app.llm.providers.huggingface import HuggingFaceProvider
from app.llm.providers.openai import OpenAIProvider


def build_provider() -> LLMProvider:
    if LLM_PROVIDER == "gemini":
        return GeminiProvider()
    if LLM_PROVIDER == "openai":
        return OpenAIProvider()
    if LLM_PROVIDER == "huggingface":
        return HuggingFaceProvider()
    raise ValueError(f"Unsupported LLM_PROVIDER: {LLM_PROVIDER}")
