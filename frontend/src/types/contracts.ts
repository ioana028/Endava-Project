/**
 * Canonical Data Contracts: AI In-Car Concierge ("Suzanne")
 * Universal architecture: EV-focused, agnostic routing, voice-first HMI.
 */

export type RoutePriority = 'FASTEST' | 'CHEAPEST' | 'SCENIC' | 'BALANCED';

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
  tag: string;                     // e.g., "Fast Charger · 250kW" or "Italian Dining"
  amenities?: string[];
  distanceMeters?: number;
  detourMinutes: number;
  chargingDurationMinutes?: number;
  mandatory?: boolean;
  partner?: {
    id: string;
    name: string;
    benefit?: string | null;
  } | null;
  partnerBenefit?: string | null;
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
  origin: string;
  destination: string;
  stats: TripStats;
  geometry: [number, number][];    // Full route polyline coordinates [[lng, lat], ...]
  stops: StopPinpoint[];
  alerts: RouteAlert[];
  chargingStop?: StopPinpoint | null;
  borderCrossings: BorderCrossing[];
  routeRequirements: RouteRequirement[];
}

export interface RoutePoiResponse {
  results: StopPinpoint[];
  routeId?: string | null;
  searchId?: string | null;
}

export interface StopAmenitiesResponse {
  selectedStopName: string;
  results: StopPinpoint[];
  radiusMeters: number;
  routeId: string;
  searchId: string;
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
  consumptionRateKwh: number;
  tyres: 'SUMMER' | 'WINTER' | 'ALL_SEASON';
  odometerKm: number;
}