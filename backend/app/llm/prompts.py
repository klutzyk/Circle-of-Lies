from __future__ import annotations

import json


def build_post_game_system_prompt() -> str:
    return (
        "You are an analytical game strategist. "
        "Summarize social strategy decisions from structured simulation logs. "
        "Do not invent rounds or outcomes. "
        "Keep the tone concise and portfolio-ready."
    )


def build_post_game_user_prompt(game_id: str, logs: list[dict], analytics: dict) -> str:
    compact_payload = {
        "game_id": game_id,
        "rounds": logs,
        "analytics": analytics,
    }
    return (
        "Generate a concise strategic review in 4 sections: "
        "1) overall approach, 2) key turning points, 3) failure/survival drivers, 4) improvement tips.\n"
        "Use bullet points and limit to 220 words.\n"
        f"DATA:\n{json.dumps(compact_payload, separators=(',', ':'))}"
    )


def build_flavor_system_prompt() -> str:
    return (
        "You are writing short in-world social deduction dialogue. "
        "Keep lines brief, tense, and character-consistent. "
        "No profanity, no meta references to prompts or LLMs."
    )


def build_flavor_user_prompt(
    game_id: str,
    speaker_name: str,
    speaker_traits: dict,
    context_event: str,
    round_number: int,
) -> str:
    return (
        "Write exactly 2 short lines of dialogue from this character after a round. "
        "Each line should be <= 18 words.\n"
        f"Game: {game_id}\n"
        f"Round: {round_number}\n"
        f"Speaker: {speaker_name}\n"
        f"Traits: {speaker_traits}\n"
        f"Context: {context_event}\n"
    )
