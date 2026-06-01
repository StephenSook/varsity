import app.llm.guardian as guardian_mod
from app.llm.guardian import GuardianClient, cites_law_clause


def test_cites_law_clause_true() -> None:
    assert cites_law_clause("Under Law 11, the attacker was offside.") is True
    assert cites_law_clause("This is governed by law 12 on fouls.") is True


def test_cites_law_clause_false() -> None:
    assert cites_law_clause("The attacker was simply ahead, no rule mentioned.") is False
    assert cites_law_clause("") is False


def _patch_generate(monkeypatch, answer):
    monkeypatch.setattr(guardian_mod._watsonx, "generate", lambda *a, **k: answer)


def test_guardian_safe_when_grounded_and_cites(monkeypatch) -> None:
    # Guardian "No" = no risk = grounded.
    _patch_generate(monkeypatch, "No")
    v = GuardianClient().check("Under Law 11, the attacker was offside.", law_context="Law 11 text")
    assert v.grounded is True
    assert v.cites_law is True
    assert v.safe is True
    assert v.risk_label == "No"


def test_guardian_unsafe_when_not_grounded(monkeypatch) -> None:
    # Guardian "Yes" = risk present = NOT grounded.
    _patch_generate(monkeypatch, "Yes")
    v = GuardianClient().check("Under Law 11, the attacker was offside.", law_context="ctx")
    assert v.grounded is False
    assert v.safe is False
    assert v.risk_label == "Yes"


def test_guardian_unsafe_when_no_law_cited(monkeypatch) -> None:
    _patch_generate(monkeypatch, "No")
    v = GuardianClient().check("The attacker was clearly ahead.", law_context="ctx")
    assert v.cites_law is False
    assert v.safe is False  # grounded but cites no Law number


def test_guardian_defaults_grounded_on_error(monkeypatch) -> None:
    def boom(*a, **k):
        raise RuntimeError("watsonx unavailable")

    monkeypatch.setattr(guardian_mod._watsonx, "generate", boom)
    v = GuardianClient().check("Under Law 11, the attacker was offside.", law_context="ctx")
    assert v.risk_label == "Failed"
    assert v.grounded is True
    assert v.safe is True  # infra flakiness must not fail a Law-cited answer
