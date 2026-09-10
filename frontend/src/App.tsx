import { useRef, useState } from 'react'
import { useVoiceAssistant } from './features/assistant/hooks/useVoiceAssistant'

interface SpeechRecognitionResultLike {
  isFinal: boolean
  [index: number]: {
    transcript: string
  }
}

interface SpeechRecognitionEventLike {
  resultIndex: number
  results: {
    length: number
    [index: number]: SpeechRecognitionResultLike
  }
}

interface SpeechRecognitionLike {
  continuous: boolean
  interimResults: boolean
  lang: string
  onresult: ((event: SpeechRecognitionEventLike) => void) | null
  onerror: (() => void) | null
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

function App() {
  const {
    state,
    response,
    error,
    startListening,
    stopListening,
  } = useVoiceAssistant()

  const [liveTranscript, setLiveTranscript] = useState('')
  const [speechError, setSpeechError] = useState<string | null>(null)

  const recognitionRef = useRef<SpeechRecognitionLike | null>(null)
  const finalTranscriptRef = useRef('')

  const isListening = state === 'LISTENING'

  function startLiveTranscription() {
    const speechWindow = window as SpeechWindow
    const SpeechRecognition =
      speechWindow.SpeechRecognition ??
      speechWindow.webkitSpeechRecognition

    if (!SpeechRecognition) {
      setSpeechError(
        'Live transcription is not supported in this browser. Try Chrome or Edge.',
      )
      return
    }

    setSpeechError(null)
    setLiveTranscript('')
    finalTranscriptRef.current = ''

    const recognition = new SpeechRecognition()

    recognition.continuous = true
    recognition.interimResults = true
    recognition.lang = 'en-US'

    recognition.onresult = (event) => {
      let interimTranscript = ''

      for (
        let index = event.resultIndex;
        index < event.results.length;
        index += 1
      ) {
        const result = event.results[index]
        const transcript = result[0].transcript

        if (result.isFinal) {
          finalTranscriptRef.current += transcript
        } else {
          interimTranscript += transcript
        }
      }

      setLiveTranscript(
        `${finalTranscriptRef.current} ${interimTranscript}`.trim(),
      )
    }

    recognition.onerror = () => {
      setSpeechError('Live transcription failed.')
    }

    recognitionRef.current = recognition
    recognition.start()
  }

  function stopLiveTranscription() {
    recognitionRef.current?.stop()
    recognitionRef.current = null
  }

  async function handleMicrophoneClick() {
    if (isListening) {
      stopLiveTranscription()
      stopListening()
      return
    }

    try {
      await startListening()
      startLiveTranscription()
    } catch (requestError) {
      setSpeechError(
        requestError instanceof Error
          ? requestError.message
          : 'Unable to access the microphone.',
      )
    }
  }

  return (
    <main>
      <h1>Suzanne</h1>

      <button
        type="button"
        onClick={() => void handleMicrophoneClick()}
        disabled={state === 'PROCESSING' || state === 'SPEAKING'}
      >
        {isListening ? 'Stop listening' : 'Start listening'}
      </button>

      <p>Assistant state: {state}</p>

      {isListening && (
        <section aria-live="polite">
          <h2>What I hear</h2>
          <p>{liveTranscript || 'Start speaking...'}</p>
        </section>
      )}

      {response && (
        <section aria-live="polite">
          <h2>Final transcript</h2>
          <p>{response.transcript}</p>

          <h2>Intent</h2>
          <p>Destination: {response.intent.destination}</p>
          <p>Priority: {response.intent.priority}</p>

          <h2>Suzanne</h2>
          <p>{response.spokenResponse}</p>
        </section>
      )}

      {speechError && (
        <p role="alert">
          {speechError}
        </p>
      )}

      {error && (
        <p role="alert">
          {error}
        </p>
      )}
    </main>
  )
}

export default App