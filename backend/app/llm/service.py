from __future__ import annotations

import hashlib
import json

from app.core.config import LLM_ENABLED
from app.db.repository import get_llm_cache, save_llm_cache
from app.llm.factory import build_provider
from app.llm.prompts import (
    build_cast_generation_system_prompt,
    build_cast_generation_user_prompt,
    build_conversation_system_prompt,
    build_conversation_user_prompt,
    build_flavor_system_prompt,
    build_flavor_user_prompt,
    build_player_intent_system_prompt,
    build_player_intent_user_prompt,
    build_post_game_system_prompt,
    build_post_game_user_prompt,
    build_turn_resolution_system_prompt,
    build_turn_resolution_user_prompt,
)
from app.llm.types import LLMResult
from app.engine.actions import VALID_ACTIONS


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


def _safe_json_loads(text: str) -> dict:
    candidate = text.strip()
    if candidate.startswith("```"):
        candidate = candidate.strip("`")
        candidate = candidate.replace("json", "", 1).strip()
    loaders = (
        lambda s: json.loads(s),
        lambda s: json.loads(s, strict=False),
    )
    for loader in loaders:
        try:
            return loader(candidate)
        except json.JSONDecodeError:
            pass

    start = candidate.find("{")
    end = candidate.rfind("}")
    if start != -1 and end != -1 and end > start:
        snippet = candidate[start : end + 1]
        for loader in loaders:
            try:
                return loader(snippet)
            except json.JSONDecodeError:
                pass
    raise json.JSONDecodeError("Unable to parse JSON payload", candidate, 0)


def _repair_json_with_model(provider, malformed_text: str) -> dict:
    repaired_text = provider.generate_text(
        "You repair malformed JSON. Return valid JSON only with no extra words.",
        (
            "Repair this malformed JSON to valid JSON. Preserve fields and values when possible.\n"
            f"{malformed_text}"
        ),
        json_mode=True,
    )
    return _safe_json_loads(repaired_text)


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


def generate_character_cast(game_id: str, player_name: str) -> list[dict]:
    if not LLM_ENABLED:
        return []

    payload = {"game_id": game_id, "player_name": player_name}
    cache_key = _hash_payload(payload)
    cached = get_llm_cache(game_id, "character_cast", cache_key)
    if cached:
        try:
            return _safe_json_loads(cached["text"]).get("characters", [])
        except Exception:
            return []

    try:
        provider = build_provider()
        text = provider.generate_text(
            build_cast_generation_system_prompt(),
            build_cast_generation_user_prompt(game_id, player_name),
            json_mode=True,
        )
        parsed = _safe_json_loads(text)
        characters = parsed.get("characters", [])
        if not isinstance(characters, list):
            return []
        save_llm_cache(
            game_id, "character_cast", cache_key, provider.provider_name, provider.model_name, json.dumps(parsed)
        )
        return characters
    except Exception:
        return []


def generate_player_intent_action(
    game_id: str,
    player_text: str,
    alive_targets: list[dict],
    event: str,
) -> dict:
    if not LLM_ENABLED:
        return {"action_type": "quiet", "target_id": "", "narration": "You keep your strategy concealed."}

    payload = {
        "game_id": game_id,
        "player_text": player_text,
        "alive_targets": alive_targets,
        "event": event,
    }
    cache_key = _hash_payload(payload)
    cached = get_llm_cache(game_id, "player_intent", cache_key)
    if cached:
        try:
            parsed = _safe_json_loads(cached["text"])
            action_type = parsed.get("action_type", "quiet")
            target_id = parsed.get("target_id", "")
            if action_type not in VALID_ACTIONS:
                action_type = "quiet"
            valid_target_ids = {t["id"] for t in alive_targets}
            if target_id and target_id not in valid_target_ids:
                target_id = ""
            return {
                "action_type": action_type,
                "target_id": target_id,
                "narration": str(parsed.get("narration", "")),
            }
        except Exception:
            pass

    try:
        provider = build_provider()
        text = provider.generate_text(
            build_player_intent_system_prompt(),
            build_player_intent_user_prompt(player_text, alive_targets, event),
            json_mode=True,
        )
        parsed = _safe_json_loads(text)
        action_type = parsed.get("action_type", "quiet")
        target_id = parsed.get("target_id", "")
        if action_type not in VALID_ACTIONS:
            action_type = "quiet"
        valid_target_ids = {t["id"] for t in alive_targets}
        if target_id and target_id not in valid_target_ids:
            target_id = ""
        result = {
            "action_type": action_type,
            "target_id": target_id,
            "narration": str(parsed.get("narration", "")),
        }
        save_llm_cache(
            game_id, "player_intent", cache_key, provider.provider_name, provider.model_name, json.dumps(result)
        )
        return result
    except Exception:
        return {"action_type": "quiet", "target_id": "", "narration": "You stay guarded and observe reactions."}


