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

async function speakKokoro(text: string): Promise<boolean> {
  const { KokoroTTS } = await import('kokoro-js')
  if (!_kokoro) {
    _kokoro = (await KokoroTTS.from_pretrained(KOKORO_MODEL, {
      dtype: 'fp32',
      device: 'webgpu',
    })) as unknown as KokoroModel
  }
  const audio = await _kokoro.generate(text, { voice: KOKORO_VOICE })
  const url = URL.createObjectURL(audio.toBlob())
  const el = new Audio(url)
  el.addEventListener('ended', () => URL.revokeObjectURL(url))
  await el.play()
  return true
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
