import type {
  BookingResponse,
  ConfirmChargingStopResponse,
  PurchaseVignetteResponse,
  ReturnToMainRouteResponse,
  RoutePoiResponse,
  RouteResponse,
  StartDrivingResponse,
  StopAmenitiesResponse,
} from '../types/contracts'

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

interface RealtimeSessionResponse {
  clientSecret: string
  model: string
}

interface PlanRouteToolResponse {
  route: RouteResponse
  routeId?: string | null
  searchId?: string | null
}

interface RerouteToolResponse {
  route: RouteResponse
}

export interface RealtimeToolError {
  code: string
  message: string
}

export class RealtimeToolRequestError extends Error {
  readonly code: string

  constructor(error: RealtimeToolError) {
    super(error.message)
    this.name = 'RealtimeToolRequestError'
    this.code = error.code
  }
}

async function throwToolError(response: Response, fallback: string): Promise<never> {
  const payload = (await response.json().catch(() => null)) as {
    error?: RealtimeToolError
  } | null
  if (payload?.error?.code && payload.error.message) {
    throw new RealtimeToolRequestError(payload.error)
  }

  throw new Error(fallback)
}

export function getRealtimeToolErrorMessage(code: string, fallback: string): string {
  const messages: Record<string, string> = {
    INVALID_POI_CATEGORY: 'That place category is not available for this route.',
    POI_UNAVAILABLE: 'I cannot search places along the route right now.',
    AMENITIES_UNAVAILABLE: 'I cannot search nearby amenities right now.',
    NO_SELECTED_STOP: 'I need a selected charging stop before searching nearby.',
    STALE_STOP_CONTEXT: 'That charging stop is no longer part of the active route.',
    STALE_STOP: 'That charging stop is no longer part of the active route.',
    STALE_ROUTE_CONTEXT: 'That route context is no longer current.',
    STALE_ROUTE: 'That route context is no longer current.',
    STALE_SEARCH_CONTEXT: 'That place search is no longer current.',
    STALE_SEARCH: 'That place search is no longer current.',
    STALE_POI_SELECTION: 'That suggestion is no longer available for this route.',
    REROUTE_UNAVAILABLE: 'I cannot change the route through that stop right now.',
    DUPLICATE_PURCHASE: 'That vignette purchase was already completed.',
    DUPLICATE_BOOKING: 'That booking was already completed.',
    MISSING_REQUIREMENT: 'There is no current vignette requirement to purchase.',
    MISSING_DETAILS: 'I need the remaining booking details before I can book it.',
    PURCHASE_UNAVAILABLE: 'I cannot complete the simulated purchase right now.',
    BOOKING_UNAVAILABLE: 'I cannot complete the simulated booking right now.',
    DRIVING_UNAVAILABLE: 'I cannot start driving mode right now.',
    NOT_IN_AMENITY_VIEW: 'There is no charger-focused view to leave right now.',
    VALIDATION_ERROR: 'I could not validate that assistant request.',
  }

  return messages[code] ?? fallback
}

export async function createRealtimeSession(): Promise<RealtimeSessionResponse> {
  const response = await fetch(`${API_BASE_URL}/api/assistant/realtime/session`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  })

  if (!response.ok) {
    throw new Error(`Realtime session failed with HTTP ${response.status}`)
  }

  const payload = (await response.json()) as RealtimeSessionResponse
  if (!payload.clientSecret) {
    throw new Error('Realtime session did not return a client secret.')
  }

  if (!payload.model) {
    throw new Error('Realtime session did not return a model.')
  }

  return payload
}

export async function planRouteWithTool(
  argumentsJson: string,
  signal?: AbortSignal,
): Promise<PlanRouteToolResponse> {
  const response = await fetch(
    `${API_BASE_URL}/api/assistant/realtime/tools/plan-route`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: argumentsJson,
      signal,
    },
  )

  if (!response.ok) {
    return throwToolError(response, 'The route request could not be completed.')
  }

  return (await response.json()) as PlanRouteToolResponse
}

export async function searchRoutePoiWithTool(
  argumentsJson: string,
  signal?: AbortSignal,
): Promise<RoutePoiResponse> {
  const response = await fetch(
    `${API_BASE_URL}/api/assistant/realtime/tools/search-route-poi`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: argumentsJson,
      signal,
    },
  )

  if (!response.ok) {
    return throwToolError(response, 'The place search could not be completed.')
  }

  return (await response.json()) as RoutePoiResponse
}

export async function searchStopAmenitiesWithTool(
  argumentsJson: string,
  signal?: AbortSignal,
): Promise<StopAmenitiesResponse> {
  const response = await fetch(
    `${API_BASE_URL}/api/assistant/realtime/tools/search-stop-amenities`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: argumentsJson,
      signal,
    },
  )

  if (!response.ok) {
    return throwToolError(response, 'The nearby amenity search could not be completed.')
  }

  return (await response.json()) as StopAmenitiesResponse
}

export function confirmChargingStopWithTool(
  argumentsJson: string,
  signal?: AbortSignal,
): Promise<ConfirmChargingStopResponse> {
  return callDay6Tool(
    'confirm-charging-stop',
    argumentsJson,
    'The charging stop could not be added right now.',
    signal,
  )
}

export async function rerouteWithTool(
  argumentsJson: string,
  signal?: AbortSignal,
): Promise<RerouteToolResponse> {
  const response = await fetch(
    `${API_BASE_URL}/api/assistant/realtime/tools/reroute-through-poi`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: argumentsJson,
      signal,
    },
  )

  if (!response.ok) {
    return throwToolError(response, 'The route change could not be completed.')
  }

  return (await response.json()) as RerouteToolResponse
}

async function callDay6Tool<T>(
  path: string,
  argumentsJson: string,
  fallback: string,
  signal?: AbortSignal,
): Promise<T> {
  const response = await fetch(`${API_BASE_URL}/api/assistant/realtime/tools/${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: argumentsJson,
    signal,
  })

  if (!response.ok) {
    return throwToolError(response, fallback)
  }

  return (await response.json()) as T
}

export function purchaseVignetteWithTool(
  argumentsJson: string,
  signal?: AbortSignal,
): Promise<PurchaseVignetteResponse> {
  return callDay6Tool(
    'purchase-vignette',
    argumentsJson,
    'The simulated vignette purchase could not be completed.',
    signal,
  )
}

export function bookHotelRoomWithTool(
  argumentsJson: string,
  signal?: AbortSignal,
): Promise<BookingResponse> {
  return callDay6Tool(
    'book-hotel-room',
    argumentsJson,
    'The simulated hotel booking could not be completed.',
    signal,
  )
}

export function bookRestaurantTableWithTool(
  argumentsJson: string,
  signal?: AbortSignal,
): Promise<BookingResponse> {
  return callDay6Tool(
    'book-restaurant-table',
    argumentsJson,
    'The simulated restaurant booking could not be completed.',
    signal,
  )
}

export function startDrivingWithTool(
  argumentsJson: string,
  signal?: AbortSignal,
): Promise<StartDrivingResponse> {
  return callDay6Tool(
    'start-driving',
    argumentsJson,
    'Driving mode could not be started.',
    signal,
  )
}

export function returnToMainRouteWithTool(
  argumentsJson: string,
  signal?: AbortSignal,
): Promise<ReturnToMainRouteResponse> {
  return callDay6Tool(
    'return-to-main-route',
    argumentsJson,
    'The main route view could not be restored.',
    signal,
  )
}