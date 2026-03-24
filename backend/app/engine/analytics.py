from __future__ import annotations

from typing import Dict, List

from app.models.domain import GameState


def strategy_archetype(player_actions: List[str]) -> str:
    if not player_actions:
        return "Unknown"

    counts: Dict[str, int] = {}
    for action in player_actions:
        counts[action] = counts.get(action, 0) + 1

    if counts.get("accuse", 0) + counts.get("spread_doubt", 0) >= len(player_actions) // 2 + 1:
        return "Pressure Manipulator"
    if counts.get("build_alliance", 0) + counts.get("defend", 0) >= len(player_actions) // 2 + 1:
        return "Coalition Builder"
    if counts.get("quiet", 0) >= len(player_actions) // 2:
        return "Low-Visibility Survivor"
    return "Adaptive Balancer"


def turning_points(state: GameState) -> List[Dict[str, object]]:
    points: List[Dict[str, object]] = []
    prev_trust = None
    prev_suspicion = None

    for log in state.history:
        t = log.summary["player_avg_trust"]
        s = log.summary["player_avg_suspicion"]

        if prev_trust is not None:
            if abs(t - prev_trust) >= 8:
                points.append(
                    {
                        "round": log.round_number,
                        "type": "trust_shift",
                        "delta": round(t - prev_trust, 2),
                        "reason": f"Trust moved after player used {log.player_action['action_type']}.",
                    }
                )
            if abs(s - prev_suspicion) >= 8:
                points.append(
                    {
                        "round": log.round_number,
                        "type": "suspicion_shift",
                        "delta": round(s - prev_suspicion, 2),
                        "reason": "Suspicion changed significantly during social resolution and vote.",
                    }
                )

        prev_trust = t
        prev_suspicion = s

    return points


def build_analytics(state: GameState) -> Dict[str, object]:
    rounds = []
    player_actions = []
    for log in state.history:
        rounds.append(
            {
                "round": log.round_number,
                "player_avg_trust": log.summary["player_avg_trust"],
                "player_avg_suspicion": log.summary["player_avg_suspicion"],
                "eliminated_id": log.eliminated_id,
            }
        )
        player_actions.append(log.player_action["action_type"])

    survived = state.participants["player"].eliminated_round is None
    outcome_reason = (
        "Player maintained enough trust to avoid decisive vote targeting."
        if survived
        else "Player suspicion outpaced coalition protection in the vote phase."
    )

    return {
        "survived": survived,
        "winner": state.winner,
        "strategy_archetype": strategy_archetype(player_actions),
        "trust_timeline": [
            {"round": r["round"], "value": r["player_avg_trust"]} for r in rounds
        ],
        "suspicion_timeline": [
            {"round": r["round"], "value": r["player_avg_suspicion"]} for r in rounds
        ],
        "round_snapshots": rounds,
        "turning_points": turning_points(state),
        "outcome_reason": outcome_reason,
        "game_theory_tags": [
            "signaling",
            "bluffing",
            "incomplete_information",
            "coalition_formation",
            "reputation_effects",
            "strategic_visibility",
        ],
    }
