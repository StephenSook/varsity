import { webgpuAvailable } from './offline'

// Read-aloud for the SIGHTED track only. The accessibility path stays the user's
// own screen reader (via the aria-live region); this is a supplementary spoken
// readout for sighted co-viewers. Two layers: a Web Speech API floor that always
// works, and a premium on-device Kokoro-82M voice (Transformers.js + WebGPU) when
// available. Never auto-plays; only on an explicit button press.

const KOKORO_MODEL = 'onnx-community/Kokoro-82M-v1.0-ONNX'
const KOKORO_VOICE = 'af_heart'

export function webSpeechAvailable(): boolean {
  return typeof window !== 'undefined' && 'speechSynthesis' in window
}

function speakWebSpeech(text: string, lang: string): boolean {
  if (!webSpeechAvailable()) return false
  const u = new SpeechSynthesisUtterance(text)
  u.lang = lang
  window.speechSynthesis.cancel()
  window.speechSynthesis.speak(u)
  return true
}

type KokoroAudio = { toBlob: () => Blob }
type KokoroModel = { generate: (text: string, opts: { voice: string }) => Promise<KokoroAudio> }
let _kokoro: KokoroModel | null = null

async function synthKokoro(text: string): Promise<Blob> {
  const { KokoroTTS } = await import('kokoro-js')
  if (!_kokoro) {
    _kokoro = (await KokoroTTS.from_pretrained(KOKORO_MODEL, {
      dtype: 'fp32',
      device: 'webgpu',
    })) as unknown as KokoroModel
  }
  const audio = await _kokoro.generate(text, { voice: KOKORO_VOICE })
  return audio.toBlob() // already an audio/wav Blob
}

async function speakKokoro(text: string): Promise<boolean> {
  const url = URL.createObjectURL(await synthKokoro(text))
  const el = new Audio(url)
  el.addEventListener('ended', () => URL.revokeObjectURL(url))
  await el.play()
  return true
}

/**
 * Render the explanation to a downloadable/shareable WAV clip with the on-device
 * Kokoro voice. Kokoro is English-first and WebGPU-only, so returns null when those
 * are unavailable (the caller then shares text instead). No network beyond the
 * lazy first-run model download.
 */
export async function synthesizeClip(
  text: string,
  opts: { lang?: string } = {},
): Promise<Blob | null> {
  const lang = opts.lang ?? 'en'
  if (!lang.startsWith('en') || !webgpuAvailable()) return null
  try {
    return await synthKokoro(text)
  } catch {
    return null
  }
}

export type ReadAloudResult = 'kokoro' | 'web-speech' | 'unavailable'

/**
 * Speak the explanation aloud for sighted viewers. Tries the premium on-device
 * Kokoro voice (WebGPU only), falling back to the Web Speech API floor. Kokoro is
 * English-first, so non-English text uses the Web Speech floor (which has the right
 * voice per the BCP-47 lang).
 */
export async function readAloud(
  text: string,
  opts: { lang?: string; preferKokoro?: boolean; onStatus?: (s: string) => void } = {},
): Promise<ReadAloudResult> {
  const lang = opts.lang ?? 'en'
  const wantKokoro = (opts.preferKokoro ?? true) && lang.startsWith('en') && webgpuAvailable()
  if (wantKokoro) {
    try {
      opts.onStatus?.('Loading Kokoro voice on-device (first run downloads the model)...')
      await speakKokoro(text)
      opts.onStatus?.('Reading aloud with Kokoro-82M (on-device).')
      return 'kokoro'
    } catch {
      // fall through to the Web Speech floor
    }
  }
  if (speakWebSpeech(text, lang)) {
    opts.onStatus?.('Reading aloud (system voice).')
    return 'web-speech'
  }
  opts.onStatus?.('Read-aloud is unavailable in this browser.')
  return 'unavailable'
}

export function stopReading(): void {
  if (webSpeechAvailable()) window.speechSynthesis.cancel()
}

/**
 * Spearcon: time-compressed speech of a rule fragment (Walker, Nance & Lindsay, ICAD 2006;
 * Walker et al., Human Factors 2013, where spearcons outperform earcons on navigation accuracy).
 * A fast audible shortcut a power screen-reader user can learn and recognise by ear. Web Speech
 * `rate` (capped here) is an assets-free approximation of the pitch-corrected spearcon technique;
 * the full explanation still goes to the user's own screen reader. User-triggered only.
 */
export function playSpearcon(text: string, opts: { lang?: string; rate?: number } = {}): boolean {
  if (!webSpeechAvailable()) return false
  const u = new SpeechSynthesisUtterance(text)
  u.lang = opts.lang ?? 'en'
  u.rate = Math.min(opts.rate ?? 3.5, 5)
  window.speechSynthesis.cancel()
  window.speechSynthesis.speak(u)
  return true
}
