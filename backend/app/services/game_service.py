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
from app.engine.engine import create_game
from app.engine.state import (
    build_participants_from_generated_cast,
    clamp,
    current_event,
    to_public_state,
)
from app.llm.service import (
    generate_character_cast,
    generate_flavor_dialogue,
    generate_post_game_analysis,
    generate_turn_resolution,
)
from app.models.domain import GameState, RoundLog


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

    alive_ids_before = state.alive_ids()
    cast = [
        {
            "participant_id": pid,
            "name": p.name,
            "persona": p.persona,
            "traits": p.traits,
        }
        for pid, p in state.participants.items()
        if pid != "player" and p.eliminated_round is None
    ]
    history_tail = [
        {
            "round": log.round_number,
            "event": log.event,
            "player_action": log.player_action,
            "eliminated_id": log.eliminated_id,
            "player_avg_trust": log.summary.get("player_avg_trust"),
            "player_avg_suspicion": log.summary.get("player_avg_suspicion"),
        }
        for log in state.history[-3:]
    ]
    recent_story_tail = [
        {
            "round_number": event.get("round_number"),
            "scene_step": event.get("scene_step"),
            "narration": event.get("narration"),
            "dialogue": event.get("dialogue", []),
            "eliminated_id": event.get("eliminated_id"),
        }
        for event in state.story_events[-3:]
        if isinstance(event, dict)
    ]
    llm_turn = generate_turn_resolution(
        game_id=game_id,
        round_number=state.current_round,
        scene_step=state.scene_step,
        event=state.current_event,
        player_name=state.player_name,
        player_text=player_text,
        cast=cast,
        history_tail=history_tail,
        recent_story_tail=recent_story_tail,
    )

    # LLM-driven trust/suspicion update on player.
    trust_on_player = llm_turn.get("trust_on_player", {}) if isinstance(llm_turn, dict) else {}
    suspicion_on_player = (
        llm_turn.get("suspicion_on_player", {}) if isinstance(llm_turn, dict) else {}
    )
    for pid in alive_ids_before:
        if pid == "player":
            continue
        if pid in trust_on_player:
            try:
                state.trust[pid]["player"] = clamp(float(trust_on_player[pid]))
            except (TypeError, ValueError):
                pass
        if pid in suspicion_on_player:
            try:
                state.suspicion[pid]["player"] = clamp(float(suspicion_on_player[pid]))
            except (TypeError, ValueError):
                pass

    # Conversation-first pacing: vote/elimination only on the second scene step.
    is_vote_step = state.scene_step >= 1
    eliminated_id = str(llm_turn.get("eliminated_id", "") or "") if is_vote_step else ""
    if eliminated_id and eliminated_id in alive_ids_before:
        state.participants[eliminated_id].eliminated_round = state.current_round

    def _player_avg(matrix: dict) -> float:
        observers = [
            pid
            for pid, participant in state.participants.items()
            if pid != "player" and participant.eliminated_round is None
        ]
        if not observers:
            return 0.0
        return round(sum(matrix[pid]["player"] for pid in observers) / len(observers), 2)

    ai_actions = llm_turn.get("ai_actions", []) if isinstance(llm_turn, dict) else []
    if not isinstance(ai_actions, list):
        ai_actions = []

    summary = {
        "player_avg_trust": _player_avg(state.trust),
        "player_avg_suspicion": _player_avg(state.suspicion),
        "alive_after_vote": state.alive_ids(),
    }

    state.story_events.append(
        {
            "round_number": state.current_round,
            "scene_step": state.scene_step + 1,
            "player_text": player_text,
            "narration": llm_turn.get("narration", ""),
            "dialogue": llm_turn.get("dialogue", []),
            "eliminated_id": eliminated_id or None,
            "summary": summary,
        }
    )

    if is_vote_step:
        state.history.append(
            RoundLog(
                round_number=state.current_round,
                event=state.current_event,
                player_action={"actor_id": "player", "action_type": "dialogue_turn", "target_id": ""},
                ai_actions=ai_actions[:5],
                votes={},
                eliminated_id=eliminated_id or None,
                summary=summary,
            )
        )

        player_alive = state.participants["player"].eliminated_round is None
        if not player_alive:
            state.status = "completed"
            state.phase = "ended"
            state.winner = "ai"
        elif state.current_round >= state.max_rounds or len(state.alive_ids()) <= 2:
            state.status = "completed"
            state.phase = "ended"
            state.winner = "player"
        else:
            state.current_round += 1
            state.current_event = current_event(state.current_round)
            state.phase = "awaiting_player_action"
        state.scene_step = 0
    else:
        state.scene_step += 1
        state.phase = "awaiting_player_action"

    save_game(state)
    replace_round_logs(state.game_id, state.history)
    if state.status == "completed":
        analytics = build_analytics(state)
        save_analytics(state.game_id, analytics)

    payload = public_game_payload(state)
    payload["story"] = {
        "player_text": player_text,
        "interpreted_action": "dialogue_turn",
        "interpreted_target_id": "",
        "narration": llm_turn.get("narration", ""),
        "dialogue": llm_turn.get("dialogue", []),
        "vote_resolved": is_vote_step,
        "llm_error": llm_turn.get("_error", ""),
    }
    return payload
