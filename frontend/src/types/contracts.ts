/**
 * Canonical Data Contracts: AI In-Car Concierge ("Suzanne")
 * Universal architecture: EV-focused, agnostic routing, voice-first HMI.
 */

export type RoutePriority = 'FASTEST' | 'CHEAPEST' | 'SCENIC' | 'BALANCED';
export type RouteSessionStatus =
  | 'ROUTE_READY'
  | 'CHARGING_OPTIONS_READY'
  | 'CHARGING_CONFIRMED'
  | 'REROUTING'
  | 'DRIVING'
  | 'ERROR';

export type StopCategory =
  | 'charging'
  | 'food'
  | 'rest'
  | 'toll'
  | 'vignette'
  | 'service'
  | 'hotel'
  | 'restaurant'
  | 'attraction'
  | 'coffee'
  | 'toilets'
  | 'fuel'
  | 'shopping';

export interface VehicleState {
  vehicleId: string;
  propulsion: 'BEV';
  batteryPercent: number;          // 0 - 100
  estimatedRangeKm: number;
  consumptionRateKwh: number;      // kWh per 100km
  tyres: 'SUMMER' | 'WINTER' | 'ALL_SEASON';
  odometerKm: number;
}

export interface Coordinates {
  lng: number;
  lat: number;
}

export interface StopPinpoint {
  id: string;
  name: string;
  category: StopCategory;
  coords: [number, number];        // [lng, lat]
  rating?: number;
  userReviewCount?: number;
  tag: string;                     // e.g., "Fast Charger · 250kW" or "Italian Dining"
  details?: string | null;
  photoReference?: string | null;
  keywords?: string[];
  provider?: string | null;
  source?: string | null;
  amenities?: string[];
  distanceMeters?: number;
  detourMinutes: number;
  routeOffsetKm?: number;
  estimatedDrivingDetourMinutes?: number;
  chargingDurationMinutes?: number;
  connectorTypes?: string[];
  availability?: boolean | null;
  mandatory?: boolean;
  partner?: {
    id: string;
    name: string;
    benefit?: string | null;
    benefitScope?: string | null;
    benefitSource?: 'fixture' | 'configured' | 'provider' | null;
    verified?: boolean;
    status?: 'suggested' | 'confirmed' | 'completed';
  } | null;
  partnerBenefit?: string | null;
}

export interface PartnerFact {
  partnerId: string;
  brand: string;
  benefit?: string | null;
  benefitScope?: string | null;
  benefitSource: 'fixture' | 'configured' | 'provider';
  verified: boolean;
}

export interface TelemetryNarrationFacts {
  batteryPercent: number;
  estimatedRangeKm: number;
  maxChargedRangeKm: number;
  consumptionRateKwh: number;
  chargingFeasible?: boolean | null;
}

export interface RouteOpportunity {
  id: string;
  type: 'charging' | 'hotel' | 'restaurant' | 'amenity' | 'partner';
  stopId?: string | null;
  resultId?: string | null;
  partnerFact?: PartnerFact | null;
  reason: string;
  detourMinutes: number;
  requiresRouteConfirmation: boolean;
  status: 'suggested' | 'confirmed' | 'completed';
}

export interface ChargingPlan {
  stops: StopPinpoint[];
  complete: boolean;
  totalChargingMinutes: number;
  confirmed: boolean;
}

export interface ChargingOption {
  optionNumber: number;
  stop: StopPinpoint;
  status: 'suggested' | 'selected' | 'validated' | 'confirmed';
}

export interface RouteSessionFacts {
  chargingPlanConfirmed: boolean;
  confirmedChargingStopIds: string[];
  purchasedVignetteRequirementIds: string[];
  remainingRequirements: RouteRequirement[];
}

export interface RouteAlert {
  type: 'WEATHER' | 'TRAFFIC' | 'TOLL' | 'VEHICLE';
  locationName?: string;
  severity: 'INFO' | 'WARNING' | 'CRITICAL';
  message: string;                 // Concise driver text
}

export interface TripStats {
  totalDistanceKm: number;
  drivingDurationMinutes: number;
  totalDurationMinutes: number;
  totalPriceEur: number;           // Aggregated estimates (tolls + charging)
}

export interface BorderCrossing {
  fromCountry: string;
  toCountry: string;
}

