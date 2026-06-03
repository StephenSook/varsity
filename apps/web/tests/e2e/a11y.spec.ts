import AxeBuilder from '@axe-core/playwright'
import { expect, test } from '@playwright/test'

// VARSITY's whole premise is that a screen-reader user gets the explanation, so the
// accessibility contract is a first-class CI gate, not an afterthought. These run on
// the production preview build.

test('no serious or critical axe violations (reduced motion)', async ({ page }) => {
  // Reduced motion is the deterministic path: the decorative 3D canvas is not
  // mounted, so axe scans the real semantic layer.
  await page.emulateMedia({ reducedMotion: 'reduce' })
  await page.goto('/')
  await page.getByRole('heading', { level: 1, name: 'VARSITY' }).waitFor()

  const results = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
    .analyze()
  const blocking = results.violations.filter(
    (v) => v.impact === 'serious' || v.impact === 'critical',
  )
  const summary = blocking.map((v) => ({ id: v.id, impact: v.impact, nodes: v.nodes.length }))
  expect(summary, JSON.stringify(summary, null, 2)).toEqual([])
})

test('the aria-live verdict region is pre-registered and empty on load', async ({ page }) => {
  // The region must exist BEFORE the verdict so a screen reader announces the
  // in-place text change. If it were created on demand, the announcement is lost.
  await page.goto('/')
  const live = page.locator('[aria-live="assertive"]')
  await expect(live).toHaveAttribute('role', 'status')
  await expect(live).toHaveAttribute('aria-atomic', 'true')
  await expect(live).toHaveText('')
})

test('single h1 and the cinematic sections render with the demo reachable', async ({ page }) => {
  await page.goto('/')
  await expect(page.locator('h1')).toHaveCount(1)
  for (const id of ['problem', 'demo', 'pipeline', 'judges']) {
    await expect(page.locator(`section#${id}`)).toBeVisible()
  }
  await expect(page.getByRole('button', { name: 'Explain the call' })).toBeVisible()
})

test('the scenario picker exposes the three real World Cup frames (offside default)', async ({
  page,
}) => {
  await page.goto('/')
  const group = page.getByRole('group', { name: /Decision scenario/ })
  await expect(group.getByRole('button', { name: 'Offside scenario' })).toHaveAttribute(
    'aria-pressed',
    'true',
  )
  for (const label of [
    'Offside scenario',
    'Onside scenario',
    'Tight call scenario',
    'Penalty scenario',
    'Handball scenario',
  ]) {
    await expect(group.getByRole('button', { name: label })).toBeVisible()
  }
})

test('the ask-any-rule oracle exposes a labelled question input and Ask button', async ({
  page,
}) => {
  await page.goto('/')
  const form = page.getByRole('form', { name: 'Ask the Laws of the Game' })
  await expect(
    form.getByRole('textbox', { name: 'Ask any question about the Laws of the Game' }),
  ).toBeVisible()
  await expect(form.getByRole('button', { name: 'Ask', exact: true })).toBeDisabled()
})

test('the /judges surface shows verifiability tiers and live run buttons', async ({ page }) => {
  await page.goto('/')
  const judges = page.locator('section#judges')
  await expect(judges.getByText('LIVE', { exact: true }).first()).toBeVisible()
  await expect(judges.getByRole('button', { name: 'Run the geometry engine' })).toBeVisible()
})

test('the decorative 3D canvas, when present, is aria-hidden', async ({ page }) => {
  await page.goto('/')
  const canvas = page.locator('canvas')
  if (await canvas.count()) {
    await expect(page.locator('[aria-hidden="true"] canvas').first()).toBeVisible()
  }
})

test('the ? keyboard shortcut toggles the shortcut help (keyboard power mode is wired)', async ({
  page,
}) => {
  await page.goto('/')
  const help = page.locator('section[aria-label="Keyboard shortcuts"]')
  await expect(help).toHaveCount(0)
  await page.keyboard.press('?')
  await expect(help).toBeVisible()
  // the help lists the core single-key actions (scoped to the help panel)
  await expect(help.getByText('Explain the call')).toBeVisible()
})
