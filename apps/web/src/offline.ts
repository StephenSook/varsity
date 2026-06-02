import type { Geometry, Player } from './OffsidePitch'

// Airplane mode: generate a Law-grounded offside explanation FULLY in-browser, with
// the network cut. Geometry and the Law text are bundled here, and the explanation
// is phrased on-device by IBM Granite 4.0 Nano (350M) via Transformers.js + WebGPU
// when available, falling back to a deterministic Law-grounded floor otherwise. No
// backend, no network: the same deterministic-floor philosophy as the server path.

const UNITS_TO_METERS = 105 / 120

// IBM Granite 4.0 Nano, ONNX-web build (Transformers.js + WebGPU ready).
const GRANITE_NANO = 'onnx-community/granite-4.0-350m-ONNX-web'

// Exact IFAB Law 11 wording, bundled so offline mode needs zero network.
export const LAW_11_TEXT =
  "Law 11 - Offside. A player is in an offside position if any part of the head, body " +
  "or feet is in the opponents' half (excluding the halfway line) and nearer to the " +
  "opponents' goal line than both the ball and the second-last opponent. Being in an " +
  "offside position is only an offence if, at the moment the ball is played by a " +
  'team-mate, the player becomes involved in active play.'

// A bundled canned World-Cup-style offside frame (so offline needs no fixture fetch).
const CANNED_FRAME: Player[] = [
  { x: 30.9, y: 59.0, teammate: true, actor: true },
  { x: 72.2, y: 77.9, teammate: true },
  { x: 57.4, y: 63.1, teammate: true },
  { x: 62.7, y: 23.4, teammate: true },
  { x: 65.98, y: 29.7, teammate: false },
  { x: 70.86, y: 74.9, teammate: false, keeper: true },
  { x: 48.2, y: 48.4, teammate: false },
  { x: 55.7, y: 46.8, teammate: false },
]

function secondLastOpponentX(frame: Player[]): number {
  const xs = frame
    .filter((p) => !p.teammate)
    .map((p) => p.x)
    .sort((a, b) => b - a)
  return xs[1]
}

function mostAdvancedAttackerX(frame: Player[]): number {
  const nonActor = frame.filter((p) => p.teammate && !p.actor)
  const pool = nonActor.length ? nonActor : frame.filter((p) => p.teammate)
  return Math.max(...pool.map((p) => p.x))
}

export function computeOffsideLocal(frame: Player[] = CANNED_FRAME): Geometry {
  const lineX = secondLastOpponentX(frame)
  const attX = mostAdvancedAttackerX(frame)
  const marginUnits = attX - lineX
  return {
    players: frame,
    offside_line_x: lineX,
    attacker_x: attX,
    margin_meters: Math.round(marginUnits * UNITS_TO_METERS * 100) / 100,
    is_offside: marginUnits > 0,
    pitch: { length: 120, width: 80 },
  }
}

export function deterministicExplanation(geo: Geometry): string {
  const m = Math.abs(geo.margin_meters).toFixed(2)
  if (geo.is_offside) {
    return (
      `Under Law 11, the most advanced attacker was ahead of the second-to-last ` +
      `defender by ${m} meters when the ball was played, so the player was correctly ` +
      `judged offside.`
    )
  }
  return (
    `Under Law 11, the most advanced attacker was level with or behind the ` +
    `second-to-last defender by ${m} meters, so the position was legal.`
  )
}

export function webgpuAvailable(): boolean {
  return typeof navigator !== 'undefined' && (navigator as { gpu?: unknown }).gpu != null
}

type Generator = (
  messages: unknown,
  opts: unknown,
) => Promise<Array<{ generated_text: Array<{ content: string }> }>>

let _generator: Generator | null = null

export type OfflineResult = {
  text: string
  source: 'granite-nano-webgpu' | 'deterministic'
  geo: Geometry
}

/**
 * Produce a Law-grounded explanation entirely on-device. Tries Granite Nano on
 * WebGPU, then falls back to the deterministic floor. Never touches the network
 * except to lazily download the model weights on first WebGPU run.
 */
export async function generateOffline(
  opts: { frame?: Player[]; onStatus?: (s: string) => void } = {},
): Promise<OfflineResult> {
  const geo = computeOffsideLocal(opts.frame)
  const floor = deterministicExplanation(geo)

  if (!webgpuAvailable()) {
    opts.onStatus?.('WebGPU unavailable; explained on-device (deterministic).')
    return { text: floor, source: 'deterministic', geo }
  }

  try {
    opts.onStatus?.('Loading Granite Nano on-device (first run downloads the model)...')
    const { pipeline } = await import('@huggingface/transformers')
    if (!_generator) {
      _generator = (await pipeline('text-generation', GRANITE_NANO, {
        dtype: 'q4',
        device: 'webgpu',
      })) as unknown as Generator
    }
    const messages = [
      {
        role: 'system',
        content:
          'You explain a soccer VAR offside decision to a blind fan in two short ' +
          'sentences, grounded in the Law text, citing the Law number. Do not invent rules.',
      },
      {
        role: 'user',
        content:
          `Law text: ${LAW_11_TEXT}\n\nDecision: the most advanced attacker was ` +
          `${Math.abs(geo.margin_meters).toFixed(2)} meters ` +
          `${geo.is_offside ? 'ahead of' : 'behind'} the second-to-last defender when ` +
          `the ball was played. Verdict: ${geo.is_offside ? 'offside' : 'onside'}. Explain why.`,
      },
    ]
    const out = await _generator(messages, { max_new_tokens: 120, do_sample: false })
    const text = out?.[0]?.generated_text?.at(-1)?.content?.trim()
    if (text && text.length >= 20 && /law/i.test(text)) {
      opts.onStatus?.('Generated on-device with Granite Nano (WebGPU).')
      return { text, source: 'granite-nano-webgpu', geo }
    }
    return { text: floor, source: 'deterministic', geo }
  } catch {
    opts.onStatus?.('On-device model unavailable; explained on-device (deterministic).')
    return { text: floor, source: 'deterministic', geo }
  }
}
