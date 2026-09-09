/**
 * Canonical Data Contracts: AI In-Car Concierge ("Suzanne")
 * Universal architecture: EV-focused, agnostic routing, voice-first HMI.
 */

export type RoutePriority = 'FASTEST' | 'CHEAPEST' | 'SCENIC' | 'BALANCED';

export type StopCategory = 'charging' | 'food' | 'rest' | 'toll' | 'vignette' | 'service';

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
  detourMinutes: number;
}

export interface RouteAlert {
  type: 'WEATHER' | 'TRAFFIC' | 'TOLL' | 'VEHICLE';
  locationName?: string;
  severity: 'INFO' | 'WARNING' | 'CRITICAL';
  message: string;                 // Concise driver text
}

export interface TripStats {
  totalDistanceKm: number;
  totalDurationMinutes: number;
  totalPriceEur: number;           // Aggregated estimates (tolls + charging)
}

export interface RouteResponse {
  origin: string;
  destination: string;
  stats: TripStats;
  geometry: [number, number][];    // Full route polyline coordinates [[lng, lat], ...]
  stops: StopPinpoint[];
  alerts: RouteAlert[];
}

export interface AssistantResponse {
  transcript: string;
  spokenResponse: string;          // Plain text fallback
  audioBase64?: string;            // MP3 audio bytes from OpenAI TTS
  route?: RouteResponse;           // Populated on Day 2; null on Day 1
  toastMessage?: string;           // e.g. "ROUTE: BUDAPEST (FASTEST)"
}