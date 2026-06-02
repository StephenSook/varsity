// Share the explanation, preferring the on-device audio clip, with graceful
// fallbacks: share the WAV file -> share the text -> download the WAV -> copy the
// text. navigator.share must run inside a user gesture (a button/key handler).

export type ShareResult = 'shared-clip' | 'shared-text' | 'downloaded' | 'copied' | 'cancelled' | 'unavailable'

const PREFIX = 'VARSITY explains the VAR call: '

type ShareNav = Navigator & {
  canShare?: (d: ShareData) => boolean
  share?: (d: ShareData) => Promise<void>
}

export async function shareExplanation(text: string, clip: Blob | null): Promise<ShareResult> {
  const nav = navigator as ShareNav

  if (clip && nav.canShare && nav.share) {
    const file = new File([clip], 'varsity-explanation.wav', { type: 'audio/wav' })
    if (nav.canShare({ files: [file] })) {
      try {
        await nav.share({ files: [file], title: 'VARSITY', text })
        return 'shared-clip'
      } catch (e) {
        if ((e as Error).name === 'AbortError') return 'cancelled'
      }
    }
  }

  if (nav.share) {
    try {
      await nav.share({ title: 'VARSITY', text: PREFIX + text })
      return 'shared-text'
    } catch (e) {
      if ((e as Error).name === 'AbortError') return 'cancelled'
    }
  }

  if (clip) {
    const url = URL.createObjectURL(clip)
    const a = document.createElement('a')
    a.href = url
    a.download = 'varsity-explanation.wav'
    a.click()
    URL.revokeObjectURL(url)
    return 'downloaded'
  }

  if (navigator.clipboard) {
    await navigator.clipboard.writeText(PREFIX + text)
    return 'copied'
  }
  return 'unavailable'
}
