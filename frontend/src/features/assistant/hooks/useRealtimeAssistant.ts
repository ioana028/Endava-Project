import { useCallback, useEffect, useRef, useState } from 'react'
import type {
  AssistantResponse,
  BookingResponse,
  PurchaseVignetteResponse,
  RouteResponse,
  StartDrivingResponse,
  StopPinpoint,
} from '../../../types/contracts'
import {
  bookHotelRoomWithTool,
  bookRestaurantTableWithTool,
  confirmChargingStopWithTool,
  createRealtimeCall,
  getVehicleContextWithTool,
  getRealtimeToolErrorMessage,
  planRouteWithTool,
  purchaseVignetteWithTool,
  RealtimeToolRequestError,
  returnToMainRouteWithTool,
  rerouteWithTool,
  searchRoutePoiWithTool,
  searchStopAmenitiesWithTool,
  startDrivingWithTool,
} from '../../../services/realtimeAssistantApi'
import { RealtimeTurnController } from '../realtimeTurnController'
import { compactRouteFacts } from '../routeFacts'
import { AMENITIES_RESULT_INSTRUCTIONS, compactPoiUpdateFacts, POI_UPDATE_INSTRUCTIONS, VIGNETTE_RESULT_INSTRUCTIONS } from '../actionNarration'

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

export type AmenitySearchState =
  | 'IDLE'
  | 'LOADING'
  | 'SUCCESS'
  | 'EMPTY'
  | 'STALE'
  | 'FAILURE'

export const REALTIME_CONNECTION_CONFIRMED_EVENT = 'suzanne:connection-confirmed'

export interface RealtimeTelemetry {
  startPressed?: number
  microphoneRequested?: number
  microphoneGranted?: number
  sessionRequestStarted?: number
  sessionRequestCompleted?: number
  peerConnectionCreated?: number
  dataChannelOpened?: number
  remoteDescriptionApplied?: number
  assistantReady?: number
  toolCallStarted?: number
  toolCallCompleted?: number
}

export interface PurchaseState extends Omit<PurchaseVignetteResponse, 'status'> {
  status: PurchaseVignetteResponse['status'] | 'pending' | 'failed'
}

export interface BookingState extends Omit<BookingResponse, 'status'> {
  status: BookingResponse['status'] | 'pending' | 'failed'
}

export interface DrivingState extends StartDrivingResponse {
  active: boolean
}

export interface SuccessFeedback {
  action: 'purchase' | 'booking' | 'driving'
  label: string
  reference: string
}

export function formatEurAmount(amountEur: number): string {
  return `${amountEur.toFixed(2)} euros`
}

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

function compactPoiFacts(
  stop: StopPinpoint,
  context: { routeId?: string | null; searchId?: string | null },
) {
  const partnerFact = stop.partner?.verified && stop.partner.benefit
    ? {
        benefit: stop.partner.benefit,
        ...(stop.partner.benefitScope
          ? { benefitScope: stop.partner.benefitScope }
          : {}),
        ...(stop.partner.benefitSource
          ? { benefitSource: stop.partner.benefitSource }
          : {}),
        verified: true,
      }
    : null

  return {
    id: stop.id,
    name: stop.name,
    category: stop.category,
    ...(typeof stop.rating === 'number' ? { rating: stop.rating } : {}),
    ...(stop.userReviewCount !== undefined
      ? { userReviewCount: stop.userReviewCount }
      : {}),
    ...(stop.tag ? { tag: stop.tag } : {}),
    ...(stop.details ? { details: stop.details } : {}),
    ...(stop.keywords?.length ? { keywords: stop.keywords.slice(0, 3) } : {}),
    ...(stop.amenities?.length ? { amenities: stop.amenities } : {}),
    ...(stop.distanceMeters !== undefined ? { distanceMeters: stop.distanceMeters } : {}),
    ...(stop.routeOffsetKm !== undefined ? { routeOffsetKm: stop.routeOffsetKm } : {}),
    detourMinutes: Math.round(
      stop.estimatedDrivingDetourMinutes ?? stop.detourMinutes,
    ),
    ...(partnerFact ? { partnerFact } : {}),
    ...(context.routeId ? { routeId: context.routeId } : {}),
    ...(context.searchId ? { searchId: context.searchId } : {}),
  }
}

function compactAmenityFacts(stop: StopPinpoint) {
  const partnerFact = stop.partner?.verified && stop.partner.benefit
    ? {
        benefit: stop.partner.benefit,
        ...(stop.partner.benefitScope
          ? { benefitScope: stop.partner.benefitScope }
          : {}),
        ...(stop.partner.benefitSource
          ? { benefitSource: stop.partner.benefitSource }
          : {}),
        verified: true,
      }
    : null

  return {
    id: stop.id,
    name: stop.name,
    category: stop.category,
    ...(stop.amenities?.length ? { amenities: stop.amenities } : {}),
    ...(stop.distanceMeters !== undefined
      ? { distanceMeters: stop.distanceMeters }
      : {}),
    ...(partnerFact ? { partnerFact } : {}),
  }
}

