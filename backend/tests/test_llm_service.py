from app.llm.service import generate_post_game_analysis


def test_llm_disabled_fallback(monkeypatch):
    monkeypatch.setattr("app.llm.service.LLM_ENABLED", False)

    result = generate_post_game_analysis("game-1", logs=[], analytics={})

    assert result.enabled is False
    assert result.provider == "none"
    assert "deterministic" in result.text.lower()
