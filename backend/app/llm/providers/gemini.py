from __future__ import annotations

import httpx

from app.core.config import GEMINI_API_KEY, GEMINI_MODEL, LLM_TIMEOUT_SECONDS
from app.llm.base import LLMProvider


class GeminiProvider(LLMProvider):
    provider_name = "gemini"
    model_name = GEMINI_MODEL

    def __init__(self) -> None:
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is not configured")
        self._api_key = GEMINI_API_KEY

    def generate_text(
        self, system_prompt: str, user_prompt: str, json_mode: bool = False
    ) -> str:
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model_name}:generateContent?key={self._api_key}"
        )
        generation_config = {"temperature": 0.75, "maxOutputTokens": 900}
        if json_mode:
            generation_config["responseMimeType"] = "application/json"

        payload = {
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"parts": [{"text": user_prompt}]}],
            "generationConfig": generation_config,
        }

        with httpx.Client(timeout=LLM_TIMEOUT_SECONDS) as client:
            response = client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()

        candidates = data.get("candidates", [])
        if not candidates:
            raise ValueError("Gemini response had no candidates")
        parts = candidates[0].get("content", {}).get("parts", [])
        text = "".join(p.get("text", "") for p in parts).strip()
        if not text:
            raise ValueError("Gemini response text is empty")
        return text
