from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


TraitMap = Dict[str, float]
Matrix = Dict[str, Dict[str, float]]


@dataclass
class Participant:
    participant_id: str
    name: str
    is_human: bool
    traits: TraitMap
    hidden_objective: str
    occupation: str = ""
    backstory: str = ""
    persona: str = ""
    eliminated_round: Optional[int] = None


@dataclass
class RoundLog:
    round_number: int
    event: str
    player_action: Dict[str, str]
    ai_actions: List[Dict[str, str]]
    votes: Dict[str, str]
    eliminated_id: Optional[str]
    summary: Dict[str, object]


@dataclass
class GameState:
    game_id: str
    player_name: str
    max_rounds: int
    current_round: int
    status: str
    phase: str
    participants: Dict[str, Participant]
    trust: Matrix
    suspicion: Matrix
    alliances: List[List[str]] = field(default_factory=list)
    history: List[RoundLog] = field(default_factory=list)
    story_events: List[Dict[str, object]] = field(default_factory=list)
    current_event: str = ""
    winner: Optional[str] = None
    scene_step: int = 0

    def alive_ids(self) -> List[str]:
        return [
            pid
            for pid, participant in self.participants.items()
            if participant.eliminated_round is None
        ]
