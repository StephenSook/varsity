"""Machine-checked safety properties of the Law-11 rule structure, via Z3 (Microsoft Research).

Encodes the propositional structure of the offside engine (``app/law11.py`` + ``app/geometry.py``)
as SMT constraints and PROVES three safety properties by showing each property's negation is
unsatisfiable. This is a formal certificate that the rules can never reach a contradictory or
out-of-Law conclusion. It complements, and never replaces, the pure-Python engine that runs in
production; ``z3-solver`` is a dev/CI-only dependency.

Each proof is guarded against vacuous truth: we first confirm the base model is satisfiable
(an offside offence is actually reachable), so an ``unsat`` on the negated property is meaningful
rather than a trivially-empty model.

Mapping to the code (every constraint mirrors a line of the engine):
    in_opp_half          <=> attacker_x > HALFWAY_X (= 60)        geometry.py / law11.py
    beyond_defender      <=> margin_m > 0                          geometry.py
    in_offside_position   = in_opp_half AND beyond_defender AND beyond_ball   law11.py:97
    offside_offence       = in_offside_position AND active AND NOT restart_exception
                            (Law 11.2 active involvement + the Law 11.3 no-offence defeaters;
                             the deployed engine runs the open-play case: restart_exception=False,
                             active=True when in an offside position)
"""

from __future__ import annotations

from dataclasses import dataclass

from z3 import And, Bool, Not, Real, Solver, sat, unsat

HALFWAY_X = 60.0


@dataclass(frozen=True)
class PropertyResult:
    name: str
    proved: bool  # the property's negation is unsatisfiable
    non_vacuous: bool  # the base model admits a true offence (the proof is meaningful)
    detail: str

    @property
    def ok(self) -> bool:
        return self.proved and self.non_vacuous


def _model() -> dict:
    """The shared SMT encoding of the Law-11 rule structure."""
    margin = Real("margin_m")
    attacker_x = Real("attacker_x")
    beyond_ball = Bool("beyond_ball")
    active = Bool("active_involvement")
    restart_exception = Bool("restart_exception")

    beyond_defender = margin > 0
    in_opp_half = attacker_x > HALFWAY_X
    in_offside_position = And(in_opp_half, beyond_defender, beyond_ball)
    offside_offence = And(in_offside_position, active, Not(restart_exception))
    return {
        "margin": margin,
        "in_opp_half": in_opp_half,
        "in_offside_position": in_offside_position,
        "offside_offence": offside_offence,
        "restart_exception": restart_exception,
    }


def _base_satisfiable() -> bool:
    s = Solver()
    s.add(_model()["offside_offence"])
    return s.check() == sat


def _prove(name: str, negation, detail: str) -> PropertyResult:
    s = Solver()
    s.add(negation)
    return PropertyResult(name, s.check() == unsat, _base_satisfiable(), detail)


def prove_mutual_exclusivity() -> PropertyResult:
    m = _model()
    level = m["margin"] == 0  # level with the second-to-last opponent counts as onside (Law 11.1)
    return _prove(
        "mutual_exclusivity",
        And(m["in_offside_position"], level),
        "an offside position and being level (onside) can never both hold",
    )


def prove_own_half_safety() -> PropertyResult:
    m = _model()
    return _prove(
        "own_half_safety",
        And(Not(m["in_opp_half"]), m["offside_offence"]),
        "a player in their own half can never commit an offside offence (Law 11.1)",
    )


def prove_restart_safety() -> PropertyResult:
    m = _model()
    return _prove(
        "restart_safety",
        And(m["restart_exception"], m["offside_offence"]),
        "a goal kick, throw-in or corner can never yield an offside offence (Law 11.3)",
    )


def prove_all() -> list[PropertyResult]:
    return [prove_mutual_exclusivity(), prove_own_half_safety(), prove_restart_safety()]


if __name__ == "__main__":
    all_ok = True
    for r in prove_all():
        print(f"[{'PROVED' if r.ok else 'FAILED'}] {r.name}: {r.detail}")
        all_ok = all_ok and r.ok
    raise SystemExit(0 if all_ok else 1)
