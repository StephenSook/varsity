import app.llm.guardian as guardian_mod
from app.llm.guardian import GuardianClient, cites_law_clause


def test_cites_law_clause_true() -> None:
    assert cites_law_clause("Under Law 11, the attacker was offside.") is True
    assert cites_law_clause("This is governed by law 12 on fouls.") is True


def test_cites_law_clause_false() -> None:
    assert cites_law_clause("The attacker was simply ahead, no rule mentioned.") is False
    assert cites_law_clause("") is False


def test_cites_law_clause_multilingual() -> None:
    assert cites_law_clause("Según la Ley 11, el jugador estaba fuera de juego.") is True
    assert cites_law_clause("Selon la Loi 11, le joueur etait hors-jeu.") is True


def _patch_chat(monkeypatch, answer):
    # Guardian now uses the chat endpoint; a fixed answer applies to both criteria.
    monkeypatch.setattr(guardian_mod._watsonx, "chat", lambda *a, **k: answer)


def test_guardian_safe_when_grounded_and_cites(monkeypatch) -> None:
    _patch_chat(monkeypatch, "No")  # "No" = no risk
    v = GuardianClient().check("Under Law 11, the attacker was offside.", law_context="Law 11 text")
    assert v.grounded is True
    assert v.screen_reader_ok is True
    assert v.cites_law is True
    assert v.safe is True
    assert v.risk_label == "No"


def test_guardian_unsafe_when_not_grounded(monkeypatch) -> None:
    _patch_chat(monkeypatch, "Yes")  # "Yes" = risk present
    v = GuardianClient().check("Under Law 11, the attacker was offside.", law_context="ctx")
    assert v.grounded is False
    assert v.safe is False
    assert v.risk_label == "Yes"


def test_guardian_flags_screen_reader_unsafe(monkeypatch) -> None:
    # Criterion-aware mock: only the screen-reader criterion fires for markdown content.
    def fake_chat(model, messages, **k):
        criterion = messages[0]["content"].lower()
        return "Yes" if "screen reader" in criterion else "No"

    monkeypatch.setattr(guardian_mod._watsonx, "chat", fake_chat)
    v = GuardianClient().check("Under **Law 11** | table |, offside.", law_context="ctx")
    assert v.grounded is True
    assert v.screen_reader_ok is False
    assert v.safe is False  # grounded + cites a Law, but not screen-reader-safe


def test_guardian_unsafe_when_no_law_cited(monkeypatch) -> None:
    _patch_chat(monkeypatch, "No")
    v = GuardianClient().check("The attacker was clearly ahead.", law_context="ctx")
    assert v.cites_law is False
    assert v.safe is False  # grounded but cites no Law number


def test_guardian_defaults_safe_on_error(monkeypatch) -> None:
    def boom(*a, **k):
        raise RuntimeError("watsonx unavailable")

    monkeypatch.setattr(guardian_mod._watsonx, "chat", boom)
    v = GuardianClient().check("Under Law 11, the attacker was offside.", law_context="ctx")
    assert v.risk_label == "Failed"
    assert v.grounded is True
    assert v.screen_reader_ok is True
    assert v.safe is True  # infra flakiness must not fail a Law-cited answer
