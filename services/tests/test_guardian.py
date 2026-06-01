from app.llm.guardian import cites_law_clause


def test_cites_law_clause_true() -> None:
    assert cites_law_clause("Under Law 11, the attacker was offside.") is True
    assert cites_law_clause("This is governed by law 12 on fouls.") is True


def test_cites_law_clause_false() -> None:
    assert cites_law_clause("The attacker was simply ahead, no rule mentioned.") is False
    assert cites_law_clause("") is False
