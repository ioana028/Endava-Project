import { useCallback, useEffect, useRef, useState } from 'react'
import type { AssistantState } from './useVoiceAssistant'
import {
  containsWakeWord,
  getSpeechRecognitionConstructor,
  playAudioFile,
  type SpeechRecognitionLike,
} from '../utils/speechRecognition'

interface UseWakeWordOptions {
  state: AssistantState
  startListening: () => Promise<void>
  stopListening: () => void
}

export function useWakeWord({
  state,
  startListening,
  stopListening,
}: UseWakeWordOptions) {
  const [enabled, setEnabled] = useState(false)
  const [transcript, setTranscript] = useState('')
  const [error, setError] = useState<string | null>(null)

  const recognitionRef = useRef<SpeechRecognitionLike | null>(null)
  const modeRef = useRef<'WAKE' | 'COMMAND' | null>(null)
  const silenceTimerRef = useRef<number | null>(null)
  const enabledRef = useRef(false)
  const wakeHandledRef = useRef(false)
  const finalTranscriptRef = useRef('')
  const startWakeRef = useRef<() => void>(() => undefined)
  const callbacksRef = useRef({ startListening, stopListening })

  const clearSilenceTimer = useCallback(() => {
    if (silenceTimerRef.current !== null) {
      window.clearTimeout(silenceTimerRef.current)
      silenceTimerRef.current = null
    }
  }, [])

  const stopRecognition = useCallback(() => {
    clearSilenceTimer()
    modeRef.current = null
    recognitionRef.current?.stop()
    recognitionRef.current = null
  }, [clearSilenceTimer])

  const startCommandRecognition = useCallback(() => {
    const SpeechRecognition = getSpeechRecognitionConstructor()

    if (!SpeechRecognition) {
      setError('Voice commands are not supported in this browser.')
      return
    }

    const recognition = new SpeechRecognition()
    modeRef.current = 'COMMAND'
    finalTranscriptRef.current = ''
    setTranscript('')
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
        if (result.isFinal) {
          finalTranscriptRef.current += result[0].transcript
        } else {
          interimTranscript += result[0].transcript
        }
      }

      setTranscript(
        `${finalTranscriptRef.current} ${interimTranscript}`.trim(),
      )
      clearSilenceTimer()
      silenceTimerRef.current = window.setTimeout(() => {
        stopRecognition()
        callbacksRef.current.stopListening()
      }, 1000)
    }

    recognition.onerror = () => {
      if (modeRef.current === 'COMMAND') {
        setError('Voice recognition failed.')
      }
    }

    recognitionRef.current = recognition
    recognition.start()
  }, [clearSilenceTimer, stopRecognition])

  const handleWakeWord = useCallback(async () => {
    stopRecognition()
    setError(null)
    await playAudioFile('/audio/listening-jingle.mp3')

    try {
      await callbacksRef.current.startListening()
      startCommandRecognition()
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : 'Unable to access the microphone.',
      )
      wakeHandledRef.current = false
      startWakeRef.current()
    }
  }, [startCommandRecognition, stopRecognition])

  const startWakeRecognition = useCallback(() => {
    const SpeechRecognition = getSpeechRecognitionConstructor()
    if (!SpeechRecognition || !enabledRef.current) return

    const recognition = new SpeechRecognition()
    modeRef.current = 'WAKE'
    recognition.continuous = true
    recognition.interimResults = true
    recognition.lang = 'en-US'

    recognition.onresult = (event) => {
      let spokenText = ''
      for (
        let index = event.resultIndex;
        index < event.results.length;
        index += 1
      ) {
        spokenText += event.results[index][0].transcript
      }

      if (containsWakeWord(spokenText) && !wakeHandledRef.current) {
        wakeHandledRef.current = true
        void handleWakeWord()
      }
    }

    recognition.onerror = () => {
      if (modeRef.current === 'WAKE') {
        setError('Wake-word listening failed. Try enabling Suzanne again.')
      }
    }

    recognition.onend = () => {
      if (modeRef.current === 'WAKE' && enabledRef.current) {
        window.setTimeout(() => startWakeRef.current(), 0)
      }
    }

    recognitionRef.current = recognition
    recognition.start()
  }, [handleWakeWord])

  const enable = useCallback(async () => {
    if (!getSpeechRecognitionConstructor()) {
      setError(
        'Wake-word listening is not supported in this browser. Try Chrome or Edge.',
      )
      return
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      stream.getTracks().forEach((track) => track.stop())
      enabledRef.current = true
      wakeHandledRef.current = false
      setEnabled(true)
      setError(null)
      startWakeRecognition()
    } catch {
      setError('Microphone permission is required for Hey Suzanne.')
    }
  }, [startWakeRecognition])

  useEffect(() => {
    callbacksRef.current = { startListening, stopListening }
  }, [startListening, stopListening])

  useEffect(() => {
    startWakeRef.current = startWakeRecognition
  }, [startWakeRecognition])

  useEffect(() => {
    if (enabled && state === 'IDLE' && !recognitionRef.current) {
      wakeHandledRef.current = false
      startWakeRecognition()
    }
  }, [enabled, startWakeRecognition, state])

  useEffect(() => {
    return () => {
      enabledRef.current = false
      stopRecognition()
    }
  }, [stopRecognition])

  return { enabled, transcript, error, enable }
}
