# The Law-11 proof as a structured argument (ASPIC+ / Dung)

This is a design note. It documents *why* VARSITY's Law-11 explanation has the shape it does, by
mapping the engine in `services/app/law11.py` onto the standard model of structured argumentation.
The engine itself stays a small, auditable, pure-Python forward-chaining reasoner (no external
solver to fail on deploy); this note records the formal correspondence so the rigour is legible
without paying the integration cost of a running argumentation solver.

## Why argumentation is the right frame

Fans and pundits explain offside argumentatively: *"it looked offside, BUT the defender
deliberately played it, SO it's onside."* That is precisely a defeasible argument with attacks.
Dung's abstract argumentation framework (Dung, *Artificial Intelligence* 77(2):321-358, 1995)
models a debate as arguments plus an attack relation and identifies the surviving (justified)
arguments. ASPIC+ (Modgil & Prakken, *Argument and Computation* 5(1):31-62, 2014) builds those
arguments from strict and defeasible rules and classifies attacks as **undermining** (a premise),
**rebutting** (a conclusion), or **undercutting** (a defeasible inference step). Diller, Gaggl,
Hanisch, Monterosso & Rauschenbach (KR 2025) show ASPIC+ can be compiled to Datalog/ASP, so the
framing is executable in principle.

## The correspondence

VARSITY's offside decision is one defeasible argument with checked-and-dismissed attackers:

| Argument | Content | Role | Engine site |
|---|---|---|---|
| **A1** (pro-offence) | in an offside position AND involved in active play => offside offence | defeasible conclusion | `law11.prove` head |
| **A2** (level) | level with the second-to-last opponent => not an offside position | **rebuts** A1's premise | `position.beyond_defender` step |
| **A3** (deliberate play) | a defender deliberately played the ball => the phase resets | **undercuts** A1's inference | Law 11.3 (clarification) |
| **A4** (restart) | the ball came from a goal kick / throw-in / corner => no offence | **undercuts** A1's inference | the three `defeater.*` steps |

The engine's proof tree *is* the surviving argument: each premise step (Law 11.1 / 11.2) is a
sub-argument of A1, and each Law 11.3 defeater is an attacker that is explicitly checked and, for
open play, dismissed (`status = "n/a"`). When A1 survives all attacks the conclusion is "offside";
when A2 succeeds the conclusion is "onside". The grounded extension of this tiny framework is what
VARSITY narrates.

## Non-adjudication, stated argumentatively

A1 is **defeasible**, never strict. When the engine's own derivation disagrees with the official's
decision (a knife-edge call a single freeze-frame point cannot resolve), VARSITY does not push its
argument through: it defers to the official, who has finer semi-automated skeletal tracking. In
ASPIC+ terms the official's decision is a strict premise that VARSITY never rebuts. That is the
coded non-adjudication property, expressed in the language of argumentation.

## What we deliberately did not build

A runnable ASPIC+/Dung solver (ASPARTIX, ASPforASPIC) would add a heavy dependency for no extra
explanatory power here: the proof tree already yields the surviving argument. Per the
neuro-symbolic verification report, we model argumentatively in this note, execute via the
pure-Python engine, and document the equivalence.
