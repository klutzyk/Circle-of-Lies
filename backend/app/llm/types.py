from __future__ import annotations

from dataclasses import dataclass


@dataclass
class LLMResult:
    text: str
    provider: str
    model: str
    cached: bool = False
    enabled: bool = True
    reason: str = ""
