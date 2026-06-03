from app import provenance
from app.geometry import FreezeFramePlayer
from app.pipeline import explanation_stages


class FakeGranite:
    def explain_offside(self, *, margin_meters, is_offside, law_text, language="English"):
        state = "offside" if is_offside else "onside"
        return f"Under Law 11, the attacker was {state} by {abs(margin_meters):.2f} meters."


class FakeGuardian:
    def check(self, explanation, *, law_context=""):
        from app.llm.guardian import GuardianVerdict, cites_law_clause

        cited = cites_law_clause(explanation)
        return GuardianVerdict(safe=cited, cites_law=cited, grounded=True, model_answer="No")


def _frame():
    return [
        FreezeFramePlayer(x=100.0, y=40.0, teammate=True),
        FreezeFramePlayer(x=50.0, y=40.0, teammate=True, actor=True),
        FreezeFramePlayer(x=98.0, y=42.0, teammate=False),
        FreezeFramePlayer(x=119.0, y=40.0, teammate=False, keeper=True),
    ]


def test_links_from_proof_uses_the_finer_clause_when_present() -> None:
    steps = [
        {
            "claim": "Nearer the goal line than the second-to-last opponent.",
            "law": "11.1",
            "status": "pass",
            "clause": "beyond the second-to-last opponent",
        }
    ]
    links = provenance.links_from_proof(steps)
    assert links[0].law_clause == "Law 11.1 (beyond the second-to-last opponent)"


def test_links_from_proof_carry_clause_and_source() -> None:
    steps = [
        {"claim": "In the opponents' half.", "law": "11.1", "status": "pass"},
        {"claim": "From a goal kick.", "law": "11.3", "status": "n/a"},
    ]
    links = provenance.links_from_proof(steps)
    assert links[0].law_clause == "Law 11.1"
    assert links[0].evidence == "met in the Law 11 proof"
    assert links[0].source == "StatsBomb 360 freeze-frame"
    assert links[1].evidence == "not applicable in the Law 11 proof"


def test_manifest_hash_is_deterministic_and_excludes_itself() -> None:
    kw = dict(
        decision_id="offside +5.45m",
        source="Canada vs Morocco",
        law="11",
        law_title="Offside",
        model="granite",
        grounded=True,
        verified=True,
        links=[provenance.link_from_law(law="11", law_title="Offside", law_text="A player...")],
    )
    a = provenance.build_manifest(**kw)
    b = provenance.build_manifest(**kw)
    assert a.manifest_hash == b.manifest_hash  # deterministic
    assert a.manifest_hash.startswith("sha256:")
    # a different grounding chain -> a different hash (tamper-evident)
    c = provenance.build_manifest(**{**kw, "grounded": False})
    assert c.manifest_hash != a.manifest_hash


def test_provenance_stage_shape() -> None:
    m = provenance.build_manifest(
        decision_id="penalty",
        source="x",
        law="14",
        law_title="The Penalty Kick",
        model="granite",
        grounded=True,
        verified=True,
        links=[provenance.link_from_law(law="14", law_title="The Penalty Kick", law_text="t")],
    )
    s = provenance.provenance_stage(m)
    assert s["stage"] == "provenance"
    assert s["link_count"] == 1
    assert s["manifest_hash"].startswith("sha256:")
    assert {"decision_id", "law", "corpus", "grounded", "verified", "links"} <= set(s)


def test_offside_pipeline_emits_complete_manifest() -> None:
    stages = {
        s["stage"]: s
        for s in explanation_stages(_frame(), granite=FakeGranite(), guardian=FakeGuardian())
    }
    prov = stages["provenance"]
    assert prov["proof_consistent"] is True
    assert prov["law"] == "11"
    # every Law-11 proof step is represented in the grounding chain + the law link
    assert prov["link_count"] == len(stages["proof"]["steps"]) + 1
    assert prov["margin_meters"] == stages["geometry"]["margin_meters"]
    assert prov["manifest_hash"].startswith("sha256:")
