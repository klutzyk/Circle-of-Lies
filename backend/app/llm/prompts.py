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


def build_cast_generation_system_prompt() -> str:
    return (
        "You generate coherent social strategy game characters. "
        "Return strict JSON only. No markdown."
    )


def build_cast_generation_user_prompt(game_id: str, player_name: str) -> str:
    schema = {
        "characters": [
            {
                "name": "string",
                "occupation": "string",
                "persona": "string",
                "backstory": "string",
                "hidden_objective": "string",
                "traits": {
                    "sociability": 0.0,
                    "aggressiveness": 0.0,
                    "loyalty": 0.0,
                    "risk_tolerance": 0.0,
                    "deception_tendency": 0.0,
                    "charisma": 0.0,
                    "suspicion_sensitivity": 0.0,
                    "empathy": 0.0,
                    "discipline": 0.0,
                },
            }
        ]
    }
    return (
        "Create 5 unique contestants for a social strategy simulator. "
        "Avoid stereotypes. Keep each backstory to 1-2 sentences. "
        "Use traits on a 0..1 scale.\n"
        f"Player name: {player_name}\n"
        f"Game id: {game_id}\n"
        f"Return JSON matching this schema:\n{json.dumps(schema)}"
    )


def build_player_intent_system_prompt() -> str:
    return (
        "Classify player text into one legal action and optional target for a strategy game. "
        "Return strict JSON only."
    )


def build_player_intent_user_prompt(
    player_text: str,
    alive_targets: list[dict],
    event: str,
) -> str:
    schema = {
        "action_type": "defend|accuse|quiet|share_info|build_alliance|spread_doubt",
        "target_id": "ai_x or empty string",
        "narration": "short one sentence describing social intent",
    }
    return (
        f"Event: {event}\n"
        f"Alive targets: {alive_targets}\n"
        f"Player message: {player_text}\n"
        f"Return JSON only in this schema: {json.dumps(schema)}"
    )
