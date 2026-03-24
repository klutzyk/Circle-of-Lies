from __future__ import annotations

import hashlib
import json

from app.core.config import LLM_ENABLED
from app.db.repository import get_llm_cache, save_llm_cache
from app.llm.factory import build_provider
from app.llm.prompts import (
    build_flavor_system_prompt,
    build_flavor_user_prompt,
    build_post_game_system_prompt,
    build_post_game_user_prompt,
)
from app.llm.types import LLMResult


def _hash_payload(payload: dict) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _disabled_result(reason: str) -> LLMResult:
    return LLMResult(
        text="LLM enhancement is disabled. Core simulation remains fully deterministic.",
        provider="none",
        model="none",
        enabled=False,
        reason=reason,
    )


def generate_post_game_analysis(game_id: str, logs: list[dict], analytics: dict) -> LLMResult:
    if not LLM_ENABLED:
        return _disabled_result("LLM_ENABLED=false")

    payload = {"game_id": game_id, "logs": logs, "analytics": analytics}
    cache_key = _hash_payload(payload)
    cached = get_llm_cache(game_id, "post_game_analysis", cache_key)
    if cached:
        return LLMResult(
            text=cached["text"],
            provider=cached["provider"],
            model=cached["model"],
            cached=True,
            enabled=True,
        )

    try:
        provider = build_provider()
    except Exception as exc:
        return _disabled_result(str(exc))

    try:
        text = provider.generate_text(
            build_post_game_system_prompt(),
            build_post_game_user_prompt(game_id, logs, analytics),
        )
    except Exception as exc:
        return LLMResult(
            text="Strategic LLM analysis unavailable; using deterministic analytics only.",
            provider=provider.provider_name,
            model=provider.model_name,
            enabled=False,
            reason=str(exc),
        )

    save_llm_cache(game_id, "post_game_analysis", cache_key, provider.provider_name, provider.model_name, text)
    return LLMResult(text=text, provider=provider.provider_name, model=provider.model_name, enabled=True)


def generate_flavor_dialogue(
    game_id: str,
    speaker_name: str,
    speaker_traits: dict,
    context_event: str,
    round_number: int,
) -> LLMResult:
    if not LLM_ENABLED:
        return _disabled_result("LLM_ENABLED=false")

    payload = {
        "game_id": game_id,
        "speaker_name": speaker_name,
        "speaker_traits": speaker_traits,
        "context_event": context_event,
        "round_number": round_number,
    }
    cache_key = _hash_payload(payload)
    cached = get_llm_cache(game_id, "flavor_dialogue", cache_key)
    if cached:
        return LLMResult(
            text=cached["text"],
            provider=cached["provider"],
            model=cached["model"],
            cached=True,
            enabled=True,
        )

    try:
        provider = build_provider()
    except Exception as exc:
        return _disabled_result(str(exc))

    try:
        text = provider.generate_text(
            build_flavor_system_prompt(),
            build_flavor_user_prompt(
                game_id=game_id,
                speaker_name=speaker_name,
                speaker_traits=speaker_traits,
                context_event=context_event,
                round_number=round_number,
            ),
        )
    except Exception as exc:
        return LLMResult(
            text=f"{speaker_name}: Keep your eyes open. I trust patterns, not promises.",
            provider=provider.provider_name,
            model=provider.model_name,
            enabled=False,
            reason=str(exc),
        )

    save_llm_cache(game_id, "flavor_dialogue", cache_key, provider.provider_name, provider.model_name, text)
    return LLMResult(text=text, provider=provider.provider_name, model=provider.model_name, enabled=True)
