from __future__ import annotations

from fastapi import HTTPException

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
from app.engine.state import to_public_state
from app.models.domain import GameState


def start_new_game(player_name: str, max_rounds: int) -> GameState:
    state = create_game(player_name=player_name, max_rounds=max_rounds)
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
