import { useRef, useState } from 'react'
import { sendVoice } from '../../../services/assistantApi'
import type { AssistantResponse } from '../../../types/contracts'

export type AssistantState =
  | 'IDLE'
  | 'LISTENING'
  | 'PROCESSING'
  | 'SPEAKING'

function getSupportedMimeType() {
  const candidates = [
    'audio/webm;codecs=opus',
    'audio/webm',
    'audio/mp4',
  ]

  return candidates.find((type) => MediaRecorder.isTypeSupported(type))
}

function playBase64Audio(audioBase64: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const audio = new Audio(`data:audio/mpeg;base64,${audioBase64}`)

    audio.onended = () => resolve()
    audio.onerror = () => reject(new Error('Unable to play Suzanne audio'))

    void audio.play().catch(reject)
  })
}

export function useVoiceAssistant() {
  const [state, setState] = useState<AssistantState>('IDLE')
  const [response, setResponse] = useState<AssistantResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  const recorderRef = useRef<MediaRecorder | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const chunksRef = useRef<Blob[]>([])

  async function startListening() {
    setError(null)
    setResponse(null)

    const stream = await navigator.mediaDevices.getUserMedia({
      audio: true,
    })

    const mimeType = getSupportedMimeType()
    const recorder = mimeType
      ? new MediaRecorder(stream, { mimeType })
      : new MediaRecorder(stream)

    streamRef.current = stream
    recorderRef.current = recorder
    chunksRef.current = []

    recorder.addEventListener('dataavailable', (event) => {
      if (event.data.size > 0) {
        chunksRef.current.push(event.data)
      }
    })

    recorder.addEventListener('stop', () => {
      void processRecording(recorder.mimeType)
    })

    recorder.start()
    setState('LISTENING')
  }

  function stopListening() {
    if (recorderRef.current?.state === 'recording') {
      recorderRef.current.stop()
      recorderRef.current = null
      setState('PROCESSING')
    }
  }

  async function processRecording(mimeType: string) {
    try {
      const audioBlob = new Blob(chunksRef.current, {
        type: mimeType || 'audio/webm',
      })

      const assistantResponse = await sendVoice(audioBlob)
      setResponse(assistantResponse)

      if (assistantResponse.audioBase64) {
        setState('SPEAKING')
        await playBase64Audio(assistantResponse.audioBase64)
      }

      setState('IDLE')
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : 'Voice request failed',
      )
      setState('IDLE')
    } finally {
      streamRef.current?.getTracks().forEach((track) => track.stop())
      streamRef.current = null
      chunksRef.current = []
    }
  }

  return {
    state,
    response,
    error,
    startListening,
    stopListening,
  }
}