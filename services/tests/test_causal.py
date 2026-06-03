from app import causal


def test_offside_is_framed_against_the_onside_foil() -> None:
    c = causal.contrastive(is_offside=True, margin_meters=5.45)
    assert c["stage"] == "causal"
    assert c["fact"] == "offside" and c["foil"] == "onside"
    assert c["opener"] == "Offside, rather than onside."
    assert c["margin_cm"] == 545
    assert "further back" in c["narration"]  # the contrastive counterfactual
    assert c["responsibility"] == 1.0 and c["contingency_set_size"] == 0


def test_onside_is_framed_against_the_offside_foil() -> None:
    c = causal.contrastive(is_offside=False, margin_meters=-3.01)
    assert c["fact"] == "onside" and c["foil"] == "offside"
    assert c["opener"] == "Onside, rather than offside."
    assert "further forward" in c["narration"]
    assert c["margin_cm"] == 301


def test_within_noise_flags_a_knife_edge_call_without_adjudicating() -> None:
    c = causal.contrastive(is_offside=True, margin_meters=0.02, within_noise=True)
    assert c["within_noise"] is True
    low = c["narration"].lower()
    assert "knife-edge" in low and "trusts the official" in low


def test_decisive_cause_is_the_margin_not_a_body_part() -> None:
    # we have no body-part keypoints (StatsBomb 360 role-booleans only); the honest decisive
    # cause is the margin, never a fabricated "torso vs foot" claim.
    c = causal.contrastive(is_offside=True, margin_meters=0.50)
    assert c["decisive_cause"] == "the attacker's margin to the offside line"
    assert "torso" not in c["narration"].lower() and "foot" not in c["narration"].lower()
