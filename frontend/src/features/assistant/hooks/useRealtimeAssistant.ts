import { useEffect, useRef, useState } from 'react'
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
  createRealtimeSession,
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

function compactRouteFacts(
  route: RouteResponse,
  context: { routeId?: string | null; searchId?: string | null } = {},
) {
  const formatDuration = (totalMinutes: number) => {
    const roundedMinutes = Math.round(totalMinutes)
    const hours = Math.floor(roundedMinutes / 60)
    const minutes = roundedMinutes % 60
    return hours === 0
      ? `${minutes} minutes`
      : minutes === 0
        ? `${hours} hours`
        : `${hours} hours and ${minutes} minutes`
  }
  const chargingStop = route.chargingStop ?? route.stops.find((stop) => stop.mandatory)
  const telemetryRequiresCharging = route.telemetry
    ? route.stats.totalDistanceKm > route.telemetry.estimatedRangeKm
    : false
  const unconfirmedChargingMinutes = chargingStop?.chargingDurationMinutes ?? 0
  const initialTotalDurationMinutes = Math.max(
    route.stats.drivingDurationMinutes,
    route.stats.totalDurationMinutes - unconfirmedChargingMinutes,
  )
  const partnerFacts = route.stops
    .map((stop) => stop.partner)
    .filter(
      (partner): partner is NonNullable<StopPinpoint['partner']> =>
        Boolean(partner?.name && partner.verified && partner.benefit),
    )
    .map((partner) => ({
      partnerId: partner.id,
      brand: partner.name,
      benefit: partner.benefit,
      ...(partner.benefitScope ? { benefitScope: partner.benefitScope } : {}),
      ...(partner.benefitSource ? { benefitSource: partner.benefitSource } : {}),
      verified: true,
    }))

  const compactChargingPlan = route.chargingPlan
    ? {
        complete: route.chargingPlan.complete,
        confirmed: route.chargingPlan.confirmed,
        totalChargingMinutes: Math.round(route.chargingPlan.totalChargingMinutes),
        stops: route.chargingPlan.stops.map((stop, index) => ({
          order: index + 1,
          id: stop.id,
          name: stop.name,
          chargingDurationMinutes: Math.round(stop.chargingDurationMinutes ?? 0),
          ...(stop.partner?.verified && stop.partner.benefit
            ? {
                partnerFact: {
                  partnerId: stop.partner.id,
                  brand: stop.partner.name,
                  benefit: stop.partner.benefit,
                  verified: true,
                },
              }
            : {}),
        })),
      }
    : null

  return {
    status: 'success',
    origin: route.origin,
    destination: route.destination,
    ...(route.countries.length > 0 ? { countries: route.countries } : {}),
    distanceKm: Math.round(route.stats.totalDistanceKm),
    travelTime: formatDuration(route.stats.drivingDurationMinutes),
    drivingDurationMinutes: Math.round(route.stats.drivingDurationMinutes),
    totalDurationMinutes: Math.round(initialTotalDurationMinutes),
    chargingRequired: Boolean(
      (route.sessionFacts?.chargingPlanConfirmed ? false : route.chargingRequired ?? Boolean(chargingStop))
      || (!route.sessionFacts?.chargingPlanConfirmed && telemetryRequiresCharging),
    ),
    vignetteRequired: route.sessionFacts?.remainingRequirements?.some(
      (requirement) => requirement.kind === 'vignette',
    ) ?? route.routeRequirements.some((requirement) => requirement.kind === 'vignette'),
    ...(route.opportunities?.length
      ? {
          opportunities: route.opportunities.map((opportunity) => ({
            id: opportunity.id,
            type: opportunity.type,
            ...(opportunity.stopId ? { stopId: opportunity.stopId } : {}),
            ...(opportunity.resultId ? { resultId: opportunity.resultId } : {}),
            reason: opportunity.reason,
            detourMinutes: opportunity.detourMinutes,
            requiresRouteConfirmation: opportunity.requiresRouteConfirmation,
            status: opportunity.status,
            ...(opportunity.partnerFact?.verified
              ? { partnerFact: opportunity.partnerFact }
              : {}),
          })),
        }
      : {}),
    ...(route.chargingOptions.length > 0
      ? {
          chargingOptions: route.chargingOptions.map((option) => ({
            optionNumber: option.optionNumber,
            name: option.stop.name,
            id: option.stop.id,
            chargingDurationMinutes: Math.round(option.stop.chargingDurationMinutes ?? 0),
            detourMinutes: option.stop.detourMinutes,
            status: option.status,
          })),
        }
      : {}),
    ...(partnerFacts.length > 0 ? { partnerFacts } : {}),
    ...(compactChargingPlan ? { chargingPlan: compactChargingPlan } : {}),
    ...(route.sessionFacts ? { sessionFacts: route.sessionFacts } : {}),
    ...(route.alerts.length
      ? {
          alerts: route.alerts.map((alert) => ({
            type: alert.type,
            locationName: alert.locationName,
            severity: alert.severity,
            message: alert.message,
          })),
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
      ? {
          routeRequirements: route.routeRequirements.map((requirement) => ({
            id: requirement.id,
            name: requirement.name,
            kind: requirement.kind,
            country: requirement.country,
          })),
        }
      : {}),
    ...(context.routeId ? { routeId: context.routeId } : {}),
    ...(context.searchId ? { searchId: context.searchId } : {}),
  }
}

function compactPoiFacts(
  stop: StopPinpoint,
  context: { routeId?: string | null; searchId?: string | null },
) {
  const partnerFact = stop.partner?.verified && stop.partner.benefit
    ? {
        partnerId: stop.partner.id,
        brand: stop.partner.name,
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
    ...(stop.photoReference ? { photoReference: stop.photoReference } : {}),
    ...(stop.keywords?.length ? { keywords: stop.keywords.slice(0, 3) } : {}),
    ...(stop.provider ? { provider: stop.provider } : {}),
    ...(stop.source ? { source: stop.source } : {}),
    ...(stop.amenities?.length ? { amenities: stop.amenities } : {}),
    ...(stop.distanceMeters !== undefined ? { distanceMeters: stop.distanceMeters } : {}),
    ...(stop.routeOffsetKm !== undefined ? { routeOffsetKm: stop.routeOffsetKm } : {}),
    ...(stop.estimatedDrivingDetourMinutes !== undefined
      ? { estimatedDrivingDetourMinutes: stop.estimatedDrivingDetourMinutes }
      : {}),
    ...(stop.estimatedDrivingDetourMinutes !== undefined
      ? { detourMinutes: stop.estimatedDrivingDetourMinutes }
      : {}),
    ...(partnerFact ? { partnerFact } : {}),
    ...(context.routeId ? { routeId: context.routeId } : {}),
    ...(context.searchId ? { searchId: context.searchId } : {}),
  }
}

function compactAmenityFacts(stop: StopPinpoint) {
  const partnerFact = stop.partner?.verified && stop.partner.benefit
    ? {
        partnerId: stop.partner.id,
        brand: stop.partner.name,
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
    ...(stop.partner?.name ? { providerBrand: stop.partner.name } : {}),
    ...(stop.partnerBenefit ? { partnerBenefit: stop.partnerBenefit } : {}),
    ...(partnerFact ? { partnerFact } : {}),
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

async function waitForDataChannelOpen(channel: RTCDataChannel) {
  if (channel.readyState === 'open') {
    return
  }

  await new Promise<void>((resolve, reject) => {
    const timeout = window.setTimeout(() => {
      channel.removeEventListener('open', onOpen)
      reject(new Error('Timed out while opening the voice data channel.'))
    }, 15_000)

    function onOpen() {
      window.clearTimeout(timeout)
      channel.removeEventListener('open', onOpen)
      resolve()
    }

    channel.addEventListener('open', onOpen)
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
  const [successFeedback, setSuccessFeedback] = useState<SuccessFeedback | null>(null)
  const [selectedBookingPoi, setSelectedBookingPoi] = useState<StopPinpoint | null>(null)
  const [telemetry, setTelemetry] = useState<RealtimeTelemetry>({})
  const [error, setError] = useState<string | null>(null)
  const connectionRef = useRef<RTCPeerConnection | null>(null)
  const channelRef = useRef<RTCDataChannel | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const feedbackAudioRef = useRef<HTMLAudioElement | null>(null)
  const connectionAbortRef = useRef<AbortController | null>(null)
  const toolAbortRef = useRef<AbortController | null>(null)
  const toolCallInFlightRef = useRef(false)
  const pendingRouteRef = useRef<{
    route: RouteResponse
    priority: AssistantResponse['intent']['priority']
  } | null>(null)
  const activePriorityRef = useRef<AssistantResponse['intent']['priority']>('BALANCED')
  const assistantTranscriptRef = useRef('')
  const startingRef = useRef(false)
  const sessionGenerationRef = useRef(0)
  const toolRequestIdRef = useRef(0)
  const successFeedbackTimerRef = useRef<number | null>(null)
  const bookingPanelTimerRef = useRef<number | null>(null)
  const speechStartedAtRef = useRef(0)

  function recordTelemetry(name: keyof RealtimeTelemetry) {
    setTelemetry((current) => ({ ...current, [name]: performance.now() }))
  }

  function sendEvent(event: Record<string, unknown>) {
    channelRef.current?.send(JSON.stringify(event))
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

  function closeSession() {
    sessionGenerationRef.current += 1
    startingRef.current = false
    connectionAbortRef.current?.abort()
    connectionAbortRef.current = null
    toolAbortRef.current?.abort()
    toolAbortRef.current = null
    toolRequestIdRef.current += 1
    if (successFeedbackTimerRef.current !== null) {
      window.clearTimeout(successFeedbackTimerRef.current)
      successFeedbackTimerRef.current = null
    }
    setSuccessFeedback(null)
    pendingRouteRef.current = null
    setChargingStopFocus(null)
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
    ) {
      return
    }

    setState('PROCESSING')
    toolCallInFlightRef.current = true
    recordTelemetry('toolCallStarted')
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
        if (!isSessionCurrent(generation) || requestId !== toolRequestIdRef.current) {
          return
        }

        setPoiResults(result.results)
        setAmenityResults([])
        setAmenitySearchContext(null)
        setAmenitySearchState('IDLE')
        setSelectedPoi(null)
        setChargingStopFocus(null)
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
              'Acknowledge that the place search completed, then give the returned results briefly. For attractions, mention what can be seen or done from details or tag, and include the rating and review count when returned. Use only returned facts and never invent review content. Never leave the driver without a spoken response.',
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

        pendingRouteRef.current = null
        setResponse((current) =>
          current
            ? { ...current, route: result.route }
            : createRouteResponse(result.route, activePriorityRef.current),
        )
        setChargingStopConfirmed(true)
        setChargingStopFocus(
          result.route.chargingStop
            ?? result.route.stops.find((stop) => stop.category === 'charging')
            ?? null,
        )
        setAmenityResults(result.results)
        setPoiResults([])
        setSelectedPoi(null)
        setAmenitySearchContext({
          selectedStopName: result.selectedStopName,
          radiusMeters: result.radiusMeters,
          routeId: result.routeId,
          searchId: result.searchId ?? null,
        })
        setAmenitySearchState(result.results.length ? 'SUCCESS' : 'EMPTY')
        setError(null)
        sendEvent({
          type: 'conversation.item.create',
          item: {
            type: 'function_call_output',
            call_id: event.call_id,
            output: JSON.stringify({
              status: 'success',
              chargingStopAdded: result.selectedStopName,
              chargingPartnerFacts: result.route.stops
                .filter((stop) => stop.category === 'charging' && stop.partner?.benefit)
                .map((stop) => ({
                  stopName: stop.name,
                  brand: stop.partner?.name,
                  benefit: stop.partner?.benefit ?? stop.partnerBenefit,
                  benefitScope: stop.partner?.benefitScope,
                  benefitSource: stop.partner?.benefitSource,
                  verified: stop.partner?.verified ?? false,
                })),
              chargingPlan: result.chargingPlan ?? result.route.chargingPlan
                ? {
                    complete: (result.chargingPlan ?? result.route.chargingPlan)?.complete,
                    confirmed: (result.chargingPlan ?? result.route.chargingPlan)?.confirmed,
                    totalChargingMinutes: Math.round((result.chargingPlan ?? result.route.chargingPlan)?.totalChargingMinutes ?? 0),
                    stops: (result.chargingPlan ?? result.route.chargingPlan)?.stops.map((stop, index) => ({
                      order: index + 1,
                      id: stop.id,
                      name: stop.name,
                      chargingDurationMinutes: Math.round(stop.chargingDurationMinutes ?? 0),
                    })),
                  }
                : undefined,
              sessionFacts: result.sessionFacts ?? result.route.sessionFacts,
              nearbyAmenities: result.results.map(compactAmenityFacts),
              nearbyPartnerFacts: result.results
                .filter((amenity) => amenity.partner?.verified && amenity.partner.benefit)
                .map((amenity) => ({
                  placeName: amenity.name,
                  brand: amenity.partner?.name,
                  benefit: amenity.partner?.benefit,
                  verified: true,
                })),
            }),
          },
        })
        sendEvent({
          type: 'response.create',
          response: {
            instructions:
              'Say the station name once, then its returned charging time and any route time added. If it has a verified partner benefit, say: "They are a verified partner of ours offering [benefit]." Do not repeat the station name, network name, verification, or benefit. Mention nearby amenities only briefly and never claim the route was replanned.',
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
          setAmenityResults([])
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
                  ? 'Say that the vignette is handled and the details were sent to the phone app. Never speak the transaction ID, requirement ID, or any internal identifier.'
                  : event.name === 'book_hotel_room' || event.name === 'book_restaurant_table'
                    ? 'Say that the booking was completed and the details were sent to the phone app. Never speak the booking ID, result ID, route ID, or any internal identifier.'
                    : 'Acknowledge the successful action clearly and briefly, then state only the useful returned result. Never speak internal IDs or reference codes.',
          },
        })
        return
      }

      if (event.name === 'search_stop_amenities') {
        setAmenitySearchState('LOADING')
        const result = await searchStopAmenitiesWithTool(
          event.arguments,
          toolController.signal,
        )
        if (!isSessionCurrent(generation) || requestId !== toolRequestIdRef.current) {
          return
        }

        setAmenityResults(result.results)
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
              'Acknowledge the amenity search and briefly name the returned nearby places, including their categories and distances when available. If there are no results, say so clearly.',
          },
        })
        return
      }

      if (event.name === 'reroute_through_poi') {
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
        setChargingStopFocus(reroutedChargingStop ?? null)
        setPoiActionState('REROUTE_SUCCESS')
        let reroutedAmenities: StopPinpoint[] = []
        if (reroutedChargingStop && result.routeId) {
          const amenityResult = await searchStopAmenitiesWithTool(
            JSON.stringify({
              stopId: reroutedChargingStop.id,
              routeId: result.routeId,
            }),
            toolController.signal,
          )
          if (isSessionCurrent(generation) && requestId === toolRequestIdRef.current) {
            reroutedAmenities = amenityResult.results
            setAmenityResults(amenityResult.results)
            setAmenitySearchContext({
              selectedStopName: amenityResult.selectedStopName,
              radiusMeters: amenityResult.radiusMeters,
              routeId: amenityResult.routeId,
              searchId: amenityResult.searchId ?? null,
            })
            setAmenitySearchState(amenityResult.results.length ? 'SUCCESS' : 'EMPTY')
          }
        }
        pendingRouteRef.current = {
          route: result.route,
          priority: activePriorityRef.current,
        }
        sendEvent({
          type: 'conversation.item.create',
          item: {
            type: 'function_call_output',
            call_id: event.call_id,
            output: JSON.stringify({
              ...compactRouteFacts(result.route, {
                ...(result.routeId ? { routeId: result.routeId } : {}),
              }),
              ...(reroutedAmenities.length
                ? { nearbyAmenities: reroutedAmenities.map(compactAmenityFacts) }
                : {}),
            }),
          },
        })
        sendEvent({
          type: 'response.create',
          response: {
            instructions:
              'Acknowledge that the selected place or places were added in one route change, then briefly state the returned route facts. Never leave the driver without a spoken response.',
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
      setAmenitySearchContext(null)
      setAmenitySearchState('IDLE')
      setPurchase(null)
      setBooking(null)
      setDriving(null)
      setChargingStopConfirmed(false)
      setChargingStopFocus(null)
      setSelectedBookingPoi(null)
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
              'Reply in exactly one natural sentence using this shape: "Okay, your route to [destination] will take [travelTime] and require [only the returned vignette and charging requirements]; would you like me to help with that?" Mention only returned requirements, omit the final question when none require action, never mention telemetry, weather, opportunities, or a charger name before confirmation, and do not repeat the acknowledgement.',
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
      if (isSessionCurrent(generation)) {
        toolCallInFlightRef.current = false
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
    sessionGenerationRef.current = generation
    recordTelemetry('startPressed')
    setError(null)
    setState('CONNECTING')

    try {
      recordTelemetry('sessionRequestStarted')
      recordTelemetry('microphoneRequested')
      const sessionPromise = createRealtimeSession().then((session) => {
        if (isSessionCurrent(generation)) {
          recordTelemetry('sessionRequestCompleted')
        }
        return session
      })
      const microphonePromise = navigator.mediaDevices
        .getUserMedia({ audio: true })
        .then((stream) => {
          if (isSessionCurrent(generation)) {
            recordTelemetry('microphoneGranted')
          }
          return stream
        })
      const [sessionResult, microphoneResult] = await Promise.allSettled([
        sessionPromise,
        microphonePromise,
      ])
      if (microphoneResult.status === 'fulfilled' && sessionResult.status === 'rejected') {
        microphoneResult.value.getTracks().forEach((track) => track.stop())
      }
      if (sessionResult.status === 'rejected') {
        throw sessionResult.reason
      }
      if (microphoneResult.status === 'rejected') {
        throw microphoneResult.reason
      }
      if (!isSessionCurrent(generation)) {
        microphoneResult.value.getTracks().forEach((track) => track.stop())
        return
      }

      const session = sessionResult.value
      const stream = microphoneResult.value
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
      channel.onopen = () => {
        if (isSessionCurrent(generation)) {
          recordTelemetry('dataChannelOpened')
        }
      }
      channel.onmessage = (message) => {
        if (!isSessionCurrent(generation)) {
          return
        }
        const event = JSON.parse(message.data) as Record<string, unknown>

        if (event.type === 'input_audio_buffer.speech_started') {
          const now = performance.now()
          if (now - speechStartedAtRef.current >= 350) {
            speechStartedAtRef.current = now
            setState('LISTENING')
          }
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
          }, generation)
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
          setState(toolCallInFlightRef.current ? 'PROCESSING' : 'LISTENING')
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

      if (!isSessionCurrent(generation)) {
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
        recordTelemetry('remoteDescriptionApplied')
        await waitForDataChannelOpen(channel)
      } finally {
        window.clearTimeout(timeout)
        if (connectionAbortRef.current === controller) {
          connectionAbortRef.current = null
        }
      }

      if (!isSessionCurrent(generation)) {
        throw new Error('Voice connection was stopped.')
      }
      channelRef.current = channel
      const feedbackAudio = new Audio('/audio/listening-jingle.mp3')
      feedbackAudioRef.current = feedbackAudio
      void feedbackAudio.play().catch(() => undefined)
      setEnabled(true)
      recordTelemetry('assistantReady')
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
        channelRef.current?.close()
        connectionRef.current?.close()
        streamRef.current?.getTracks().forEach((track) => track.stop())
        streamRef.current = null
        audioRef.current?.pause()
        audioRef.current?.remove()
        audioRef.current = null
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
    amenitySearchState,
    amenitySearchContext,
    purchase,
    booking,
    driving,
    chargingStopConfirmed,
    chargingStopFocus,
    selectedBookingPoi,
    telemetry,
    successFeedback,
    selectPoi,
    error,
    enable,
    disable: closeSession,
  }
}