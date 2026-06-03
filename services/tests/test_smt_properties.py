from verify.law11_smt import prove_all


def test_all_law11_safety_properties_proved() -> None:
    """Z3 proves the three Law-11 safety properties (negation unsatisfiable, non-vacuously)."""
    results = prove_all()
    assert len(results) == 3
    for r in results:
        assert r.non_vacuous, f"{r.name}: base model vacuously unsatisfiable (proof meaningless)"
        assert r.proved, f"{r.name}: safety property NOT proved (its negation was satisfiable)"
