from __future__ import annotations

from fastapi import APIRouter

from app.engine.actions import ACTION_CATALOG
from app.schemas.game import (
    AnalyticsResponse,
    GameStateResponse,
    PlayerActionRequest,
    RoundLogsResponse,
    StartGameRequest,
)
from app.services.game_service import (
    analytics_payload,
    fetch_game_or_404,
    logs_payload,
    play_action,
    public_game_payload,
    start_new_game,
)

router = APIRouter(prefix="/api", tags=["game"])


@router.get("/meta/actions")
def get_actions() -> dict:
    return {"actions": ACTION_CATALOG}


@router.post("/games", response_model=GameStateResponse)
def start_game(request: StartGameRequest):
    state = start_new_game(request.player_name, request.max_rounds)
    return public_game_payload(state)


@router.get("/games/{game_id}", response_model=GameStateResponse)
def get_game(game_id: str):
    state = fetch_game_or_404(game_id)
    return public_game_payload(state)


@router.post("/games/{game_id}/actions", response_model=GameStateResponse)
def submit_action(game_id: str, request: PlayerActionRequest):
    state = play_action(game_id, request.action_type, request.target_id)
    return public_game_payload(state)


@router.get("/games/{game_id}/logs", response_model=RoundLogsResponse)
def get_logs(game_id: str):
    return logs_payload(game_id)


@router.get("/games/{game_id}/analytics", response_model=AnalyticsResponse)
def get_analytics(game_id: str):
    return analytics_payload(game_id)
