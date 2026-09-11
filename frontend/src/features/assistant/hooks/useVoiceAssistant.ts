import { useEffect, useRef, useState } from 'react'
import { sendVoice } from '../../../services/assistantApi'
import type { AssistantResponse } from '../../../types/contracts'

export type AssistantState =
  | 'IDLE'
  | 'LISTENING'
  | 'PROCESSING'
  | 'SPEAKING'

const processingAudioFiles = [
  '/audio/calculating-route.mp3',
  '/audio/checking-route.mp3',
]

function getSupportedMimeType() {
  const candidates = [
    'audio/webm;codecs=opus',
    'audio/webm',
    'audio/mp4',
  ]

  return candidates.find((type) => MediaRecorder.isTypeSupported(type))
}

interface AudioPlayback {
  finished: Promise<void>
  stop: () => void
}

function playAudioFile(path: string): AudioPlayback {
  const audio = new Audio(path)
  let resolveFinished: () => void = () => undefined

  const finished = new Promise<void>((resolve) => {
    resolveFinished = resolve
  })

  const finish = () => {
    audio.onended = null
    audio.onerror = null
    resolveFinished()
  }

  audio.onended = finish
  audio.onerror = finish

  void audio.play().catch(finish)

  return {
    finished,
    stop: () => {
      audio.pause()
      audio.currentTime = 0
      finish()
    },
  }
}

function playProcessingAudio(): AudioPlayback {
  const filename =
    processingAudioFiles[
      Math.floor(Math.random() * processingAudioFiles.length)
    ]

  return playAudioFile(filename)
}

function playBase64Audio(audioBase64: string): Promise<void> {
  return playAudioFile(`data:audio/mpeg;base64,${audioBase64}`).finished
}

export function useVoiceAssistant() {
  const [state, setState] = useState<AssistantState>('IDLE')
  const [response, setResponse] = useState<AssistantResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  const recorderRef = useRef<MediaRecorder | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const processingAudioRef = useRef<AudioPlayback | null>(null)

  function stopProcessingAudio() {
    const playback = processingAudioRef.current

    if (!playback) {
      return
    }

    playback.stop()
    processingAudioRef.current = null
  }

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
      processingAudioRef.current = playProcessingAudio()
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

      const processingAudio = processingAudioRef.current
      setResponse(assistantResponse)

      if (processingAudio) {
        await processingAudio.finished
        processingAudioRef.current = null
      }

      if (assistantResponse.audioBase64) {
        setState('SPEAKING')
        await playBase64Audio(assistantResponse.audioBase64)
      }

      setState('IDLE')
    } catch (requestError) {
      stopProcessingAudio()

      setError(
        requestError instanceof Error
          ? requestError.message
          : 'Unable to calculate your route.',
      )
      setState('SPEAKING')
      await playAudioFile('/audio/route-error.mp3').finished
      setState('IDLE')
    } finally {
      streamRef.current?.getTracks().forEach((track) => track.stop())
      streamRef.current = null
      chunksRef.current = []
    }
  }

  useEffect(() => {
    return () => {
      stopProcessingAudio()
      streamRef.current?.getTracks().forEach((track) => track.stop())
    }
  }, [])

  return {
    state,
    response,
    error,
    startListening,
    stopListening,
  }
}