def generate_conversation_beat(
    game_id: str,
    round_number: int,
    event: str,
    player_name: str,
    player_text: str,
    interpreted_action: str,
    interpreted_target_id: str,
    cast: list[dict],
) -> dict:
    fallback = {
        "narration": "A tense hush settles over the table as your words force everyone to recalculate their position.",
        "dialogue": [],
    }

    if not LLM_ENABLED:
        return fallback

    payload = {
        "game_id": game_id,
        "round_number": round_number,
        "event": event,
        "player_name": player_name,
        "player_text": player_text,
        "interpreted_action": interpreted_action,
        "interpreted_target_id": interpreted_target_id,
        "cast": cast,
    }
    cache_key = _hash_payload(payload)
    cached = get_llm_cache(game_id, "conversation_beat", cache_key)
    if cached:
        try:
            parsed = _safe_json_loads(cached["text"])
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass

    try:
        provider = build_provider()
        text = provider.generate_text(
            build_conversation_system_prompt(),
            build_conversation_user_prompt(
                game_id=game_id,
                round_number=round_number,
                event=event,
                player_name=player_name,
                player_text=player_text,
                interpreted_action=interpreted_action,
                interpreted_target_id=interpreted_target_id,
                cast=cast,
            ),
        )
        parsed = _safe_json_loads(text)
        narration = str(parsed.get("narration", fallback["narration"]))
        dialogue = parsed.get("dialogue", [])
        if not isinstance(dialogue, list):
            dialogue = []
        # Guardrail: only keep well-formed lines with speaker id.
        cleaned = []
        for item in dialogue[:3]:
            if not isinstance(item, dict):
                continue
            speaker_id = str(item.get("speaker_id", "")).strip()
            speaker_name = str(item.get("speaker_name", "")).strip()
            line = str(item.get("line", "")).strip()
            if speaker_id and line:
                cleaned.append(
                    {"speaker_id": speaker_id, "speaker_name": speaker_name, "line": line}
                )
        result = {"narration": narration, "dialogue": cleaned}
        save_llm_cache(
            game_id,
            "conversation_beat",
            cache_key,
            provider.provider_name,
            provider.model_name,
            json.dumps(result),
        )
        return result
    except Exception:
        return fallback


def generate_turn_resolution(
    game_id: str,
    round_number: int,
    scene_step: int,
    event: str,
    player_name: str,
    player_text: str,
    cast: list[dict],
    history_tail: list[dict],
    recent_story_tail: list[dict],
) -> dict:
    player_excerpt = " ".join(player_text.strip().split()[:10]).strip()
    if player_excerpt:
        player_excerpt = f"'{player_excerpt}'"
    else:
        player_excerpt = "'your last statement'"

    fallback_narration = (
        f"Neon light hums above the table while the room measures {player_name}'s words against old grudges. "
        f"Two contestants exchange a quick look when {player_excerpt} lands harder than expected. "
        "No one relaxes; everyone is quietly recalculating who can be useful for one more vote."
    )
    fallback_templates = [
        "That sounded composed, but I am checking whether your timing protects someone specific.",
        "Calm words are easy; I care about who benefits if we follow your lead.",
        "If you want trust, give us one concrete name and one concrete reason.",
        "You are managing tone well, but this room rewards receipts, not posture.",
    ]
    fallback_dialogue = []
    for idx, c in enumerate(cast[:3]):
        fallback_dialogue.append(
            {
                "speaker_id": c.get("participant_id", ""),
                "speaker_name": c.get("name", "Contestant"),
                "line": fallback_templates[idx % len(fallback_templates)],
            }
        )
    fallback = {
        "narration": fallback_narration,
        "dialogue": fallback_dialogue,
        "trust_on_player": {},
        "suspicion_on_player": {},
        "eliminated_id": "",
        "ai_actions": [],
    }

    if not LLM_ENABLED:
        return fallback

    payload = {
        "game_id": game_id,
        "round_number": round_number,
        "scene_step": scene_step,
        "event": event,
        "player_name": player_name,
        "player_text": player_text,
        "cast": cast,
        "history_tail": history_tail,
        "recent_story_tail": recent_story_tail,
    }
    cache_key = _hash_payload(payload)
    cached = get_llm_cache(game_id, "turn_resolution", cache_key)
    if cached:
        try:
            parsed = _safe_json_loads(cached["text"])
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass

    try:
        provider = build_provider()
        text = provider.generate_text(
            build_turn_resolution_system_prompt(),
            build_turn_resolution_user_prompt(
                game_id=game_id,
                round_number=round_number,
                scene_step=scene_step,
                event=event,
                player_name=player_name,
                player_text=player_text,
                cast=cast,
                history_tail=history_tail,
                recent_story_tail=recent_story_tail,
            ),
            json_mode=True,
        )
        try:
            parsed = _safe_json_loads(text)
        except json.JSONDecodeError:
            parsed = _repair_json_with_model(provider, text)
        narration = str(parsed.get("narration", fallback["narration"])).strip()
        recent_narrations = {
            str(item.get("narration", "")).strip().lower()
            for item in recent_story_tail
            if isinstance(item, dict)
        }
        if not narration or narration.lower() in recent_narrations:
            narration = fallback["narration"]

        dialogue = parsed.get("dialogue", [])
        if not isinstance(dialogue, list):
            dialogue = []
        cleaned_dialogue = []
        seen_speakers = set()
        for item in dialogue:
            if not isinstance(item, dict):
                continue
            speaker_id = str(item.get("speaker_id", "")).strip()
            speaker_name = str(item.get("speaker_name", "")).strip()
            line = str(item.get("line", "")).strip()
            if not speaker_id or not line:
                continue
            if speaker_id in seen_speakers and len(cleaned_dialogue) >= 2:
                continue
            seen_speakers.add(speaker_id)
            cleaned_dialogue.append(
                {"speaker_id": speaker_id, "speaker_name": speaker_name, "line": line}
            )
            if len(cleaned_dialogue) >= 4:
                break

        result = {
            "narration": narration,
            "dialogue": cleaned_dialogue,
            "trust_on_player": parsed.get("trust_on_player", {}),
            "suspicion_on_player": parsed.get("suspicion_on_player", {}),
            "eliminated_id": str(parsed.get("eliminated_id", "") or ""),
            "ai_actions": parsed.get("ai_actions", []),
        }
        save_llm_cache(
            game_id,
            "turn_resolution",
            cache_key,
            provider.provider_name,
            provider.model_name,
            json.dumps(result),
        )
        return result
    except Exception as exc:
        failed = dict(fallback)
        failed["_error"] = f"turn_resolution_failed: {exc}"
        return failed
