from __future__ import annotations

import uuid
from typing import Dict, List, Optional

from app.agents.rule_based import choose_ai_action, choose_vote_target
from app.engine.actions import VALID_ACTIONS
from app.engine.state import (
    build_default_participants,
    clamp,
    current_event,
    initialize_matrix,
)
from app.models.domain import GameState, RoundLog


def create_game(
    player_name: str,
    max_rounds: int,
    participants: Optional[dict] = None,
) -> GameState:
    participants = participants or build_default_participants(player_name)
    ids = list(participants.keys())
    trust = initialize_matrix(ids, 50)
    suspicion = initialize_matrix(ids, 25)

    return GameState(
        game_id=str(uuid.uuid4()),
        player_name=player_name,
        max_rounds=max_rounds,
        current_round=1,
        status="active",
        phase="awaiting_player_action",
        participants=participants,
        trust=trust,
        suspicion=suspicion,
        current_event=current_event(1),
    )


def _apply_social_delta(
    state: GameState,
    source: str,
    target: Optional[str],
    trust_delta: float,
    suspicion_delta: float,
) -> None:
    if target and target in state.participants and target != source:
        state.trust[target][source] = clamp(state.trust[target][source] + trust_delta)
        state.suspicion[target][source] = clamp(
            state.suspicion[target][source] + suspicion_delta
        )


def _apply_action(state: GameState, actor_id: str, action_type: str, target_id: Optional[str]) -> None:
    alive = state.alive_ids()
    if target_id and target_id not in alive:
        target_id = None

    if action_type == "defend" and target_id:
        _apply_social_delta(state, actor_id, target_id, trust_delta=9, suspicion_delta=-5)
        _apply_social_delta(state, actor_id, actor_id, trust_delta=2, suspicion_delta=0)
    elif action_type == "accuse" and target_id:
        for observer in alive:
            if observer != target_id:
                state.suspicion[observer][target_id] = clamp(
                    state.suspicion[observer][target_id] + 6
                )
        for observer in alive:
            if observer != actor_id:
                state.suspicion[observer][actor_id] = clamp(
                    state.suspicion[observer][actor_id] + 2
                )
    elif action_type == "quiet":
        for observer in alive:
            if observer != actor_id:
                state.suspicion[observer][actor_id] = clamp(
                    state.suspicion[observer][actor_id] - 3
                )
    elif action_type == "share_info" and target_id:
        _apply_social_delta(state, actor_id, target_id, trust_delta=8, suspicion_delta=-4)
    elif action_type == "build_alliance" and target_id:
        _apply_social_delta(state, actor_id, target_id, trust_delta=10, suspicion_delta=-3)
        _apply_social_delta(state, actor_id, actor_id, trust_delta=1, suspicion_delta=0)
    elif action_type == "spread_doubt" and target_id:
        for observer in alive:
            if observer != target_id:
                state.suspicion[observer][target_id] = clamp(
                    state.suspicion[observer][target_id] + 4
                )
        for observer in alive:
            if observer != actor_id:
                state.trust[observer][actor_id] = clamp(state.trust[observer][actor_id] - 2)


def _update_alliances(state: GameState) -> None:
    alive = sorted(state.alive_ids())
    alliances: List[List[str]] = []
    for i, a in enumerate(alive):
        for b in alive[i + 1 :]:
            if state.trust[a][b] >= 65 and state.trust[b][a] >= 65:
                if state.suspicion[a][b] <= 40 and state.suspicion[b][a] <= 40:
                    alliances.append([a, b])
    state.alliances = alliances


def _resolve_votes(state: GameState) -> tuple[Dict[str, str], Optional[str]]:
    alive = sorted(state.alive_ids())
    votes: Dict[str, str] = {}
    counts: Dict[str, int] = {pid: 0 for pid in alive}

    for voter in alive:
        target = choose_vote_target(state, voter)
        votes[voter] = target
        counts[target] += 1

    eliminated = max(
        alive,
        key=lambda pid: (
            counts[pid],
            sum(state.suspicion[o][pid] for o in alive if o != pid),
            -ord(pid[-1]),
        ),
    )

    state.participants[eliminated].eliminated_round = state.current_round
    return votes, eliminated


def _player_avg(state: GameState, matrix: Dict[str, Dict[str, float]]) -> float:
    observers = [pid for pid in state.alive_ids() if pid != "player"]
    if not observers:
        return 0.0
    return round(sum(matrix[pid]["player"] for pid in observers) / len(observers), 2)


def _is_game_over(state: GameState) -> bool:
    player_alive = state.participants["player"].eliminated_round is None
    if not player_alive:
        state.status = "completed"
        state.winner = "ai"
        state.phase = "ended"
        return True

    if state.current_round >= state.max_rounds:
        state.status = "completed"
        state.winner = "player"
        state.phase = "ended"
        return True

    if len(state.alive_ids()) <= 2:
        state.status = "completed"
        state.winner = "player" if player_alive else "ai"
        state.phase = "ended"
        return True

    return False


def advance_round(state: GameState, action_type: str, target_id: Optional[str]) -> GameState:
    if state.status != "active":
        raise ValueError("Game is not active")
    if state.phase != "awaiting_player_action":
        raise ValueError("Game is not ready for player action")
    if action_type not in VALID_ACTIONS:
        raise ValueError(f"Invalid action type: {action_type}")

    alive = state.alive_ids()
    if target_id and target_id not in alive:
        raise ValueError("Target is not alive")

    player_action = {
        "actor_id": "player",
        "action_type": action_type,
        "target_id": target_id or "",
    }
    _apply_action(state, "player", action_type, target_id)

    state.phase = "ai_resolution"
    ai_actions = []
    for ai_id in sorted(pid for pid in alive if pid != "player"):
        if state.participants[ai_id].eliminated_round is not None:
            continue
        ai_action = choose_ai_action(state, ai_id)
        ai_actions.append(ai_action)
        _apply_action(state, ai_id, ai_action["action_type"], ai_action["target_id"] or None)

    _update_alliances(state)
    state.phase = "voting"
    votes, eliminated_id = _resolve_votes(state)

    summary = {
        "player_avg_trust": _player_avg(state, state.trust),
        "player_avg_suspicion": _player_avg(state, state.suspicion),
        "alive_after_vote": state.alive_ids(),
    }

    state.history.append(
        RoundLog(
            round_number=state.current_round,
            event=state.current_event,
            player_action=player_action,
            ai_actions=ai_actions,
            votes=votes,
            eliminated_id=eliminated_id,
            summary=summary,
        )
    )

    if _is_game_over(state):
        return state

    state.current_round += 1
    state.phase = "awaiting_player_action"
    state.current_event = current_event(state.current_round)
    return state
