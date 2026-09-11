export interface SpeechRecognitionResultLike {
  isFinal: boolean
  [index: number]: { transcript: string }
}

export interface SpeechRecognitionEventLike {
  resultIndex: number
  results: {
    length: number
    [index: number]: SpeechRecognitionResultLike
  }
}

export interface SpeechRecognitionLike {
  continuous: boolean
  interimResults: boolean
  lang: string
  onresult: ((event: SpeechRecognitionEventLike) => void) | null
  onerror: (() => void) | null
  onend: (() => void) | null
  start: () => void
  stop: () => void
}

interface SpeechRecognitionConstructor {
  new (): SpeechRecognitionLike
}

type SpeechWindow = Window & {
  SpeechRecognition?: SpeechRecognitionConstructor
  webkitSpeechRecognition?: SpeechRecognitionConstructor
}

export function getSpeechRecognitionConstructor() {
  const speechWindow = window as SpeechWindow
  return speechWindow.SpeechRecognition ?? speechWindow.webkitSpeechRecognition
}

export function normalizeSpeech(text: string) {
  return text
    .toLowerCase()
    .replace(/[^\p{L}\s]/gu, '')
    .replace(/\s+/g, ' ')
    .trim()
}

export function containsWakeWord(text: string) {
  const normalizedText = normalizeSpeech(text)
  return (
    normalizedText.includes('hey suzanne') ||
    normalizedText.includes('hey susanne')
  )
}

export function playAudioFile(path: string): Promise<void> {
  return new Promise((resolve) => {
    const audio = new Audio(path)
    audio.onended = () => resolve()
    audio.onerror = () => resolve()
    void audio.play().catch(() => resolve())
  })
}