function getAmenityLoadingContext(
  argumentsJson: string,
  route: RouteResponse | undefined,
  candidates: StopPinpoint[],
) {
  try {
    const argumentsValue = JSON.parse(argumentsJson) as {
      stopId?: unknown
      routeId?: unknown
      searchId?: unknown
    }
    if (typeof argumentsValue.stopId !== 'string') {
      return null
    }

    const routeStops = route
      ? [
          ...(route.chargingStop ? [route.chargingStop] : []),
          ...route.chargingOptions.map((option) => option.stop),
          ...route.stops,
        ]
      : []
    const selectedStop = [...candidates, ...routeStops].find(
      (stop) => stop.id === argumentsValue.stopId && stop.category === 'charging',
    )
    if (!selectedStop) {
      return null
    }

    return {
      selectedStopName: selectedStop.name,
      radiusMeters: 500,
      routeId:
        typeof argumentsValue.routeId === 'string' ? argumentsValue.routeId : '',
      searchId:
        typeof argumentsValue.searchId === 'string'
          ? argumentsValue.searchId
          : null,
    }
  } catch {
    return null
  }
}

function getRoutePriority(argumentsJson: string) {
  const argumentsValue = JSON.parse(argumentsJson) as {
    priority?: AssistantResponse['intent']['priority']
  }

  return argumentsValue.priority ?? 'BALANCED'
}

