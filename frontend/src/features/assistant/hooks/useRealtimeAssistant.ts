import { useEffect, useRef, useState } from 'react'
import type {
  AssistantResponse,
  RouteResponse,
  StopPinpoint,
} from '../../../types/contracts'
import {
  createRealtimeSession,
  getRealtimeToolErrorMessage,
  planRouteWithTool,
  RealtimeToolRequestError,
  rerouteWithTool,
  searchRoutePoiWithTool,
} from '../../../services/realtimeAssistantApi'

export type RealtimeAssistantState =
  | 'IDLE'
  | 'CONNECTING'
  | 'LISTENING'
  | 'PROCESSING'
  | 'SPEAKING'
  | 'ERROR'

export type PoiActionState =
  | 'IDLE'
  | 'CONFIRMATION_PENDING'
  | 'REROUTING_IN_PROGRESS'
  | 'REROUTE_SUCCESS'
  | 'REROUTE_FAILED'

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

function compactRouteFacts(route: RouteResponse) {
  const chargingStop = route.chargingStop ?? route.stops.find((stop) => stop.mandatory)
  const partnerBenefit = chargingStop?.partner?.benefit ?? chargingStop?.partnerBenefit

  return {
    status: 'success',
    destination: route.destination,
    distanceKm: route.stats.totalDistanceKm,
    drivingDurationMinutes: route.stats.drivingDurationMinutes,
    totalDurationMinutes: route.stats.totalDurationMinutes,
    chargingRequired: Boolean(chargingStop),
    chargingStop: chargingStop
      ? {
          name: chargingStop.name,
          detourMinutes: chargingStop.detourMinutes,
          chargingDurationMinutes: chargingStop.chargingDurationMinutes,
          partnerLocation: Boolean(chargingStop.partner),
          ...(partnerBenefit ? { partnerBenefit } : {}),
        }
      : null,
    ...(chargingStop
      ? {
          mandatoryStops: route.stops
            .filter((stop) => stop.mandatory)
            .map((stop) => stop.name),
        }
      : {}),
    ...(route.borderCrossings.length > 0
      ? {
          borderCrossings: route.borderCrossings.map(
            (crossing) => `${crossing.fromCountry}-${crossing.toCountry}`,
          ),
        }
      : {}),
    ...(route.routeRequirements.length > 0
      ? { routeRequirements: route.routeRequirements.map((requirement) => requirement.name) }
      : {}),
  }
}

