import type { RouteResponse } from '../../types/contracts'

export const VIGNETTE_RESULT_INSTRUCTIONS =
  'Give one concise purchase outcome. For status completed and phoneConfirmationStatus simulated_sent, say "Your vignette is purchased, and confirmation has been sent to your phone." The phone delivery is presentation-only; do not describe it as simulated in speech. If phoneConfirmationStatus is absent, say only "Your vignette is purchased." For duplicate, say "Your vignette was already purchased." Do not imply a new purchase or another notification for a duplicate. Never separately narrate walletStatus, payment status, route requirements, amounts, or IDs. Do not add an acknowledgement or route summary. Do not claim success for any other status.'

export const AMENITIES_RESULT_INSTRUCTIONS =
  'This is the amenities-only continuation, not a route or charging summary. Say exactly one short sentence beginning "Nearby you have" about up to three distinct nearbyAmenities in the preceding charging result. Mention only those places and their own verified partner benefits. A charging station benefit is not an amenity benefit: never repeat the charger name, its benefit, charging duration, route duration, destination, weather, requirements, or a route summary. No preamble or follow-up question. If empty, say "I could not find nearby amenities." If amenitiesStatus is unavailable, say "I could not check nearby amenities right now." Do not claim amenities were added to the route.'

export const POI_UPDATE_INSTRUCTIONS =
  'Briefly confirm the addedPlaces and report only travelTimeChangeMinutes: positive means minutes added, negative means minutes saved, zero means no extra driving time. If absent, omit the time estimate. This is driving time, not time spent visiting the attraction. Mention newly required motorway requirements only from newRequirements, or charging feasibility only if chargingFeasibilityChanged is present. Never repeat the complete route summary, total travel time, weather, existing charging details, partner benefits, or unchanged requirements. Use at most two short sentences and no follow-up question.'

/** Keep operational route IDs elsewhere; narration receives only the change. */
export function compactPoiUpdateFacts(previous: RouteResponse | undefined, next: RouteResponse) {
  const previousStopIds = new Set(previous?.stops.map(stop => stop.id) ?? [])
  const previousRequirements = new Set(previous?.routeRequirements.map(item => item.id) ?? [])
  const before = previous?.stats.drivingDurationMinutes
  const after = next.stats.drivingDurationMinutes
  const previousFeasibility = previous?.telemetry?.chargingFeasible
  const nextFeasibility = next.telemetry?.chargingFeasible
  return {
    status: 'success',
    addedPlaces: next.stops.filter(stop => !previousStopIds.has(stop.id))
      .map(({ name, category }) => ({ name, category })),
    ...(typeof before === 'number' && Number.isFinite(before) && Number.isFinite(after)
      ? { travelTimeChangeMinutes: Math.round(after - before) } : {}),
    newRequirements: previous
      ? next.routeRequirements.filter(item => !previousRequirements.has(item.id))
        .map(({ name, country, kind }) => ({ name, country, kind })) : [],
    ...(typeof previousFeasibility === 'boolean' && typeof nextFeasibility === 'boolean'
      && previousFeasibility !== nextFeasibility
      ? { chargingFeasibilityChanged: nextFeasibility } : {}),
  }
}
