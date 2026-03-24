from __future__ import annotations

import json
from dataclasses import asdict
from typing import List, Optional

from app.db.database import get_connection
from app.models.domain import GameState, Participant, RoundLog


def serialize_state(state: GameState) -> str:
    return json.dumps(asdict(state), separators=(",", ":"))


def deserialize_state(payload: str) -> GameState:
    raw = json.loads(payload)

    participants = {
        pid: Participant(**participant)
        for pid, participant in raw["participants"].items()
    }
    history = [RoundLog(**item) for item in raw.get("history", [])]

    return GameState(
        game_id=raw["game_id"],
        player_name=raw["player_name"],
        max_rounds=raw["max_rounds"],
        current_round=raw["current_round"],
        status=raw["status"],
        phase=raw["phase"],
        participants=participants,
        trust=raw["trust"],
        suspicion=raw["suspicion"],
        alliances=raw.get("alliances", []),
        history=history,
        current_event=raw.get("current_event", ""),
        winner=raw.get("winner"),
    )


def save_game(state: GameState) -> None:
    state_json = serialize_state(state)

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO games (game_id, player_name, max_rounds, current_round, status, phase, winner, state_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(game_id) DO UPDATE SET
                current_round=excluded.current_round,
                status=excluded.status,
                phase=excluded.phase,
                winner=excluded.winner,
                state_json=excluded.state_json,
                updated_at=CURRENT_TIMESTAMP
            """,
            (
                state.game_id,
                state.player_name,
                state.max_rounds,
                state.current_round,
                state.status,
                state.phase,
                state.winner,
                state_json,
            ),
        )

        for participant in state.participants.values():
            conn.execute(
                """
                INSERT INTO participants (game_id, participant_id, name, is_human, hidden_objective, traits_json, eliminated_round)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(game_id, participant_id) DO UPDATE SET
                    eliminated_round=excluded.eliminated_round,
                    traits_json=excluded.traits_json
                """,
                (
                    state.game_id,
                    participant.participant_id,
                    participant.name,
                    1 if participant.is_human else 0,
                    participant.hidden_objective,
                    json.dumps(participant.traits),
                    participant.eliminated_round,
                ),
            )


def get_game(game_id: str) -> Optional[GameState]:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT state_json FROM games WHERE game_id = ?",
            (game_id,),
        ).fetchone()
    if not row:
        return None
    return deserialize_state(row["state_json"])


def replace_round_logs(game_id: str, logs: List[RoundLog]) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM round_logs WHERE game_id = ?", (game_id,))
        for log in logs:
            conn.execute(
                """
                INSERT INTO round_logs (game_id, round_number, event, player_action_json, ai_actions_json, votes_json, eliminated_id, summary_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    game_id,
                    log.round_number,
                    log.event,
                    json.dumps(log.player_action),
                    json.dumps(log.ai_actions),
                    json.dumps(log.votes),
                    log.eliminated_id,
                    json.dumps(log.summary),
                ),
            )


def get_round_logs(game_id: str) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT round_number, event, player_action_json, ai_actions_json, votes_json, eliminated_id, summary_json FROM round_logs WHERE game_id = ? ORDER BY round_number ASC",
            (game_id,),
        ).fetchall()

    return [
        {
            "round_number": row["round_number"],
            "event": row["event"],
            "player_action": json.loads(row["player_action_json"]),
            "ai_actions": json.loads(row["ai_actions_json"]),
            "votes": json.loads(row["votes_json"]),
            "eliminated_id": row["eliminated_id"],
            "summary": json.loads(row["summary_json"]),
        }
        for row in rows
    ]


def save_analytics(game_id: str, analytics: dict) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO analytics_snapshots (game_id, analytics_json)
            VALUES (?, ?)
            ON CONFLICT(game_id) DO UPDATE SET
                analytics_json=excluded.analytics_json,
                updated_at=CURRENT_TIMESTAMP
            """,
            (game_id, json.dumps(analytics)),
        )


def get_analytics(game_id: str) -> Optional[dict]:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT analytics_json FROM analytics_snapshots WHERE game_id = ?",
            (game_id,),
        ).fetchone()

    if not row:
        return None
    return json.loads(row["analytics_json"])