function compactPoiFacts(
  stop: StopPinpoint,
  context: { routeId?: string | null; searchId?: string | null },
) {
  return {
    id: stop.id,
    name: stop.name,
    category: stop.category,
    ...(stop.rating !== undefined ? { rating: stop.rating } : {}),
    ...(stop.tag ? { tag: stop.tag } : {}),
    ...(stop.amenities?.length ? { amenities: stop.amenities } : {}),
    detourMinutes: stop.detourMinutes,
    ...(context.routeId ? { routeId: context.routeId } : {}),
    ...(context.searchId ? { searchId: context.searchId } : {}),
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
  const [poiResults, setPoiResults] = useState<StopPinpoint[]>([])
  const [selectedPoi, setSelectedPoi] = useState<StopPinpoint | null>(null)
  const [poiActionState, setPoiActionState] = useState<PoiActionState>('IDLE')
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
  const activePriorityRef = useRef<AssistantResponse['intent']['priority']>('BALANCED')
  const assistantTranscriptRef = useRef('')
  const startingRef = useRef(false)
  const toolRequestIdRef = useRef(0)

  function sendEvent(event: Record<string, unknown>) {
    channelRef.current?.send(JSON.stringify(event))
  }

  function closeSession() {
    startingRef.current = false
    connectionAbortRef.current?.abort()
    connectionAbortRef.current = null
    toolAbortRef.current?.abort()
    toolAbortRef.current = null
    toolRequestIdRef.current += 1
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
    if (
      event.name !== 'plan_route' &&
      event.name !== 'search_route_poi' &&
      event.name !== 'reroute_through_poi'
    ) {
      return
    }

    setState('PROCESSING')
    const requestId = ++toolRequestIdRef.current
    if (event.name === 'reroute_through_poi') {
      setPoiActionState('REROUTING_IN_PROGRESS')
    }
    const toolController = new AbortController()
    toolAbortRef.current = toolController

    try {
      if (event.name === 'search_route_poi') {
        const result = await searchRoutePoiWithTool(
          event.arguments,
          toolController.signal,
        )
        if (!startingRef.current || requestId !== toolRequestIdRef.current) {
          return
        }

        setPoiResults(result.results)
        setSelectedPoi(null)
        setPoiActionState('IDLE')
        setError(
          result.results.length === 0
            ? 'No suitable stops were found along this route.'
            : null,
        )
        sendEvent({
          type: 'conversation.item.create',
          item: {
            type: 'function_call_output',
            call_id: event.call_id,
            output: JSON.stringify({
              status: 'success',
              results: result.results.map((stop) =>
                compactPoiFacts(stop, result),
              ),
            }),
          },
        })
        sendEvent({ type: 'response.create' })
        return
      }

      if (event.name === 'reroute_through_poi') {
        const result = await rerouteWithTool(
          event.arguments,
          toolController.signal,
        )
        if (!startingRef.current || requestId !== toolRequestIdRef.current) {
          return
        }

        setResponse((current) =>
          current
            ? { ...current, route: result.route }
            : createRouteResponse(result.route, activePriorityRef.current),
        )
        setPoiResults([])
        setSelectedPoi(null)
        setPoiActionState('REROUTE_SUCCESS')
        pendingRouteRef.current = {
          route: result.route,
          priority: activePriorityRef.current,
        }
        sendEvent({
          type: 'conversation.item.create',
          item: {
            type: 'function_call_output',
            call_id: event.call_id,
            output: JSON.stringify(compactRouteFacts(result.route)),
          },
        })
        sendEvent({ type: 'response.create' })
        return
      }

      const result = await planRouteWithTool(event.arguments, toolController.signal)
      if (!startingRef.current || requestId !== toolRequestIdRef.current) {
        return
      }

      setPoiResults([])
      const routePriority = getRoutePriority(event.arguments)
      activePriorityRef.current = routePriority
      pendingRouteRef.current = {
        route: result.route,
        priority: routePriority,
      }
      setPoiResults([])
      setSelectedPoi(null)
      setPoiActionState('IDLE')
      setError(null)
      sendEvent({
        type: 'conversation.item.create',
        item: {
          type: 'function_call_output',
          call_id: event.call_id,
          output: JSON.stringify(compactRouteFacts(result.route)),
        },
      })
      sendEvent({ type: 'response.create' })
    } catch (toolError) {
      if (
        !startingRef.current ||
        toolController.signal.aborted ||
        requestId !== toolRequestIdRef.current
      ) {
        if (startingRef.current) {
          setError(
            event.name === 'reroute_through_poi'
              ? 'The route could not be updated. Your previous route is unchanged.'
              : event.name === 'search_route_poi'
                ? 'Route suggestions are temporarily unavailable.'
                : 'Route planning is temporarily unavailable.',
          )
        }
        if (event.name === 'reroute_through_poi' && startingRef.current) {
          setPoiActionState('REROUTE_FAILED')
        }
        return
      }

      sendEvent({
        type: 'conversation.item.create',
        item: {
          type: 'function_call_output',
          call_id: event.call_id,
          output: JSON.stringify({
            error: (() => {
              const code =
                toolError instanceof RealtimeToolRequestError
                  ? toolError.code
                  : 'TOOL_FAILED'
              const fallback =
                toolError instanceof Error
                  ? toolError.message
                  : 'The requested assistant tool failed.'
              return {
                code,
                message: getRealtimeToolErrorMessage(code, fallback),
              }
            })(),
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

  function selectPoi(poiId: string) {
    const poi = poiResults.find((result) => result.id === poiId)
    if (!poi) {
      setSelectedPoi(null)
      setPoiActionState('REROUTE_FAILED')
      setError('That route suggestion is no longer available.')
      return
    }

    setSelectedPoi(poi)
    setPoiActionState('CONFIRMATION_PENDING')
    setError(null)

    if (startingRef.current) {
      sendEvent({
        type: 'conversation.item.create',
        item: {
          type: 'message',
          role: 'user',
          content: [
            {
              type: 'input_text',
              text: `I selected the suggested stop "${poi.name}" (POI ID: ${poi.id}). Explain the proposed detour and ask for my confirmation. Do not reroute yet.`,
            },
          ],
        },
      })
      sendEvent({ type: 'response.create' })
    }
  }

  return {
    enabled,
    state,
    transcript,
    response,
    poiResults,
    selectedPoi,
    poiActionState,
    selectPoi,
    error,
    enable,
    disable: closeSession,
  }
}