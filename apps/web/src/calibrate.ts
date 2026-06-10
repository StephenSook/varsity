// Pure helpers for the what-if offside-line calibrator. The constant and the margin
// formula MIRROR services/app/geometry.py: StatsBomb's 120 x 80 grid is in YARDS, so a
// grid-unit margin converts with the international yard (1 yd = 0.9144 m), never by
// assuming the 120-unit length spans a 105 m pitch. A unit test pins parity with the
// backend's canned WC2022 value so the two formulas cannot drift silently.
export const METERS_PER_UNIT = 0.9144

export function clampLineX(x: number, pitchLength: number): number {
  return Math.min(Math.max(x, 0), pitchLength)
}

/**
 * Signed metres from the moved defender line to the attacker, along the goal-line normal.
 * Positive = the attacker is ahead of the moved line (the offside side). This is a
 * what-if against the MOVED LINE only; the official call (which can bind to the ball
 * under Law 11) is computed by the backend and never changes here.
 */
export function whatIfMarginMeters(attackerX: number, lineX: number): number {
  return Math.round((attackerX - lineX) * METERS_PER_UNIT * 100) / 100
}
