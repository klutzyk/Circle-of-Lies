from __future__ import annotations

import httpx

from app.core.config import LLM_TIMEOUT_SECONDS, OPENAI_API_KEY, OPENAI_MODEL
from app.llm.base import LLMProvider


class OpenAIProvider(LLMProvider):
    provider_name = "openai"
    model_name = OPENAI_MODEL

    def __init__(self) -> None:
        if not OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is not configured")
        self._api_key = OPENAI_API_KEY

    def generate_text(self, system_prompt: str, user_prompt: str) -> str:
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.4,
            "max_tokens": 350,
        }

        with httpx.Client(timeout=LLM_TIMEOUT_SECONDS) as client:
            response = client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {self._api_key}"},
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        choices = data.get("choices", [])
        if not choices:
            raise ValueError("OpenAI response had no choices")
        text = choices[0].get("message", {}).get("content", "").strip()
        if not text:
            raise ValueError("OpenAI response text is empty")
        return text
