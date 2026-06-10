import AxeBuilder from '@axe-core/playwright'
import { expect, test } from '@playwright/test'

// The what-if calibrator must move the line with REAL recomputation (the same yards
// formula as the backend geometry), be fully keyboard-operable, and never move the
// official call. Mocked SSE keeps it deterministic, like the a11y online-path test.

const geometry = {
  stage: 'geometry',
  players: [
    { x: 72.2, y: 30, teammate: true },
    { x: 50, y: 40, teammate: true, actor: true },
    { x: 65.98, y: 35, teammate: false },
    { x: 110, y: 40, teammate: false, keeper: true },
  ],
  offside_line_x: 65.98,
  attacker_x: 72.2,
  margin_meters: 5.69,
  is_offside: true,
  confidence: 'clear',
  pitch: { length: 120, width: 80 },
}
const verdict = {
  stage: 'verdict',
  text: 'The attacker was offside by 5.69 metres, grounded in Law 11.',
  is_offside: true,
  margin_meters: 5.69,
  confidence: 'clear',
  law: '11',
  law_text: 'Law 11',
}
const body =
  `event: geometry\ndata: ${JSON.stringify(geometry)}\n\n` +
  `event: verdict\ndata: ${JSON.stringify(verdict)}\n\n`

test('the calibrator recomputes the margin from the moved line, by keyboard, and resets', async ({
  page,
}) => {
  await page.route('**/stream/canned**', (route) =>
    route.fulfill({ status: 200, contentType: 'text/event-stream', body }),
  )
  // Reduced motion keeps the 2D SVG pitch mounted, where the dashed what-if line renders.
  await page.emulateMedia({ reducedMotion: 'reduce' })
  await page.goto('/')
  await page.locator('#explain-cta').click()

  const slider = page.getByRole('slider', { name: 'Defender line position' })
  await expect(slider).toBeVisible()
  const readout = page.getByTestId('whatif-readout')
  // untouched: the moved-line margin equals the real call, and no dashed line yet
  await expect(readout).toContainText('5.69')
  await expect(page.getByTestId('whatif-line')).toHaveCount(0)
  const reset = page.getByRole('button', { name: 'Back to the real line' })
  await expect(reset).toBeDisabled()

  // keyboard: arrow keys move the line, the margin recomputes, the real call stays anchored
  const before = (await readout.textContent()) ?? ''
  await slider.focus()
  for (let i = 0; i < 10; i++) await page.keyboard.press('ArrowRight')
  await expect(readout).not.toHaveText(before)
  await expect(readout).toContainText('5.69') // the official margin never moves
  // toHaveCount, not toBeVisible: a vertical SVG <line> has a zero-width bounding
  // box, which Playwright's visibility check reports as hidden even when painted.
  await expect(page.getByTestId('whatif-line')).toHaveCount(1)
  await expect(reset).toBeEnabled()

  // reset restores the real line
  await reset.click()
  await expect(page.getByTestId('whatif-line')).toHaveCount(0)
  await expect(reset).toBeDisabled()
  await expect(readout).toHaveText(before)
})

test('the calibrator panel has no serious or critical axe violations', async ({ page }) => {
  await page.route('**/stream/canned**', (route) =>
    route.fulfill({ status: 200, contentType: 'text/event-stream', body }),
  )
  await page.emulateMedia({ reducedMotion: 'reduce' })
  await page.goto('/')
  await page.locator('#explain-cta').click()
  await expect(page.getByTestId('whatif-panel')).toBeVisible()

  const results = await new AxeBuilder({ page })
    .include('[data-testid="whatif-panel"]')
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'])
    .analyze()
  const blocking = results.violations.filter(
    (v) => v.impact === 'serious' || v.impact === 'critical',
  )
  const summary = blocking.map((v) => ({ id: v.id, impact: v.impact, nodes: v.nodes.length }))
  expect(summary, JSON.stringify(summary, null, 2)).toEqual([])
})
