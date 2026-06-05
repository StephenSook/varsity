import { retrieveLawOffline } from './inBrowserRag'
import type { Geometry, Player } from './OffsidePitch'

// The offside scenario the offline path explains; used to retrieve the governing Law
// from the in-browser IFAB index (mirrors the backend's offside query).
const OFFSIDE_QUERY =
  'offside attacker nearer the goal line than the second-last defender and the ball'

// Airplane mode: generate a Law-grounded offside explanation FULLY in-browser, with
// the network cut. Geometry and the Law text are bundled here, and the explanation
// is phrased on-device by IBM Granite 4.0 Nano (350M) via Transformers.js + WebGPU
// when available, falling back to a deterministic Law-grounded floor otherwise. No
// backend, no network: the same deterministic-floor philosophy as the server path.

// StatsBomb's 120x80 grid is in YARDS; convert with the international yard, matching
// services/app/geometry.py (METERS_PER_UNIT = 0.9144), Demo.tsx, and sonify.ts. The old
// 105/120 (= 0.875) under-states every margin ~4.3% and was the audit-fixed bug; the
// offline spoken margin must stay consistent with the online geometry and its own sonification.
const UNITS_TO_METERS = 0.9144

// IBM Granite 4.0 Nano, ONNX-web build (Transformers.js + WebGPU ready).
// A 3-tier on-device ladder, all IBM Granite + Apache-2.0: the deterministic floor, the
// light Granite Nano 350M default (~0.3 GB), and an OPT-IN high-accuracy Granite 4.0 1B
// (~1.5 GB q4; the model IBM itself ships in its Granite-4.0-Nano-WebGPU Space). The 1B is
// off by default - it is a deliberate, gated download, never forced on the demo path.
const GRANITE_NANO = 'onnx-community/granite-4.0-350m-ONNX-web'
const GRANITE_1B = 'onnx-community/granite-4.0-1b-ONNX-web'

export type OfflineTier = 'nano' | 'granite-1b'
const _MODELS: Record<OfflineTier, string> = { nano: GRANITE_NANO, 'granite-1b': GRANITE_1B }
let _tier: OfflineTier = 'nano'

/** Opt into the high-accuracy on-device tier (a ~1.5 GB one-time download). */
export function setOfflineTier(tier: OfflineTier): void {
  _tier = tier
}
export function getOfflineTier(): OfflineTier {
  return _tier
}

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

function confidenceLabel(marginMeters: number): string {
  const m = Math.abs(marginMeters)
  if (m >= 0.5) return 'clear'
  if (m >= 0.2) return 'tight'
  return 'very tight'
}

export function computeOffsideLocal(frame: Player[] = CANNED_FRAME): Geometry {
  const lineX = secondLastOpponentX(frame)
  const attX = mostAdvancedAttackerX(frame)
  const marginUnits = attX - lineX
  const margin = Math.round(marginUnits * UNITS_TO_METERS * 100) / 100
  return {
    players: frame,
    offside_line_x: lineX,
    attacker_x: attX,
    margin_meters: margin,
    is_offside: marginUnits > 0,
    confidence: confidenceLabel(margin),
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

/**
 * A stronger WebGPU check than `navigator.gpu != null`: confirms an adapter can
 * actually be acquired (navigator.gpu can exist while requestAdapter() returns null,
 * e.g. blocklisted GPUs), so we never start a doomed model download. Transformers.js
 * exposes no "did it really use the GPU" signal, so we verify the adapter ourselves.
 */
export async function webgpuReady(): Promise<boolean> {
  const gpu = (navigator as { gpu?: { requestAdapter?: () => Promise<unknown> } }).gpu
  if (!gpu?.requestAdapter) return false
  try {
    return (await gpu.requestAdapter()) != null
  } catch {
    return false
  }
}

type Generator = (
  messages: unknown,
  opts: unknown,
) => Promise<Array<{ generated_text: Array<{ content: string }> }>>

const _generators: Partial<Record<OfflineTier, Generator>> = {}

export type OfflineResult = {
  text: string
  source: 'granite-nano-webgpu' | 'granite-1b-webgpu' | 'deterministic'
  geo: Geometry
  lawText: string
  retrieval: 'orama-bm25' | 'bundled'
}

/**
 * Produce a Law-grounded explanation entirely on-device. First retrieves the governing
 * Law from the in-browser IFAB index (Orama BM25), then tries Granite Nano on WebGPU,
 * falling back to the deterministic floor. The only network is the one-time fetch of
 * the static index and (on first WebGPU run) the model weights, both service-worker
 * cached for true airplane-mode use.
 */
export async function generateOffline(
  opts: { frame?: Player[]; onStatus?: (s: string) => void } = {},
): Promise<OfflineResult> {
  const geo = computeOffsideLocal(opts.frame)
  const floor = deterministicExplanation(geo)

  // Retrieve the Law on-device; fall back to the bundled Law 11 text if the index
  // is not reachable (e.g. cold airplane mode before the service worker cached it).
  const chunk = await retrieveLawOffline(OFFSIDE_QUERY).catch(() => null)
  const lawText = chunk?.text ?? LAW_11_TEXT
  const retrieval: OfflineResult['retrieval'] = chunk ? 'orama-bm25' : 'bundled'

  if (!(await webgpuReady())) {
    opts.onStatus?.('WebGPU unavailable; explained on-device (deterministic).')
    return { text: floor, source: 'deterministic', geo, lawText, retrieval }
  }

  const tier = _tier
  const sourceTag: OfflineResult['source'] =
    tier === 'granite-1b' ? 'granite-1b-webgpu' : 'granite-nano-webgpu'
  try {
    opts.onStatus?.(
      tier === 'granite-1b'
        ? 'Loading Granite 4.0 1B on-device (first run downloads ~1.5 GB)...'
        : 'Loading Granite Nano on-device (first run downloads the model)...',
    )
    const { pipeline } = await import('@huggingface/transformers')
    if (!_generators[tier]) {
      _generators[tier] = (await pipeline('text-generation', _MODELS[tier], {
        dtype: 'q4',
        device: 'webgpu',
      })) as unknown as Generator
    }
    const _generator = _generators[tier]!
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
          `Law text: ${lawText.slice(0, 1200)}\n\nDecision: the most advanced attacker was ` +
          `${Math.abs(geo.margin_meters).toFixed(2)} meters ` +
          `${geo.is_offside ? 'ahead of' : 'behind'} the second-to-last defender when ` +
          `the ball was played. Verdict: ${geo.is_offside ? 'offside' : 'onside'}. Explain why.`,
      },
    ]
    const out = await _generator(messages, { max_new_tokens: 120, do_sample: false })
    const text = out?.[0]?.generated_text?.at(-1)?.content?.trim()
    if (text && text.length >= 20 && /law/i.test(text)) {
      opts.onStatus?.(
        tier === 'granite-1b'
          ? 'Generated on-device with Granite 4.0 1B (WebGPU).'
          : 'Generated on-device with Granite Nano (WebGPU).',
      )
      return { text, source: sourceTag, geo, lawText, retrieval }
    }
    return { text: floor, source: 'deterministic', geo, lawText, retrieval }
  } catch {
    opts.onStatus?.('On-device model unavailable; explained on-device (deterministic).')
    return { text: floor, source: 'deterministic', geo, lawText, retrieval }
  }
}
