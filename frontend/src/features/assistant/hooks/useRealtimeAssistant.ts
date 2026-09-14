import { useEffect, useRef, useState } from 'react'
import type { AssistantResponse, RouteResponse } from '../../../types/contracts'
import {
  createRealtimeSession,
  planRouteWithTool,
} from '../../../services/realtimeAssistantApi'

export type RealtimeAssistantState =
  | 'IDLE'
  | 'CONNECTING'
  | 'LISTENING'
  | 'PROCESSING'
  | 'SPEAKING'
  | 'ERROR'

function createRouteResponse(
  route: RouteResponse,
  priority: AssistantResponse['intent']['priority'],
  spokenResponse = '',
): AssistantResponse {
  return {
    transcript: '',
    intent: {
      destination: route.destination,
      priority,
    },
    spokenResponse,
    route,
  }
}

function getRoutePriority(argumentsJson: string) {
  const argumentsValue = JSON.parse(argumentsJson) as {
    priority?: AssistantResponse['intent']['priority']
  }

  return argumentsValue.priority ?? 'BALANCED'
}

async function waitForIceGathering(peerConnection: RTCPeerConnection) {
  if (peerConnection.iceGatheringState === 'complete') {
    return
  }

  await new Promise<void>((resolve, reject) => {
    const timeout = window.setTimeout(() => {
      peerConnection.removeEventListener('icegatheringstatechange', onState)
      reject(new Error('Timed out while preparing the voice connection.'))
    }, 10_000)

    function onState() {
      if (peerConnection.iceGatheringState !== 'complete') {
        return
      }

      window.clearTimeout(timeout)
      peerConnection.removeEventListener('icegatheringstatechange', onState)
      resolve()
    }

    peerConnection.addEventListener('icegatheringstatechange', onState)
    onState()
  })
}

