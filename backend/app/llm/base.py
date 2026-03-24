from __future__ import annotations

from abc import ABC, abstractmethod


class LLMProvider(ABC):
    provider_name: str
    model_name: str

    @abstractmethod
    def generate_text(
        self, system_prompt: str, user_prompt: str, json_mode: bool = False
    ) -> str:
        raise NotImplementedError
