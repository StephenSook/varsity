"""Walton critical-questions surface for a received VAR/offside decision.

Frames the explanation as the answers to the critical questions a skeptic would raise about an
expert's ruling - Walton, Reed & Macagno's "Argument from Expert Opinion" scheme and its
critical questions (Argumentation Schemes, Cambridge University Press, 2008). VARSITY answers
the questions most relevant to an offside call, grounded in evidence it already has (the
geometry, the Law-11 proof, the camera-parallax note, the uncertainty band).

This DEFENDS the received decision's authority and points at the evidence; it never re-judges
the call. Answering "is the official an authority?" and "is there backing evidence?" is
explanation, not adjudication.
"""

from __future__ import annotations


def critical_questions(
    *, is_offside: bool, margin_meters: float, within_noise: bool = False, law: str = "11"
) -> dict:
    """The Argument-from-Expert-Opinion critical questions, answered for this offside call."""
    verdict = "offside" if is_offside else "onside"
    consistency = (
        "Viewing angle can deceive - see the camera-parallax note - so VARSITY uses the real "
        "tracked positions, not one broadcast angle."
    )
    if within_noise:
        consistency = (
            "This is a knife-edge call within the measurement noise, so VARSITY trusts the "
            "official's finer semi-automated tracking. " + consistency
        )
    return {
        "stage": "critical_questions",
        "scheme": "Argument from expert opinion (the match official)",
        "questions": [
            {
                "q": "What exactly did the official decide?",
                "a": f"{verdict.capitalize()} under Law {law}, "
                f"by a margin of {abs(margin_meters):.2f} m.",
            },
            {
                "q": "Is the official an authority on this call?",
                "a": "Yes: the on-field referee with the assistant referee and the VAR, using "
                "semi-automated offside technology with skeletal tracking finer than this "
                "single freeze-frame.",
            },
            {
                "q": "Is there backing evidence?",
                "a": "Yes: the freeze-frame geometry, the auditable Law-11 proof, and the "
                "official offside-line graphic.",
            },
            {
                "q": "Is the call consistent across viewing angles?",
                "a": consistency,
            },
        ],
    }