export function useRealtimeAssistant() {
  const [enabled, setEnabled] = useState(false)
  const [state, setState] = useState<RealtimeAssistantState>('IDLE')
  const [transcript, setTranscript] = useState('')
  const [response, setResponse] = useState<AssistantResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const connectionRef = useRef<RTCPeerConnection | null>(null)
  const channelRef = useRef<RTCDataChannel | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const feedbackAudioRef = useRef<HTMLAudioElement | null>(null)
  const connectionAbortRef = useRef<AbortController | null>(null)
  const toolAbortRef = useRef<AbortController | null>(null)
  const pendingRouteRef = useRef<{
    route: RouteResponse
    priority: AssistantResponse['intent']['priority']
  } | null>(null)
  const assistantTranscriptRef = useRef('')
  const startingRef = useRef(false)

  function sendEvent(event: Record<string, unknown>) {
    channelRef.current?.send(JSON.stringify(event))
  }

  function closeSession() {
    startingRef.current = false
    connectionAbortRef.current?.abort()
    connectionAbortRef.current = null
    toolAbortRef.current?.abort()
    toolAbortRef.current = null
    pendingRouteRef.current = null
    assistantTranscriptRef.current = ''
    channelRef.current?.close()
    channelRef.current = null
    connectionRef.current?.close()
    connectionRef.current = null
    streamRef.current?.getTracks().forEach((track) => track.stop())
    streamRef.current = null
    if (audioRef.current) {
      audioRef.current.pause()
      audioRef.current.srcObject = null
      audioRef.current.remove()
      audioRef.current = null
    }
    feedbackAudioRef.current?.pause()
    feedbackAudioRef.current = null
    setEnabled(false)
    setState('IDLE')
  }

  async function handleToolCall(event: {
    call_id: string
    name: string
    arguments: string
  }) {
    if (event.name !== 'plan_route') {
      return
    }

    setState('PROCESSING')
    const toolController = new AbortController()
    toolAbortRef.current = toolController

    try {
      const result = await planRouteWithTool(event.arguments, toolController.signal)
      if (!startingRef.current) {
        return
      }

      pendingRouteRef.current = {
        route: result.route,
        priority: getRoutePriority(event.arguments),
      }
      sendEvent({
        type: 'conversation.item.create',
        item: {
          type: 'function_call_output',
          call_id: event.call_id,
          output: JSON.stringify({
            status: 'success',
            destination: result.route.destination,
            distanceKm: result.route.stats.totalDistanceKm,
            durationMinutes: result.route.stats.totalDurationMinutes,
            vehicleAlerts: result.route.alerts
              .filter((alert) => alert.type === 'VEHICLE')
              .map((alert) => alert.message),
          }),
        },
      })
      sendEvent({ type: 'response.create' })
    } catch (toolError) {
      if (!startingRef.current || toolController.signal.aborted) {
        return
      }

      sendEvent({
        type: 'conversation.item.create',
        item: {
          type: 'function_call_output',
          call_id: event.call_id,
          output: JSON.stringify({
            error:
              toolError instanceof Error
                ? toolError.message
                : 'Route planning failed.',
          }),
        },
      })
      sendEvent({ type: 'response.create' })
    } finally {
      if (toolAbortRef.current === toolController) {
        toolAbortRef.current = null
      }
    }
  }

  async function enable() {
    if (enabled || startingRef.current) {
      return
    }

    startingRef.current = true
    setError(null)
    setState('CONNECTING')

    const feedbackAudio = new Audio('/audio/listening-jingle.mp3')
    feedbackAudioRef.current = feedbackAudio
    void feedbackAudio.play().catch(() => undefined)

    try {
      const session = await createRealtimeSession()
      if (!startingRef.current) {
        return
      }

      const peerConnection = new RTCPeerConnection()
      const audio = new Audio()
      audio.autoplay = true
      connectionRef.current = peerConnection
      audioRef.current = audio
      peerConnection.ontrack = (event) => {
        audio.srcObject = event.streams[0]
        void audio.play().catch(() => undefined)
      }

      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      if (!startingRef.current) {
        stream.getTracks().forEach((track) => track.stop())
        peerConnection.close()
        return
      }

      for (const track of stream.getTracks()) {
        peerConnection.addTrack(track, stream)
      }

      streamRef.current = stream

      const channel = peerConnection.createDataChannel('oai-events')
      channel.onmessage = (message) => {
        const event = JSON.parse(message.data) as Record<string, unknown>

        if (event.type === 'input_audio_buffer.speech_started') {
          setState('LISTENING')
        } else if (event.type === 'response.created') {
          setState('SPEAKING')
        } else if (event.type === 'response.output_audio_transcript.done') {
          const transcriptText = event.transcript
          if (typeof transcriptText === 'string') {
            assistantTranscriptRef.current = transcriptText
            setResponse((current) =>
              current ? { ...current, spokenResponse: transcriptText } : current,
            )
          }
        } else if (event.type === 'conversation.item.input_audio_transcription.completed') {
          const inputTranscript = event.transcript
          if (typeof inputTranscript === 'string') {
            setTranscript(inputTranscript)
          }
        } else if (event.type === 'response.function_call_arguments.done') {
          void handleToolCall({
            call_id: String(event.call_id),
            name: String(event.name),
            arguments: String(event.arguments),
          })
        } else if (event.type === 'response.done') {
          if (pendingRouteRef.current) {
            const pendingRoute = pendingRouteRef.current
            pendingRouteRef.current = null
            setResponse(
              createRouteResponse(
                pendingRoute.route,
                pendingRoute.priority,
                assistantTranscriptRef.current,
              ),
            )
          }
          setState('LISTENING')
        } else if (event.type === 'error') {
          const eventError = event.error as { message?: string } | undefined
          setError(
            eventError?.message ??
              'Realtime assistant failed to process the request.',
          )
          setState('ERROR')
        }
      }

      const offer = await peerConnection.createOffer()
      await peerConnection.setLocalDescription(offer)
      await waitForIceGathering(peerConnection)

      if (!startingRef.current) {
        throw new Error('Voice connection was stopped.')
      }

      const controller = new AbortController()
      connectionAbortRef.current = controller
      const timeout = window.setTimeout(() => controller.abort(), 15_000)
      try {
        const answerResponse = await fetch(
            `https://api.openai.com/v1/realtime/calls?model=${encodeURIComponent(session.model)}`,
          {
            method: 'POST',
            body: peerConnection.localDescription?.sdp,
            headers: {
              Authorization: `Bearer ${session.clientSecret}`,
              'Content-Type': 'application/sdp',
            },
            signal: controller.signal,
          },
        )

        if (!answerResponse.ok) {
          throw new Error(`Realtime connection failed with HTTP ${answerResponse.status}`)
        }

        await peerConnection.setRemoteDescription({
          type: 'answer',
          sdp: await answerResponse.text(),
        })
      } finally {
        window.clearTimeout(timeout)
        connectionAbortRef.current = null
      }

      channelRef.current = channel
      setEnabled(true)
      setState('LISTENING')
    } catch (connectionError) {
      const stoppedByUser = !startingRef.current
      startingRef.current = false
      channelRef.current?.close()
      connectionRef.current?.close()
      streamRef.current?.getTracks().forEach((track) => track.stop())
      streamRef.current = null
      audioRef.current?.pause()
      audioRef.current?.remove()
      audioRef.current = null
      if (stoppedByUser) {
        return
      }

      if (connectionError instanceof DOMException && connectionError.name === 'AbortError') {
        setError('Realtime connection timed out.')
      } else {
        setError(
          connectionError instanceof Error
            ? connectionError.message
            : 'Unable to connect Suzanne.',
        )
      }
      setState('ERROR')
    }
  }

  useEffect(() => closeSession, [])

  return {
    enabled,
    state,
    transcript,
    response,
    error,
    enable,
    disable: closeSession,
  }
}