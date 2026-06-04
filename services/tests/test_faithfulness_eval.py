from verify.faithfulness_eval import evaluate, payload


def test_positives_are_not_blocked() -> None:
    r = evaluate()
    assert r.positives_passed == r.positives_total  # faithful explanations pass the gate


def test_structural_injections_have_zero_leakage() -> None:
    r = evaluate()
    # every structural injection is caught deterministically on every applicable positive
    for name, d in r.per_class.items():
        if d["kind"] == "structural":
            assert d["caught"] == d["total"], f"{name} leaked"
    assert r.structural_leaks == 0


def test_semantic_injections_need_the_advisory_layer() -> None:
    # an honest boundary: a swapped name / changed number still cites the Law, restates the
    # right verdict, and stays neutral, so the DETERMINISTIC gate cannot catch them - they are
    # the advisory Granite Guardian groundedness layer's job.
    r = evaluate()
    assert r.per_class["swap_name"]["caught"] == 0
    assert r.per_class["change_number"]["caught"] == 0


def test_covers_offside_penalty_and_handball() -> None:
    r = evaluate()
    assert {"offside", "penalty", "handball"} <= set(r.per_decision)
    for d in r.per_decision.values():
        assert d["positives_passed"] == d["positives"]
        assert d["structural_caught"] == d["structural_total"]  # zero leakage per decision type


def test_payload_surfaces_per_class_and_per_decision() -> None:
    p = payload()
    assert p["structural_leakage"] == 0
    assert any(row["decision"] == "penalty" for row in p["per_decision"])
    assert any(row["kind"] == "structural" for row in p["per_class"])
