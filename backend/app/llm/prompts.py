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


def build_conversation_system_prompt() -> str:
    return (
        "You write immersive social strategy scene narration and dialogue. "
        "Keep continuity with player input and cast traits. "
        "No markdown and no meta commentary."
    )


def build_conversation_user_prompt(
    game_id: str,
    round_number: int,
    event: str,
    player_name: str,
    player_text: str,
    interpreted_action: str,
    interpreted_target_id: str,
    cast: list[dict],
) -> str:
    schema = {
        "narration": "2-4 vivid sentences setting social tension and consequences",
        "dialogue": [
            {"speaker_id": "ai_1", "speaker_name": "Mara", "line": "single in-character sentence"}
        ],
    }
    return (
        "Create one short narrative beat plus dialogue reactions.\n"
        "Rules:\n"
        "- narration must be atmospheric and specific.\n"
        "- include 1 to 3 dialogue lines.\n"
        "- at least one line must directly react to the player's message.\n"
        "- speakers must be alive cast members only.\n"
        "- each dialogue line max 22 words.\n"
        f"Game: {game_id}\n"
        f"Round: {round_number}\n"
        f"Event: {event}\n"
        f"Player: {player_name}\n"
        f"Player message: {player_text}\n"
        f"Interpreted action: {interpreted_action}\n"
        f"Interpreted target_id: {interpreted_target_id}\n"
        f"Cast: {cast}\n"
        f"Return JSON only in schema: {json.dumps(schema)}"
    )


def build_turn_resolution_system_prompt() -> str:
    return (
        "You are the simulation director for a social strategy game. "
        "Generate believable evolving interactions that reflect personality and context. "
        "Return strict JSON only."
    )


def build_turn_resolution_user_prompt(
    game_id: str,
    round_number: int,
    event: str,
    player_name: str,
    player_text: str,
    cast: list[dict],
    history_tail: list[dict],
) -> str:
    schema = {
        "narration": "2-5 vivid sentences",
        "dialogue": [
            {"speaker_id": "ai_1", "speaker_name": "Mara", "line": "short line <= 24 words"}
        ],
        "trust_on_player": {"ai_1": 63.0, "ai_2": 49.0},
        "suspicion_on_player": {"ai_1": 31.0, "ai_2": 58.0},
        "eliminated_id": "ai_3 or player or empty string",
        "ai_actions": [
            {"actor_id": "ai_1", "action_type": "accuse|defend|quiet|share_info|build_alliance|spread_doubt", "target_id": "ai_2 or player or empty"}
        ],
    }
    return (
        "Simulate this round from player dialogue. "
        "Keep character voice distinct, non-repetitive, and reactive to exact player wording.\n"
        "Rules:\n"
        "- dialogue lines must include disagreement/alignment dynamics when relevant.\n"
        "- include 2 to 4 dialogue lines from different speakers when plausible.\n"
        "- trust_on_player and suspicion_on_player values are 0..100.\n"
        "- eliminated_id should usually be one alive participant; use empty string if no elimination this round.\n"
        "- keep output coherent with recent history.\n"
        f"Game: {game_id}\n"
        f"Round: {round_number}\n"
        f"Event: {event}\n"
        f"Player: {player_name}\n"
        f"Player text: {player_text}\n"
        f"Alive cast: {cast}\n"
        f"Recent history: {history_tail}\n"
        f"Return JSON only in schema: {json.dumps(schema)}"
    )
