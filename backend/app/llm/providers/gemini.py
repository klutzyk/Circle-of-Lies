from __future__ import annotations

import time

import httpx

from app.core.config import (
    GEMINI_API_KEY,
    GEMINI_FALLBACK_MODELS,
    GEMINI_MAX_RETRIES,
    GEMINI_MODEL,
    GEMINI_RETRY_BASE_SECONDS,
    GEMINI_RETRY_MAX_SECONDS,
    LLM_TIMEOUT_SECONDS,
)
from app.llm.base import LLMProvider


class GeminiProvider(LLMProvider):
    provider_name = "gemini"
    model_name = GEMINI_MODEL

    def __init__(self) -> None:
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is not configured")
        self._api_key = GEMINI_API_KEY

    @staticmethod
    def _retry_after_seconds(response: httpx.Response | None) -> float | None:
        if response is None:
            return None
        value = response.headers.get("Retry-After", "").strip()
        if not value:
            return None
        try:
            return max(0.0, float(value))
        except ValueError:
            return None

    def _extract_text(self, data: dict) -> str:
        candidates = data.get("candidates", [])
        if not candidates:
            raise ValueError("Gemini response had no candidates")
        parts = candidates[0].get("content", {}).get("parts", [])
        text = "".join(p.get("text", "") for p in parts).strip()
        if not text:
            raise ValueError("Gemini response text is empty")
        return text

    def _call_model(self, model_name: str, payload: dict) -> str:
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model_name}:generateContent?key={self._api_key}"
        )
        with httpx.Client(timeout=LLM_TIMEOUT_SECONDS) as client:
            last_error: Exception | None = None
            for attempt in range(GEMINI_MAX_RETRIES + 1):
                try:
                    response = client.post(url, json=payload)
                    response.raise_for_status()
                    return self._extract_text(response.json())
                except httpx.HTTPStatusError as exc:
                    status = exc.response.status_code
                    retryable = status in {429, 500, 502, 503, 504}
                    if not retryable or attempt >= GEMINI_MAX_RETRIES:
                        raise
                    retry_after = self._retry_after_seconds(exc.response)
                    backoff = min(
                        GEMINI_RETRY_MAX_SECONDS,
                        GEMINI_RETRY_BASE_SECONDS * (2**attempt),
                    )
                    time.sleep(retry_after if retry_after is not None else backoff)
                    last_error = exc
                except (httpx.ConnectError, httpx.ReadTimeout) as exc:
                    if attempt >= GEMINI_MAX_RETRIES:
                        raise
                    backoff = min(
                        GEMINI_RETRY_MAX_SECONDS,
                        GEMINI_RETRY_BASE_SECONDS * (2**attempt),
                    )
                    time.sleep(backoff)
                    last_error = exc
            if last_error:
                raise last_error
            raise ValueError("Gemini call failed without response")

    def generate_text(
        self, system_prompt: str, user_prompt: str, json_mode: bool = False
    ) -> str:
        generation_config = {"temperature": 1, "maxOutputTokens": 900}
        if json_mode:
            generation_config["responseMimeType"] = "application/json"

        payload = {
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"parts": [{"text": user_prompt}]}],
            "generationConfig": generation_config,
        }

        models_to_try: list[str] = []
        for model_name in [self.model_name, *GEMINI_FALLBACK_MODELS]:
            if model_name and model_name not in models_to_try:
                models_to_try.append(model_name)

        last_error: Exception | None = None
        for model_name in models_to_try:
            try:
                return self._call_model(model_name, payload)
            except Exception as exc:
                last_error = exc
                continue
        if last_error:
            raise last_error
        raise ValueError("No Gemini model is configured")
