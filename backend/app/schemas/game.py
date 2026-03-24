from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class StartGameRequest(BaseModel):
    player_name: str = Field(min_length=1, max_length=32)
    max_rounds: int = Field(default=7, ge=6, le=8)


class PlayerActionRequest(BaseModel):
    action_type: str
    target_id: Optional[str] = None


class ActionCatalogItem(BaseModel):
    action_type: str
    label: str
    needs_target: bool
    description: str


class GameSummaryResponse(BaseModel):
    game_id: str
    current_round: int
    max_rounds: int
    status: str
    phase: str
    winner: Optional[str]


class GameStateResponse(BaseModel):
    summary: GameSummaryResponse
    state: dict


class RoundLogsResponse(BaseModel):
    game_id: str
    logs: list[dict]


class AnalyticsResponse(BaseModel):
    game_id: str
    analytics: dict


class FlavorDialogueRequest(BaseModel):
    speaker_id: str


class StoryTurnRequest(BaseModel):
    player_text: str = Field(min_length=1, max_length=500)


class LLMEnhancementResponse(BaseModel):
    game_id: str
    use_case: str
    text: str
    provider: str
    model: str
    cached: bool
    enabled: bool
    reason: str = ""