export interface RouteRequirement {
  id: string;
  name: string;
  country: string;
  kind: 'toll' | 'vignette';
  mandatory: boolean;
}

export interface RouteResponse {
  sessionId?: string | null;
  routeStatus?: RouteSessionStatus;
  origin: string;
  originCoordinates?: Coordinates | null;
  destination: string;
  countries: string[];
  stats: TripStats;
  geometry: [number, number][];    // Full route polyline coordinates [[lng, lat], ...]
  stops: StopPinpoint[];
  alerts: RouteAlert[];
  chargingStop?: StopPinpoint | null;
  chargingRequired?: boolean;
  borderCrossings: BorderCrossing[];
  routeRequirements: RouteRequirement[];
  opportunities?: RouteOpportunity[];
  chargingOptions: ChargingOption[];
  chargingPlan?: ChargingPlan | null;
  sessionFacts?: RouteSessionFacts | null;
  telemetry?: TelemetryNarrationFacts | null;
}

export interface RoutePoiResponse {
  results: StopPinpoint[];
  opportunities?: RouteOpportunity[];
  routeId?: string | null;
  searchId?: string | null;
}

export interface StopAmenitiesResponse {
  selectedStopName: string;
  results: StopPinpoint[];
  opportunities?: RouteOpportunity[];
  radiusMeters: number;
  routeId: string;
  searchId?: string | null;
}

export interface ConfirmChargingStopResponse extends StopAmenitiesResponse {
  route: RouteResponse;
  chargingPlan?: ChargingPlan | null;
  sessionFacts?: RouteSessionFacts | null;
}

export interface PurchaseVignetteRequest {
  routeId: string;
  requirementId: string;
  confirmation: 'confirmed';
}

export interface PurchaseVignetteResponse {
  status: 'completed' | 'duplicate';
  sessionId?: string | null;
  transactionId: string;
  routeId: string;
  requirementId: string;
  walletStatus: 'ready' | 'processing' | 'completed' | 'declined' | 'duplicate';
  phoneConfirmationStatus: 'pending' | 'sent' | 'failed';
  amountEur: number;
  currency: 'EUR';
  sessionFacts?: RouteSessionFacts | null;
}

export type BookingType = 'hotel_room' | 'restaurant_table';

export interface BookingRequest {
  routeId: string;
  searchId: string;
  resultId: string;
  bookingType: BookingType;
  guests: number;
  date: string;
  time?: string | null;
  confirmation: 'confirmed';
}

export interface BookingResponse {
  status: 'completed' | 'duplicate' | 'pending' | 'failed';
  sessionId?: string | null;
  bookingId: string;
  resultId: string;
  routeId: string;
  bookingType: BookingType;
  guests: number;
  date: string;
  time?: string | null;
  walletStatus: 'ready' | 'processing' | 'completed' | 'declined' | 'duplicate';
  phoneConfirmationStatus: 'pending' | 'sent' | 'failed';
}

export interface StartDrivingResponse {
  status: 'active';
  sessionId?: string | null;
  routeId: string;
  remainingDistanceKm: number;
  remainingDurationMinutes: number;
  eta: string;
  nextStop?: Pick<StopPinpoint, 'id' | 'name' | 'category'> | null;
  chargingRequired: boolean;
}

export interface ReturnToMainRouteResponse {
  status: 'success';
  sessionId?: string | null;
  routeId: string;
}

export interface AssistantIntent {
  destination: string;
  priority: RoutePriority;
}

export interface AssistantResponse {
  transcript: string;
  intent: AssistantIntent;
  spokenResponse: string;          // Plain text fallback
  audioBase64?: string;            // MP3 audio bytes from OpenAI TTS
  route?: RouteResponse;           // Populated on Day 2; null on Day 1
  poiResults?: StopPinpoint[];
  toastMessage?: string;           // e.g. "ROUTE: BUDAPEST (FASTEST)"
}

export interface VehicleTelemetry {
  vehicleId: string;
  propulsion: 'BEV';
  batteryPercent: number;
  estimatedRangeKm: number;
  maxChargedRangeKm: number;
  consumptionRateKwh: number;
  connectorTypes: string[];
  maxChargingPowerKw: number;
  batteryCapacityKwh: number;
  tyres: 'SUMMER' | 'WINTER' | 'ALL_SEASON';
  odometerKm: number;
}