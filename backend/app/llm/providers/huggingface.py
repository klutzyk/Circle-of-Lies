from __future__ import annotations

import httpx

from app.core.config import (
    HF_BASE_URL,
    HF_ENABLE_THINKING,
    HF_MODEL,
    HF_TOKEN,
    LLM_TIMEOUT_SECONDS,
)
from app.llm.base import LLMProvider


class HuggingFaceProvider(LLMProvider):
    provider_name = "huggingface"
    model_name = HF_MODEL or "unknown"

    def __init__(self) -> None:
        if not HF_TOKEN:
            raise ValueError("HF_TOKEN is not configured")
        if not HF_MODEL:
            raise ValueError("HF_MODEL is not configured")
        self._token = HF_TOKEN
        self._base_url = HF_BASE_URL.rstrip("/")
        self.model_name = HF_MODEL

    def generate_text(
        self, system_prompt: str, user_prompt: str, json_mode: bool = False
    ) -> str:
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.8,
            "extra_body": {
                "chat_template_kwargs": {"enable_thinking": HF_ENABLE_THINKING}
            },
        }
        # Keep JSON constrained via prompts; some HF providers reject OpenAI response_format.
        if json_mode:
            payload["temperature"] = 0.4

        with httpx.Client(timeout=LLM_TIMEOUT_SECONDS) as client:
            try:
                response = client.post(
                    f"{self._base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self._token}"},
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
            except httpx.HTTPStatusError as exc:
                detail = ""
                try:
                    detail = exc.response.text
                except Exception:
                    detail = ""
                raise ValueError(
                    f"Hugging Face chat completion failed with status {exc.response.status_code}: {detail}"
                ) from exc

        choices = data.get("choices", [])
        if not choices:
            raise ValueError("Hugging Face response had no choices")
        message = choices[0].get("message", {})
        content = message.get("content", "")
        if isinstance(content, list):
            text = "".join(
                str(item.get("text", ""))
                for item in content
                if isinstance(item, dict)
            ).strip()
        else:
            text = str(content).strip()
        if not text:
            raise ValueError("Hugging Face response text is empty")
        return text
