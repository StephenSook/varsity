from verify.faithfulness_eval import STRUCTURAL, evaluate


def test_positives_are_not_blocked() -> None:
    r = evaluate()
    assert r.positives_passed == r.positives_total  # faithful explanations pass the gate


def test_structural_injections_have_zero_leakage() -> None:
    r = evaluate()
    # every structural injection is caught deterministically on every positive
    for name in STRUCTURAL:
        assert r.caught[name] == r.total_per_class, f"{name} leaked"
    assert r.structural_leaks == 0


def test_semantic_injections_need_the_advisory_layer() -> None:
    # an honest boundary: a swapped name / changed number still cites the Law, restates the
    # right verdict, and stays neutral, so the DETERMINISTIC gate cannot catch them - they are
    # the advisory Granite Guardian groundedness layer's job.
    r = evaluate()
    assert r.caught["swap_name"] == 0
    assert r.caught["change_number"] == 0
