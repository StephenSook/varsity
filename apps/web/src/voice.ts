// On-device voice input for the rule oracle: the fan speaks a question in their language, it is
// transcribed ENTIRELY in the browser (no audio leaves the device), and the transcript feeds the
// existing oracle (retrieve -> Granite -> Guardian -> spoken answer in their language). This is the
// premium tier; the Web Speech API in Demo.tsx is the zero-download floor.
//
// Model choice (feasibility-verified). The on-device default is Whisper-base (multilingual, ~150MB,
// the one confirmed practically-sized in-browser ASR in Transformers.js + WebGPU). IBM Granite
// Speech (onnx-community/granite-speech-4.1-2b-ONNX) DOES run on-device in the browser via
// Transformers.js (the GraniteSpeechForConditionalGeneration generate() path + WebGPU, demonstrated
// in a community Space), but it is ~1.5GB+ with no official ASR pipeline, so it is the honest
// opt-in / experimental ALL-IBM on-device path, not the default. The rule ANSWER is already
// all-IBM (Granite + Guardian, fully on-device via Granite Nano). See docs/VOICE.md.

import { webgpuReady } from './offline'

// The on-device ASR model: Whisper-base (multilingual, runs in Transformers.js with WebGPU). To run
// the all-IBM Granite Speech path instead, swap to GraniteSpeechForConditionalGeneration with
// onnx-community/granite-speech-4.1-2b-ONNX (a ~1.5GB+ opt-in, not the practical default).
const MODEL = 'onnx-community/whisper-base'

// Map our BCP-47 narration codes to the recognizer's language name.
const _ASR_LANG: Record<string, string> = {
  en: 'english',
  es: 'spanish',
  fr: 'french',
  pt: 'portuguese',
  de: 'german',
}

export function recognitionLang(bcp47: string): string {
  const key = bcp47.slice(0, 2).toLowerCase()
  return _ASR_LANG[key] ?? 'english'
}

export async function onDeviceAsrAvailable(): Promise<boolean> {
  return (
    typeof navigator !== 'undefined' &&
    !!navigator.mediaDevices?.getUserMedia &&
    typeof MediaRecorder !== 'undefined' &&
    (await webgpuReady())
  )
}

// Record from the microphone until stop() is called or maxMs elapses; resolves to the audio blob.
function recordAudio(maxMs: number, onReady?: () => void): { done: Promise<Blob>; stop: () => void } {
  let stop = () => {}
  const done = (async () => {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    const rec = new MediaRecorder(stream)
    const chunks: Blob[] = []
    rec.ondataavailable = (e) => {
      if (e.data.size) chunks.push(e.data)
    }
    return await new Promise<Blob>((resolve, reject) => {
      const finish = () => stream.getTracks().forEach((track) => track.stop())
      rec.onstop = () => {
        finish()
        resolve(new Blob(chunks, { type: rec.mimeType || 'audio/webm' }))
      }
      rec.onerror = (e) => {
        finish()
        reject(e)
      }
      rec.start()
      onReady?.()
      stop = () => rec.state !== 'inactive' && rec.stop()
      window.setTimeout(stop, maxMs)
    })
  })()
  return { done, stop: () => stop() }
}

// Decode any recorded audio to the mono 16 kHz Float32 the ASR model expects.
async function decodeToMono16k(blob: Blob): Promise<Float32Array> {
  const buf = await blob.arrayBuffer()
  const ac = new AudioContext()
  const decoded = await ac.decodeAudioData(buf)
  void ac.close()
  const TARGET = 16000
  if (decoded.numberOfChannels === 1 && decoded.sampleRate === TARGET) {
    return decoded.getChannelData(0)
  }
  const off = new OfflineAudioContext(1, Math.ceil(decoded.duration * TARGET), TARGET)
  const src = off.createBufferSource()
  src.buffer = decoded
  src.connect(off.destination)
  src.start()
  const rendered = await off.startRendering()
  return rendered.getChannelData(0)
}

let _asr: ((audio: Float32Array, opts: unknown) => Promise<{ text?: string }>) | null = null

/** Record a question and transcribe it fully on-device. Returns a controller so the UI can stop
 *  recording early, plus a promise resolving to the transcript. */
export function listen(
  bcp47: string,
  opts: { maxMs?: number; onStatus?: (s: string) => void } = {},
): { transcript: Promise<string>; stop: () => void } {
  const onStatus = opts.onStatus
  const rec = recordAudio(opts.maxMs ?? 6000, () => onStatus?.('Listening...'))
  const transcript = (async () => {
    const blob = await rec.done
    onStatus?.('Transcribing on-device...')
    const audio = await decodeToMono16k(blob)
    const { pipeline } = await import('@huggingface/transformers')
    if (!_asr) {
      _asr = (await pipeline('automatic-speech-recognition', MODEL, {
        dtype: 'q4',
        device: 'webgpu',
      })) as unknown as typeof _asr
    }
    const out = await _asr!(audio, { language: recognitionLang(bcp47), task: 'transcribe' })
    return (out.text ?? '').trim()
  })()
  return { transcript, stop: rec.stop }
}
