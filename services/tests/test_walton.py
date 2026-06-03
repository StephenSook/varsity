from app import walton


def test_offside_questions_are_grounded_and_cite_the_law() -> None:
    cq = walton.critical_questions(is_offside=True, margin_meters=5.45)
    assert cq["stage"] == "critical_questions"
    assert "expert opinion" in cq["scheme"].lower()
    assert len(cq["questions"]) == 4
    first = cq["questions"][0]
    assert "Offside under Law 11" in first["a"] and "5.45 m" in first["a"]


def test_within_noise_defers_to_the_official_without_re_judging() -> None:
    cq = walton.critical_questions(is_offside=True, margin_meters=0.02, within_noise=True)
    consistency = cq["questions"][3]["a"].lower()
    assert "knife-edge" in consistency and "trusts the official" in consistency


def test_questions_defend_authority_and_evidence_never_adjudicate() -> None:
    cq = walton.critical_questions(is_offside=False, margin_meters=-3.01)
    joined = " ".join(q["a"].lower() for q in cq["questions"])
    assert "onside under law 11" in joined
    assert "auditable law-11 proof" in joined  # backing evidence
    # never opines that the call was right or wrong
    assert "wrong" not in joined and "mistake" not in joined