async function waitForDataChannelOpen(channel: RTCDataChannel, signal: AbortSignal) {
  if (channel.readyState === 'open') {
    return
  }

  await new Promise<void>((resolve, reject) => {
    const timeout = window.setTimeout(() => {
      cleanup()
      reject(new Error('Timed out while opening the voice data channel.'))
    }, 15_000)

    function onOpen() {
      cleanup()
      resolve()
    }
    function onFailure() {
      cleanup()
      reject(signal.aborted
        ? new DOMException('Voice connection aborted.', 'AbortError')
        : new Error('The voice connection was closed.'))
    }
    function cleanup() {
      window.clearTimeout(timeout)
      channel.removeEventListener('open', onOpen)
      channel.removeEventListener('close', onFailure)
      channel.removeEventListener('error', onFailure)
      signal.removeEventListener('abort', onFailure)
    }
    channel.addEventListener('open', onOpen)
    channel.addEventListener('close', onFailure)
    channel.addEventListener('error', onFailure)
    signal.addEventListener('abort', onFailure, { once: true })
    if (signal.aborted || channel.readyState === 'closed') onFailure()
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
  const [amenityResults, setAmenityResults] = useState<StopPinpoint[]>([])
  const [amenityMarkersVisible, setAmenityMarkersVisible] = useState(false)
  const [amenitySearchState, setAmenitySearchState] = useState<AmenitySearchState>('IDLE')
  const [amenitySearchContext, setAmenitySearchContext] = useState<{
    selectedStopName: string
    radiusMeters: number
    routeId: string
    searchId: string | null
  } | null>(null)
  const [purchase, setPurchase] = useState<PurchaseState | null>(null)
  const [booking, setBooking] = useState<BookingState | null>(null)
  const [driving, setDriving] = useState<DrivingState | null>(null)
  const [chargingStopConfirmed, setChargingStopConfirmed] = useState(false)
  const [chargingStopFocus, setChargingStopFocus] = useState<StopPinpoint | null>(null)
  const [destinationFocus, setDestinationFocus] = useState(false)
  const [successFeedback, setSuccessFeedback] = useState<SuccessFeedback | null>(null)
  const [selectedBookingPoi, setSelectedBookingPoi] = useState<StopPinpoint | null>(null)
  const [telemetry, setTelemetry] = useState<RealtimeTelemetry>({})
  const [error, setError] = useState<string | null>(null)
  const connectionRef = useRef<RTCPeerConnection | null>(null)
  const channelRef = useRef<RTCDataChannel | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const feedbackAudioRef = useRef<HTMLAudioElement | null>(null)
  const listeningJinglePlayedRef = useRef(false)
  const listeningJinglePlaybackRef = useRef<Promise<void> | null>(null)
  const connectionAbortRef = useRef<AbortController | null>(null)
  const toolAbortRef = useRef<AbortController | null>(null)
  const toolCallInFlightRef = useRef(false)
  const activePriorityRef = useRef<AssistantResponse['intent']['priority']>('BALANCED')
  const assistantTranscriptRef = useRef('')
  const startingRef = useRef(false)
  const sessionGenerationRef = useRef(0)
  const toolRequestIdRef = useRef(0)
  const successFeedbackTimerRef = useRef<number | null>(null)
  const bookingPanelTimerRef = useRef<number | null>(null)
  const chargingSpeechPhaseRef = useRef<'plan' | 'amenities' | null>(null)
  const chargingAmenitiesFocusStopRef = useRef<StopPinpoint | null>(null)
  const chargingSpeechResponseIdRef = useRef<string | null>(null)
  const turnControllerRef = useRef<RealtimeTurnController | null>(null)
  const speechStartedAtRef = useRef(0)
  const currentRouteRef = useRef<RouteResponse | undefined>(undefined)

  useEffect(() => {
    // The WebRTC callback outlives the render that opened the connection.
    currentRouteRef.current = response?.route
  }, [response])

  function recordTelemetry(name: keyof RealtimeTelemetry) {
    setTelemetry((current) => ({ ...current, [name]: performance.now() }))
  }

  function sendEvent(event: Record<string, unknown>) {
    if (event.type === 'response.create') {
      turnControllerRef.current?.request(event, event.response ? 'result' : 'user')
    } else if (channelRef.current?.readyState === 'open') {
      channelRef.current.send(JSON.stringify(event))
    }
  }

  function isSessionCurrent(generation: number) {
    return startingRef.current && sessionGenerationRef.current === generation
  }

  function showSuccessFeedback(feedback: SuccessFeedback) {
    if (successFeedbackTimerRef.current !== null) {
      window.clearTimeout(successFeedbackTimerRef.current)
    }
    if (bookingPanelTimerRef.current !== null) {
      window.clearTimeout(bookingPanelTimerRef.current)
      bookingPanelTimerRef.current = null
    }
    setSuccessFeedback(feedback)
    successFeedbackTimerRef.current = window.setTimeout(() => {
      setSuccessFeedback(null)
      successFeedbackTimerRef.current = null
    }, 5000)
  }

  const clearChargingMapFocus = useCallback(() => {
    chargingSpeechPhaseRef.current = null
    chargingAmenitiesFocusStopRef.current = null
    chargingSpeechResponseIdRef.current = null
    setChargingStopFocus(null)
  }, [])

  const closeSession = useCallback(() => {
    sessionGenerationRef.current += 1
    startingRef.current = false
    connectionAbortRef.current?.abort()
    connectionAbortRef.current = null
    toolAbortRef.current?.abort()
    toolAbortRef.current = null
    toolRequestIdRef.current += 1
    toolCallInFlightRef.current = false
    turnControllerRef.current?.reset()
    turnControllerRef.current = null
    if (bookingPanelTimerRef.current !== null) {
      window.clearTimeout(bookingPanelTimerRef.current)
      bookingPanelTimerRef.current = null
    }
    if (successFeedbackTimerRef.current !== null) {
      window.clearTimeout(successFeedbackTimerRef.current)
      successFeedbackTimerRef.current = null
    }
    setSuccessFeedback(null)
    clearChargingMapFocus()
    setDestinationFocus(false)
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
  }, [clearChargingMapFocus])

  async function handleToolCall(event: {
    call_id: string
    name: string
    arguments: string
  }, generation: number) {
    if (!isSessionCurrent(generation)) {
      return
    }
    if (
      event.name !== 'plan_route' &&
      event.name !== 'search_route_poi' &&
      event.name !== 'search_stop_amenities' &&
      event.name !== 'confirm_charging_stop' &&
      event.name !== 'reroute_through_poi' &&
      event.name !== 'purchase_vignette' &&
      event.name !== 'book_hotel_room' &&
      event.name !== 'book_restaurant_table' &&
      event.name !== 'start_driving' &&
      event.name !== 'return_to_main_route'
      && event.name !== 'get_vehicle_context'
    ) {
      return
    }

    const disposition = turnControllerRef.current?.beginTool(event.call_id, event.name)
    if (disposition === 'duplicate') return
    if (disposition === 'busy') {
      sendEvent({ type: 'conversation.item.create', item: {
        type: 'function_call_output', call_id: event.call_id,
        output: JSON.stringify({ error: { code: 'ACTION_IN_PROGRESS', message: 'An action is already processing. Do not repeat or confirm this action.' } }),
      } })
      return
    }
    setState('PROCESSING')
    toolCallInFlightRef.current = true
    recordTelemetry('toolCallStarted')
    const requestId = ++toolRequestIdRef.current
    if (event.name === 'reroute_through_poi') {
      setPoiActionState('REROUTING_IN_PROGRESS')
    }
    if (event.name === 'search_route_poi') {
      try {
        const search = JSON.parse(event.arguments) as { category?: string; location?: string }
        setDestinationFocus(
          (search.category === 'hotel' || search.category === 'restaurant') &&
          search.location === 'destination',
        )
      } catch {
        setDestinationFocus(false)
      }
    } else if (
      event.name === 'plan_route' ||
      event.name === 'confirm_charging_stop' ||
      event.name === 'reroute_through_poi' ||
      event.name === 'return_to_main_route' ||
      event.name === 'start_driving'
    ) {
      setDestinationFocus(false)
    }
    const toolController = new AbortController()
    toolAbortRef.current = toolController

    try {
      if (event.name === 'get_vehicle_context') {
        const result = await getVehicleContextWithTool(event.arguments, toolController.signal)
        if (!isSessionCurrent(generation) || requestId !== toolRequestIdRef.current) {
          return
        }
        sendEvent({
          type: 'conversation.item.create',
          item: {
            type: 'function_call_output',
            call_id: event.call_id,
            output: JSON.stringify({
              status: 'success',
              currentLocation: result.currentLocation,
              vehicleModel: result.vehicleModel,
              currentRangeKm: Math.round(result.currentRangeKm),
              maxRangeKm: Math.round(result.maxRangeKm),
              batteryPercent: Math.round(result.batteryPercent),
              consumptionRateKwh: result.consumptionRateKwh,
              connectorTypes: result.connectorTypes,
              maxChargingPowerKw: result.maxChargingPowerKw,
            }),
          },
        })
        sendEvent({
          type: 'response.create',
          response: {
            instructions:
              'Answer the direct location or vehicle question in one concise sentence using only the returned facts. Do not mention internal IDs or make a Google request.',
          },
        })
        return
      }

      if (event.name === 'search_route_poi') {
        const requestedSearch = JSON.parse(event.arguments) as { category: string; location: string; preference?: string }
        const result = await searchRoutePoiWithTool(
          event.arguments,
          toolController.signal,
        )
        if (!isSessionCurrent(generation) || requestId !== toolRequestIdRef.current) {
          return
        }

        setPoiResults(result.results)
        setAmenityResults([])
        setAmenityMarkersVisible(false)
        setAmenitySearchContext(null)
        setAmenitySearchState('IDLE')
        setSelectedPoi(null)
        clearChargingMapFocus()
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
              requestedSearch,
              ...(result.opportunities?.length
                ? { opportunities: result.opportunities }
                : {}),
              results: result.results.map((stop) =>
                compactPoiFacts(stop, result),
              ),
            }),
          },
        })
        sendEvent({
          type: 'response.create',
          response: {
            instructions:
              'Describe only the latest returned search results and requestedSearch. Discard earlier rejected suggestions and categories; never combine the current cuisine with a previous mistaken category. In one concise response, give at most two returned hotels or restaurants and describe each in one short phrase using returned details, tags, amenities, or category. For attractions, choose one useful description from returned details or tags, and include rating and review count when present. Translate a non-English name into a speech-only English rendering when reliable, but preserve official names for maps and tool calls. Use only returned facts; do not claim an option matches a preference without supporting facts, invent review sentiment, repeat details, or add a separate acknowledgement.',
          },
        })
        return
      }

      if (event.name === 'confirm_charging_stop') {
        const result = await confirmChargingStopWithTool(
          event.arguments,
          toolController.signal,
        )
        if (!isSessionCurrent(generation) || requestId !== toolRequestIdRef.current) {
          return
        }

        setResponse((current) =>
          current
            ? { ...current, route: result.route }
            : createRouteResponse(result.route, activePriorityRef.current),
        )
        setChargingStopConfirmed(true)
        clearChargingMapFocus()
        chargingAmenitiesFocusStopRef.current =
          result.amenitiesAvailable !== false && result.results.length > 0
            ? result.route.chargingStop
              ?? result.route.stops.find((stop) => stop.category === 'charging')
              ?? null
            : null
        // Keep the nearby list available without displaying amenity pins.
        setAmenityResults(result.results)
        setPoiResults([])
        setSelectedPoi(null)
        setAmenityMarkersVisible(false)
        setAmenitySearchContext({
          selectedStopName: result.selectedStopName,
          radiusMeters: result.radiusMeters,
          routeId: result.routeId,
          searchId: result.searchId ?? null,
        })
        setAmenitySearchState(
          result.amenitiesAvailable === false
            ? 'FAILURE'
            : result.results.length
              ? 'SUCCESS'
              : 'EMPTY',
        )
        setError(null)
        sendEvent({
          type: 'conversation.item.create',
          item: {
            type: 'function_call_output',
            call_id: event.call_id,
            output: JSON.stringify({
              status: 'success',
              routeId: result.routeId,
              routeRequirements: compactRouteFacts(result.route).routeRequirements,
              amenitiesStatus:
                result.amenitiesAvailable === false
                  ? 'unavailable'
                  : result.results.length
                    ? 'available'
                    : 'empty',
              chargingPlan: result.chargingPlan ?? result.route.chargingPlan
                ? {
                    stops: (result.chargingPlan ?? result.route.chargingPlan)?.stops.map((stop) => ({
                      name: stop.name,
                      chargingDurationMinutes: Math.round(stop.chargingDurationMinutes ?? 0),
                      ...(stop.partner?.verified && stop.partner.benefit
                        ? { partnerBenefit: stop.partner.benefit }
                        : {}),
                    })),
                  }
                : undefined,
              nearbyAmenities: result.results.map(compactAmenityFacts),
            }),
          },
        })
        chargingSpeechPhaseRef.current = 'plan'
        sendEvent({
          type: 'response.create',
          response: {
            instructions:
              'In one concise response, confirm the complete returned charging plan and state each returned station and charging duration once. Do not mention nearby amenities or amenitiesStatus yet, and do not announce a search, say you will check nearby, or introduce the next response. Stop after the charging details. Do not ask for another confirmation, repeat route requirements, or claim the route was replanned. Mention a verified returned partner benefit at most once.',
          },
        })
        return
      }

      if (
        event.name === 'purchase_vignette' ||
        event.name === 'book_hotel_room' ||
        event.name === 'book_restaurant_table' ||
        event.name === 'start_driving' ||
        event.name === 'return_to_main_route'
      ) {
        let result: PurchaseVignetteResponse | BookingResponse | StartDrivingResponse | { status: 'success'; routeId: string }
        if (event.name === 'purchase_vignette') {
          result = await purchaseVignetteWithTool(event.arguments, toolController.signal)
        } else if (event.name === 'book_hotel_room') {
          result = await bookHotelRoomWithTool(event.arguments, toolController.signal)
        } else if (event.name === 'book_restaurant_table') {
          result = await bookRestaurantTableWithTool(event.arguments, toolController.signal)
        } else if (event.name === 'start_driving') {
          result = await startDrivingWithTool(event.arguments, toolController.signal)
        } else {
          result = await returnToMainRouteWithTool(event.arguments, toolController.signal)
        }
        if (!isSessionCurrent(generation) || requestId !== toolRequestIdRef.current) {
          return
        }
        if (event.name === 'purchase_vignette') {
          const purchaseResult = result as PurchaseVignetteResponse
          setPurchase({ ...purchaseResult, status: purchaseResult.status })
          if (purchaseResult.sessionFacts) {
            setResponse(current => current?.route ? {
              ...current, route: { ...current.route, sessionFacts: purchaseResult.sessionFacts },
            } : current)
          }
          showSuccessFeedback({
            action: 'purchase',
            label: 'Vignette purchase confirmed',
            reference: purchaseResult.transactionId,
          })
        } else if (event.name === 'book_hotel_room' || event.name === 'book_restaurant_table') {
          const bookingResult = result as BookingResponse
          setBooking({ ...bookingResult, status: bookingResult.status })
          if (bookingPanelTimerRef.current !== null) {
            window.clearTimeout(bookingPanelTimerRef.current)
          }
          bookingPanelTimerRef.current = window.setTimeout(() => {
            setBooking(null)
            bookingPanelTimerRef.current = null
          }, 5000)
          if (bookingResult.status === 'completed' || bookingResult.status === 'duplicate') {
            showSuccessFeedback({
              action: 'booking',
              label: `${bookingResult.bookingType === 'hotel_room' ? 'Hotel room' : 'Restaurant table'} confirmed`,
              reference: bookingResult.bookingId,
            })
          } else {
            setError('The booking was not completed. Please try again.')
          }
        } else if (event.name === 'start_driving') {
          setDriving({ ...result as StartDrivingResponse, active: true })
          showSuccessFeedback({
            action: 'driving',
            label: 'Driving mode active',
            reference: 'route-active',
          })
        } else {
          clearChargingMapFocus()
          setAmenityResults([])
          setAmenityMarkersVisible(false)
          setAmenitySearchContext(null)
          setAmenitySearchState('IDLE')
        }
        sendEvent({
          type: 'conversation.item.create',
          item: {
            type: 'function_call_output',
            call_id: event.call_id,
            output: JSON.stringify({
              ...result,
              ...(event.name === 'purchase_vignette' &&
              'amountEur' in result &&
              typeof result.amountEur === 'number'
                ? { amountSpoken: formatEurAmount(result.amountEur) }
                : {}),
            }),
          },
        })
        sendEvent({
          type: 'response.create',
          response: {
            instructions:
              event.name === 'return_to_main_route'
                ? 'Confirm that the full route view has been restored. Keep it to one short sentence and do not claim that a new route was planned.'
                : event.name === 'purchase_vignette'
                  ? VIGNETTE_RESULT_INSTRUCTIONS
                  : event.name === 'book_hotel_room' || event.name === 'book_restaurant_table'
                    ? 'Confirm the returned booking status once. Never claim an external reservation or phone notification. Never speak the booking ID, result ID, route ID, or other internal identifier.'
                    : 'Use one concise sentence to confirm the action and state only its useful returned result. Do not repeat an acknowledgement or speak internal IDs or reference codes.',
          },
        })
        return
      }

      if (event.name === 'search_stop_amenities') {
        setAmenityResults([])
        setAmenityMarkersVisible(false)
        setAmenitySearchContext(
          getAmenityLoadingContext(event.arguments, response?.route, [
            ...(selectedPoi ? [selectedPoi] : []),
            ...(chargingStopFocus ? [chargingStopFocus] : []),
            ...poiResults,
          ]),
        )
        setAmenitySearchState('LOADING')
        setError(null)
        const result = await searchStopAmenitiesWithTool(
          event.arguments,
          toolController.signal,
        )
        if (!isSessionCurrent(generation) || requestId !== toolRequestIdRef.current) {
          return
        }

        setAmenityResults(result.results)
        setAmenityMarkersVisible(true)
        setPoiResults([])
        setSelectedPoi(null)
        setPoiActionState('IDLE')
        setAmenitySearchContext({
          selectedStopName: result.selectedStopName,
          radiusMeters: result.radiusMeters,
          routeId: result.routeId ?? '',
          searchId: result.searchId ?? null,
        })
        setAmenitySearchState(result.results.length ? 'SUCCESS' : 'EMPTY')
        setError(
          result.results.length === 0
            ? `No amenities were found within ${result.radiusMeters} metres of ${result.selectedStopName}.`
            : null,
        )
        sendEvent({
          type: 'conversation.item.create',
          item: {
            type: 'function_call_output',
            call_id: event.call_id,
            output: JSON.stringify({
              status: result.results.length ? 'success' : 'empty',
              selectedStopName: result.selectedStopName,
              radiusMeters: result.radiusMeters,
              ...(result.opportunities?.length
                ? { opportunities: result.opportunities }
                : {}),
              results: result.results.map(compactAmenityFacts),
            }),
          },
        })
        sendEvent({
          type: 'response.create',
          response: {
            instructions:
              'Give one concise factual result using only returned places, categories, and distances. If there are no results, say none were found. Do not add a separate acknowledgement or infer amenities that were not returned.',
          },
        })
        return
      }

      if (event.name === 'reroute_through_poi') {
        const previousRoute = currentRouteRef.current
        const result = await rerouteWithTool(
          event.arguments,
          toolController.signal,
        )
        if (!isSessionCurrent(generation) || requestId !== toolRequestIdRef.current) {
          return
        }

        setResponse((current) =>
          current
            ? { ...current, route: result.route }
            : createRouteResponse(result.route, activePriorityRef.current),
        )
        setPoiResults([])
        setSelectedPoi(null)
        const reroutedChargingStop = result.route.stops.find((stop) => stop.category === 'charging')
        setChargingStopConfirmed(Boolean(reroutedChargingStop))
        // Adding a POI waypoint must keep the full-route viewport. Charger
        // focus is reserved for the explicit charging-stop amenities flow.
        clearChargingMapFocus()
        setPoiActionState('REROUTE_SUCCESS')
        // Nearby amenities are an explicit follow-up request. Searching them
        // here adds an unnecessary provider call and leaves a stale charger
        // focus that makes the map zoom into the station after any waypoint.
        setAmenityResults([])
        setAmenityMarkersVisible(false)
        setAmenitySearchContext(null)
        setAmenitySearchState('IDLE')
        sendEvent({
          type: 'conversation.item.create',
          item: {
            type: 'function_call_output',
            call_id: event.call_id,
            output: JSON.stringify({
              ...compactRouteFacts(result.route, {
                ...(result.routeId ? { routeId: result.routeId } : {}),
              }),
              updateFacts: compactPoiUpdateFacts(previousRoute, result.route),
            }),
          },
        })
        sendEvent({
          type: 'response.create',
          response: {
            instructions:
              `Use only updateFacts for this narration. ${POI_UPDATE_INSTRUCTIONS}`,
          },
        })
        return
      }

      const result = await planRouteWithTool(event.arguments, toolController.signal)
      if (!isSessionCurrent(generation) || requestId !== toolRequestIdRef.current) {
        return
      }

      setPoiResults([])
      setAmenityResults([])
      setAmenityMarkersVisible(false)
      setAmenitySearchContext(null)
      setAmenitySearchState('IDLE')
      setPurchase(null)
      setBooking(null)
      setDriving(null)
      setChargingStopConfirmed(false)
      clearChargingMapFocus()
      setSelectedBookingPoi(null)
      const routePriority = getRoutePriority(event.arguments)
      activePriorityRef.current = routePriority
      setResponse(createRouteResponse(result.route, routePriority))
      setPoiResults([])
      setSelectedPoi(null)
      setPoiActionState('IDLE')
      setError(null)
      sendEvent({
        type: 'conversation.item.create',
        item: {
          type: 'function_call_output',
          call_id: event.call_id,
          output: JSON.stringify(
            compactRouteFacts(result.route, {
              routeId: result.routeId,
              searchId: result.searchId,
            }),
          ),
        },
      })
      sendEvent({
        type: 'response.create',
        response: {
          instructions:
            'Give the route overview in no more than two concise sentences. Say the destination and approximate travelTime once; if routeWeatherSummary is present, include its condition and temperature naturally. Then phrase only positive requirements as actions: "You will need to stop for charging" if chargingRequired is true, "buy a motorway vignette" if vignetteCount is positive, and mention a toll only if tollRequired is true. When any requirement is present, finish with one offer: "Shall I help with that?" Never say "no other tolls" or mention any absent requirement. Omit missing weather and requirements. Do not mention alerts, IDs, telemetry, opportunities, unconfirmed chargers, or repeat an acknowledgement.',
        },
      })
    } catch (toolError) {
      if (
        !isSessionCurrent(generation) ||
        toolController.signal.aborted ||
        requestId !== toolRequestIdRef.current
      ) {
        if (isSessionCurrent(generation)) {
          setError(
            event.name === 'reroute_through_poi'
              ? 'The route could not be updated. Your previous route is unchanged.'
              : event.name === 'search_route_poi'
                ? 'Route suggestions are temporarily unavailable.'
                : 'Route planning is temporarily unavailable.',
          )
        }
        if (event.name === 'reroute_through_poi' && isSessionCurrent(generation)) {
          setPoiActionState('REROUTE_FAILED')
        }
        if (event.name === 'search_route_poi' && isSessionCurrent(generation)) {
          setDestinationFocus(false)
        }
        if (event.name === 'search_stop_amenities' && isSessionCurrent(generation)) {
          setAmenitySearchState('STALE')
        }
        return
      }

      if (event.name === 'search_stop_amenities') {
        const code =
          toolError instanceof RealtimeToolRequestError
            ? toolError.code
            : 'TOOL_FAILED'
        setAmenitySearchState(
          code.startsWith('STALE_') ? 'STALE' : 'FAILURE',
        )
      }
      if (event.name === 'search_route_poi') {
        setDestinationFocus(false)
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
      sendEvent({ type: 'response.create', response: {
        instructions: 'Explain the returned tool error once in a short sentence. Ask only the returned clarification if necessary; never ask for an internal ID or claim success.',
      } })
    } finally {
      if (isSessionCurrent(generation)) {
        toolCallInFlightRef.current = false
        turnControllerRef.current?.finishTool(event.call_id)
        recordTelemetry('toolCallCompleted')
        if (toolAbortRef.current === toolController) {
          toolAbortRef.current = null
        }
      }
    }
  }

  async function enable() {
    if (enabled || startingRef.current) {
      return
    }

    startingRef.current = true
    const generation = sessionGenerationRef.current + 1
    const connectionStartedAt = performance.now()
    sessionGenerationRef.current = generation
    recordTelemetry('startPressed')
    setError(null)
    setState('CONNECTING')

    if (!listeningJinglePlayedRef.current) {
      listeningJinglePlayedRef.current = true
      const feedbackAudio = new Audio('/audio/listening-jingle.mp3')
      feedbackAudio.preload = 'auto'
      feedbackAudioRef.current = feedbackAudio
      const playbackEnded = new Promise<void>((resolve) => {
        const timeout = window.setTimeout(finish, 2500)
        function finish() {
          window.clearTimeout(timeout)
          feedbackAudio.removeEventListener('ended', finish)
          feedbackAudio.removeEventListener('pause', finish)
          feedbackAudio.removeEventListener('error', finish)
          resolve()
        }
        feedbackAudio.addEventListener('ended', finish, { once: true })
        feedbackAudio.addEventListener('pause', finish, { once: true })
        feedbackAudio.addEventListener('error', finish, { once: true })
      })
      listeningJinglePlaybackRef.current = feedbackAudio
        .play()
        .then(() => playbackEnded)
        .catch(() => undefined)
    }

    try {
      recordTelemetry('microphoneRequested')
      const stream = await navigator.mediaDevices
        .getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } })
        .then((stream) => {
          stream.getAudioTracks().forEach((track) => { track.enabled = false })
          if (isSessionCurrent(generation)) {
            recordTelemetry('microphoneGranted')
          }
          return stream
        })
      if (!isSessionCurrent(generation)) {
        stream.getTracks().forEach((track) => track.stop())
        return
      }

      streamRef.current = stream
      const microphoneReadyAt = performance.now()
      const peerConnection = new RTCPeerConnection()
      recordTelemetry('peerConnectionCreated')
      const audio = new Audio()
      audio.autoplay = true
      connectionRef.current = peerConnection
      audioRef.current = audio
      peerConnection.ontrack = (event) => {
        if (!isSessionCurrent(generation)) {
          return
        }
        audio.srcObject = event.streams[0]
        void audio.play().catch(() => undefined)
      }

      for (const track of stream.getTracks()) {
        peerConnection.addTrack(track, stream)
      }

      streamRef.current = stream

      const channel = peerConnection.createDataChannel('oai-events')
      channelRef.current = channel
      turnControllerRef.current = new RealtimeTurnController(
        (event) => {
          if (isSessionCurrent(generation) && channel.readyState === 'open') {
            channel.send(JSON.stringify(event))
          }
        },
        (responseId, status) => {
          if (!isSessionCurrent(generation)) return
          if (responseId === chargingSpeechResponseIdRef.current) {
            if (status !== 'completed') {
              clearChargingMapFocus()
            } else if (chargingSpeechPhaseRef.current === 'plan') {
              chargingSpeechPhaseRef.current = 'amenities'
              chargingSpeechResponseIdRef.current = null
              sendEvent({ type: 'response.create', response: {
                instructions: AMENITIES_RESULT_INSTRUCTIONS,
              } })
            } else {
              clearChargingMapFocus()
            }
          }
          setState(toolCallInFlightRef.current ? 'PROCESSING' : 'LISTENING')
        },
      )
      channel.onopen = () => {
        if (isSessionCurrent(generation)) {
          // VAD and tools are configured atomically by the backend at call creation.
          recordTelemetry('dataChannelOpened')
        }
      }
      channel.onmessage = (message) => {
        if (!isSessionCurrent(generation)) {
          return
        }
        const event = JSON.parse(message.data) as Record<string, unknown>
        turnControllerRef.current?.handle(event)

        if (event.type === 'input_audio_buffer.speech_started') {
          const now = performance.now()
          if (now - speechStartedAtRef.current >= 350) {
            speechStartedAtRef.current = now
            setState('LISTENING')
            if (chargingSpeechPhaseRef.current !== null) clearChargingMapFocus()
          }
        } else if (event.type === 'response.created') {
          const createdResponse = event.response as { id?: string } | undefined
          if (
            chargingSpeechPhaseRef.current !== null &&
            chargingSpeechResponseIdRef.current === null &&
            typeof createdResponse?.id === 'string' &&
            turnControllerRef.current?.isResult(createdResponse.id)
          ) {
            chargingSpeechResponseIdRef.current = createdResponse.id
          }
          setState('PROCESSING')
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
          }, generation)
        } else if (event.type === 'output_audio_buffer.started') {
          setState('SPEAKING')
          if (
            chargingSpeechPhaseRef.current === 'amenities' &&
            event.response_id === chargingSpeechResponseIdRef.current
          ) {
            setChargingStopFocus(chargingAmenitiesFocusStopRef.current)
          }
        } else if (event.type === 'output_audio_buffer.cleared') {
          if (
            chargingSpeechPhaseRef.current !== null &&
            (event.response_id == null ||
              event.response_id === chargingSpeechResponseIdRef.current)
          ) {
            clearChargingMapFocus()
            setState('LISTENING')
          }
        } else if (event.type === 'error') {
          const eventError = event.error as { code?: string; message?: string } | undefined
          if (eventError?.code === 'response_cancel_not_active') return
          setError(
            eventError?.message ??
              'Realtime assistant failed to process the request.',
          )
          setState('ERROR')
        }
      }

      const offer = await peerConnection.createOffer()
      await peerConnection.setLocalDescription(offer)

      if (!isSessionCurrent(generation)) {
        throw new Error('Voice connection was stopped.')
      }

      const controller = new AbortController()
      connectionAbortRef.current = controller
      const timeout = window.setTimeout(() => controller.abort(), 20_000)
      const callStartedAt = performance.now()
      let callCompletedAt = callStartedAt
      try {
        recordTelemetry('sessionRequestStarted')
        const answer = await createRealtimeCall(offer.sdp ?? '', controller.signal)
        callCompletedAt = performance.now()
        recordTelemetry('sessionRequestCompleted')
        if (!isSessionCurrent(generation)) return

        await peerConnection.setRemoteDescription({
          type: 'answer',
          sdp: answer,
        })
        recordTelemetry('remoteDescriptionApplied')
        await waitForDataChannelOpen(channel, controller.signal)
      } finally {
        window.clearTimeout(timeout)
        if (connectionAbortRef.current === controller) {
          connectionAbortRef.current = null
        }
      }

      if (!isSessionCurrent(generation)) {
        throw new Error('Voice connection was stopped.')
      }
      await listeningJinglePlaybackRef.current
      if (!isSessionCurrent(generation)) return
      listeningJinglePlaybackRef.current = null
      feedbackAudioRef.current?.pause()
      stream.getAudioTracks().forEach((track) => {
        track.enabled = true
      })
      channelRef.current = channel
      setEnabled(true)
      recordTelemetry('assistantReady')
      console.info('realtime_connection_ms', {
        total: Math.round(performance.now() - connectionStartedAt),
        microphone: Math.round(microphoneReadyAt - connectionStartedAt),
        call: Math.round(callCompletedAt - callStartedAt),
        transport: Math.round(performance.now() - callCompletedAt),
      })
      window.dispatchEvent(
        new CustomEvent(REALTIME_CONNECTION_CONFIRMED_EVENT, {
          detail: { generation },
        }),
      )
      setState('LISTENING')
    } catch (connectionError) {
      const stoppedByUser = !isSessionCurrent(generation)
      if (isSessionCurrent(generation)) {
        startingRef.current = false
        turnControllerRef.current?.reset()
        turnControllerRef.current = null
        channelRef.current?.close()
        channelRef.current = null
        connectionRef.current?.close()
        connectionRef.current = null
        streamRef.current?.getTracks().forEach((track) => track.stop())
        streamRef.current = null
        audioRef.current?.pause()
        audioRef.current?.remove()
        audioRef.current = null
        feedbackAudioRef.current?.pause()
        listeningJinglePlaybackRef.current = null
      }
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

  useEffect(() => closeSession, [closeSession])

  function selectPoi(poiId: string) {
    const poi = poiResults.find((result) => result.id === poiId)
    if (!poi) {
      setSelectedPoi(null)
      setPoiActionState('REROUTE_FAILED')
      setError('That route suggestion is no longer available.')
      return
    }

    setSelectedPoi(poi)
    setSelectedBookingPoi(
      poi.category === 'hotel' || poi.category === 'restaurant' ? poi : null,
    )
    setPoiActionState('CONFIRMATION_PENDING')
    setError(null)

    if (startingRef.current) {
      const selectionPrompt =
        poi.category === 'hotel' || poi.category === 'restaurant'
          ? `I selected the ${poi.category} suggestion "${poi.name}" (POI ID: ${poi.id}). Store this selection and ask for any missing booking details. Do not book it yet.`
          : `I selected the suggested stop "${poi.name}" (POI ID: ${poi.id}). Explain the proposed detour and ask for my confirmation. Do not reroute yet.`
      sendEvent({
        type: 'conversation.item.create',
        item: {
          type: 'message',
          role: 'user',
          content: [
            {
              type: 'input_text',
              text: selectionPrompt,
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
    amenityResults,
    amenityMarkersVisible,
    amenitySearchState,
    amenitySearchContext,
    purchase,
    booking,
    driving,
    chargingStopConfirmed,
    chargingStopFocus,
    destinationFocus,
    selectedBookingPoi,
    telemetry,
    successFeedback,
    selectPoi,
    error,
    enable,
    disable: closeSession,
  }
}
