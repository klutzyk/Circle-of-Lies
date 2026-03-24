from __future__ import annotations

import uuid

from fastapi import HTTPException

from app.core.config import LLM_ENABLED, LLM_STORY_MODE
from app.db.repository import (
    get_analytics,
    get_game,
    get_round_logs,
    replace_round_logs,
    save_analytics,
    save_game,
)
from app.engine.analytics import build_analytics
from app.engine.engine import advance_round, create_game
from app.engine.state import build_participants_from_generated_cast, to_public_state
from app.llm.service import (
    generate_character_cast,
    generate_flavor_dialogue,
    generate_player_intent_action,
    generate_post_game_analysis,
)
from app.models.domain import GameState


def start_new_game(player_name: str, max_rounds: int) -> GameState:
    participants = None
    if LLM_ENABLED and LLM_STORY_MODE:
        generated_cast = generate_character_cast(str(uuid.uuid4()), player_name)
        if generated_cast:
            participants = build_participants_from_generated_cast(player_name, generated_cast)
    state = create_game(player_name=player_name, max_rounds=max_rounds, participants=participants)
    save_game(state)
    replace_round_logs(state.game_id, state.history)
    return state


def fetch_game_or_404(game_id: str) -> GameState:
    state = get_game(game_id)
    if not state:
        raise HTTPException(status_code=404, detail="Game not found")
    return state


def play_action(game_id: str, action_type: str, target_id: str | None) -> GameState:
    state = fetch_game_or_404(game_id)
    try:
        next_state = advance_round(state, action_type=action_type, target_id=target_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    save_game(next_state)
    replace_round_logs(next_state.game_id, next_state.history)

    if next_state.status == "completed":
        analytics = build_analytics(next_state)
        save_analytics(next_state.game_id, analytics)

    return next_state


def public_game_payload(state: GameState) -> dict:
    return {
        "summary": {
            "game_id": state.game_id,
            "current_round": state.current_round,
            "max_rounds": state.max_rounds,
            "status": state.status,
            "phase": state.phase,
            "winner": state.winner,
        },
        "state": to_public_state(state),
    }


def logs_payload(game_id: str) -> dict:
    return {
        "game_id": game_id,
        "logs": get_round_logs(game_id),
    }


def analytics_payload(game_id: str) -> dict:
    cached = get_analytics(game_id)
    if cached:
        return {"game_id": game_id, "analytics": cached}

    state = fetch_game_or_404(game_id)
    analytics = build_analytics(state)
    if state.status == "completed":
        save_analytics(game_id, analytics)
    return {"game_id": game_id, "analytics": analytics}


def post_game_llm_analysis_payload(game_id: str) -> dict:
    state = fetch_game_or_404(game_id)
    logs = get_round_logs(game_id)
    analytics = get_analytics(game_id) or build_analytics(state)

    result = generate_post_game_analysis(game_id=game_id, logs=logs, analytics=analytics)
    return {
        "game_id": game_id,
        "use_case": "post_game_analysis",
        "text": result.text,
        "provider": result.provider,
        "model": result.model,
        "cached": result.cached,
        "enabled": result.enabled,
        "reason": result.reason,
    }


def flavor_dialogue_payload(game_id: str, speaker_id: str) -> dict:
    state = fetch_game_or_404(game_id)
    speaker = state.participants.get(speaker_id)
    if not speaker:
        raise HTTPException(status_code=404, detail="Speaker not found")

    result = generate_flavor_dialogue(
        game_id=game_id,
        speaker_name=speaker.name,
        speaker_traits=speaker.traits,
        context_event=state.current_event,
        round_number=state.current_round,
    )
    return {
        "game_id": game_id,
        "use_case": "flavor_dialogue",
        "text": result.text,
        "provider": result.provider,
        "model": result.model,
        "cached": result.cached,
        "enabled": result.enabled,
        "reason": result.reason,
    }


def play_story_turn_payload(game_id: str, player_text: str) -> dict:
    state = fetch_game_or_404(game_id)
    if state.status != "active":
        raise HTTPException(status_code=400, detail="Game is not active")

    alive_targets = [
        {"id": pid, "name": p.name}
        for pid, p in state.participants.items()
        if pid != "player" and p.eliminated_round is None
    ]
    interpreted = generate_player_intent_action(
        game_id=game_id,
        player_text=player_text,
        alive_targets=alive_targets,
        event=state.current_event,
    )
    next_state = play_action(
        game_id=game_id,
        action_type=interpreted["action_type"],
        target_id=interpreted["target_id"] or None,
    )
    payload = public_game_payload(next_state)
    payload["story"] = {
        "player_text": player_text,
        "interpreted_action": interpreted["action_type"],
        "interpreted_target_id": interpreted["target_id"],
        "narration": interpreted["narration"],
    }
    return payload
