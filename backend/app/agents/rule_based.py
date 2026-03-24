from __future__ import annotations

from typing import Dict, List

from app.models.domain import GameState


def sorted_alive_ids(state: GameState) -> List[str]:
    return sorted(state.alive_ids())


def choose_ai_action(state: GameState, actor_id: str) -> Dict[str, str]:
    actor = state.participants[actor_id]
    alive = [pid for pid in sorted_alive_ids(state) if pid != actor_id]
    if not alive:
        return {"actor_id": actor_id, "action_type": "quiet", "target_id": ""}

    susp_scores = [(pid, state.suspicion[actor_id][pid]) for pid in alive]
    trust_scores = [(pid, state.trust[actor_id][pid]) for pid in alive]

    top_sus_target, top_sus = max(susp_scores, key=lambda x: (x[1], -ord(x[0][-1])))
    top_trust_target, top_trust = max(trust_scores, key=lambda x: (x[1], -ord(x[0][-1])))

    aggr = actor.traits["aggressiveness"]
    loyal = actor.traits["loyalty"]
    deceptive = actor.traits["deception_tendency"]
    sociable = actor.traits["sociability"]

    if top_sus > 60 and aggr >= 0.6:
        return {"actor_id": actor_id, "action_type": "accuse", "target_id": top_sus_target}

    if top_trust > 62 and loyal >= 0.6:
        return {
            "actor_id": actor_id,
            "action_type": "build_alliance",
            "target_id": top_trust_target,
        }

    if top_sus > 50 and deceptive >= 0.6:
        return {"actor_id": actor_id, "action_type": "spread_doubt", "target_id": top_sus_target}

    if sociable >= 0.7 and top_trust > 52:
        return {"actor_id": actor_id, "action_type": "defend", "target_id": top_trust_target}

    return {"actor_id": actor_id, "action_type": "quiet", "target_id": ""}


def choose_vote_target(state: GameState, actor_id: str) -> str:
    alive = [pid for pid in sorted_alive_ids(state) if pid != actor_id]
    actor = state.participants[actor_id]

    def score(target: str) -> float:
        suspicion = state.suspicion[actor_id][target]
        trust = state.trust[actor_id][target]
        alliance_bonus = 15 if sorted([actor_id, target]) in state.alliances else 0
        return suspicion - (trust * actor.traits["loyalty"] * 0.35) - alliance_bonus

    return max(alive, key=lambda pid: (score(pid), -ord(pid[-1])))
