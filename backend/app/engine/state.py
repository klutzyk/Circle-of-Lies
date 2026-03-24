from __future__ import annotations

from typing import Dict, List

from app.models.domain import GameState, Participant


EVENT_ROTATION = [
    "Resource allocation challenge",
    "Conflicting witness reports",
    "Secret pair immunity rumor",
    "Public negotiation task",
    "Trust contract proposal",
    "Crisis vote pressure",
    "Final influence scramble",
    "Endgame credibility check",
]


def build_default_participants(player_name: str) -> Dict[str, Participant]:
    templates = [
        (
            "ai_1",
            "Mara",
            {
                "sociability": 0.8,
                "aggressiveness": 0.4,
                "loyalty": 0.7,
                "risk_tolerance": 0.5,
                "deception_tendency": 0.3,
                "charisma": 0.8,
                "suspicion_sensitivity": 0.5,
            },
            "Protect a trusted ally until round 6.",
        ),
        (
            "ai_2",
            "Jalen",
            {
                "sociability": 0.5,
                "aggressiveness": 0.8,
                "loyalty": 0.4,
                "risk_tolerance": 0.7,
                "deception_tendency": 0.6,
                "charisma": 0.6,
                "suspicion_sensitivity": 0.7,
            },
            "Force out high-charisma rivals.",
        ),
        (
            "ai_3",
            "Nia",
            {
                "sociability": 0.7,
                "aggressiveness": 0.5,
                "loyalty": 0.8,
                "risk_tolerance": 0.4,
                "deception_tendency": 0.2,
                "charisma": 0.7,
                "suspicion_sensitivity": 0.6,
            },
            "Maintain the strongest alliance network.",
        ),
        (
            "ai_4",
            "Orion",
            {
                "sociability": 0.4,
                "aggressiveness": 0.7,
                "loyalty": 0.5,
                "risk_tolerance": 0.8,
                "deception_tendency": 0.8,
                "charisma": 0.4,
                "suspicion_sensitivity": 0.5,
            },
            "Reach the end with minimal direct blame.",
        ),
        (
            "ai_5",
            "Selene",
            {
                "sociability": 0.9,
                "aggressiveness": 0.3,
                "loyalty": 0.6,
                "risk_tolerance": 0.4,
                "deception_tendency": 0.4,
                "charisma": 0.9,
                "suspicion_sensitivity": 0.4,
            },
            "Keep trust score above group median.",
        ),
    ]

    participants: Dict[str, Participant] = {
        "player": Participant(
            participant_id="player",
            name=player_name,
            is_human=True,
            traits={
                "sociability": 0.6,
                "aggressiveness": 0.5,
                "loyalty": 0.5,
                "risk_tolerance": 0.5,
                "deception_tendency": 0.5,
                "charisma": 0.6,
                "suspicion_sensitivity": 0.5,
            },
            hidden_objective="Survive to final round with positive social capital.",
        )
    }

    for pid, name, traits, objective in templates:
        participants[pid] = Participant(
            participant_id=pid,
            name=name,
            is_human=False,
            traits=traits,
            hidden_objective=objective,
        )
    return participants


def initialize_matrix(participant_ids: List[str], baseline: float) -> Dict[str, Dict[str, float]]:
    matrix: Dict[str, Dict[str, float]] = {}
    for source in participant_ids:
        matrix[source] = {}
        for target in participant_ids:
            matrix[source][target] = baseline if source != target else 0.0
    return matrix


def clamp(value: float, floor: float = 0.0, ceiling: float = 100.0) -> float:
    return max(floor, min(ceiling, value))


def current_event(round_number: int) -> str:
    return EVENT_ROTATION[(round_number - 1) % len(EVENT_ROTATION)]


def to_public_state(state: GameState) -> dict:
    return {
        "participants": {
            pid: {
                "name": p.name,
                "is_human": p.is_human,
                "traits": p.traits,
                "eliminated_round": p.eliminated_round,
            }
            for pid, p in state.participants.items()
        },
        "trust": state.trust,
        "suspicion": state.suspicion,
        "alliances": state.alliances,
        "current_event": state.current_event,
        "history": [
            {
                "round_number": log.round_number,
                "event": log.event,
                "player_action": log.player_action,
                "ai_actions": log.ai_actions,
                "votes": log.votes,
                "eliminated_id": log.eliminated_id,
                "summary": log.summary,
            }
            for log in state.history
        ],
    }
