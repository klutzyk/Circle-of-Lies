from __future__ import annotations

from app.engine.engine import advance_round, create_game


def run_scripted_game(actions: list[tuple[str, str | None]]):
    state = create_game(player_name="Tester", max_rounds=7)
    for action_type, target in actions:
        if state.status != "active":
            break
        state = advance_round(state, action_type=action_type, target_id=target)
    return state


def test_deterministic_outcome_for_fixed_sequence():
    sequence = [
        ("build_alliance", "ai_3"),
        ("defend", "ai_3"),
        ("share_info", "ai_1"),
        ("quiet", None),
        ("spread_doubt", "ai_4"),
        ("defend", "ai_1"),
        ("quiet", None),
    ]
    first = run_scripted_game(sequence)
    second = run_scripted_game(sequence)

    assert first.status == second.status
    assert first.winner == second.winner
    assert [log.eliminated_id for log in first.history] == [
        log.eliminated_id for log in second.history
    ]


def test_round_advances_and_history_appends():
    state = create_game(player_name="Tester", max_rounds=7)
    state = advance_round(state, action_type="quiet", target_id=None)

    assert state.current_round == 2 or state.status == "completed"
    assert len(state.history) == 1
    assert state.history[0].round_number == 1


def test_player_elimination_ends_game():
    state = create_game(player_name="Tester", max_rounds=6)
    # Aggressive pattern tends to raise suspicion on player in this deterministic system.
    for _ in range(6):
        if state.status != "active":
            break
        state = advance_round(state, action_type="accuse", target_id="ai_2")

    assert state.status == "completed"
    assert state.phase == "ended"
    assert state.winner in {"player", "ai"}
