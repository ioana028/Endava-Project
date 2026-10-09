import type { RouteResponse } from '../../types/contracts'

export function compactRouteFacts(
  route: RouteResponse,
  context: { routeId?: string | null; searchId?: string | null } = {},
) {
  const formatDuration = (totalMinutes: number) => {
    const roundedMinutes = Math.round(totalMinutes)
    if (roundedMinutes < 60) {
      return `${roundedMinutes} minutes`
    }
    const hours = Math.round(roundedMinutes / 60)
    return `${hours} hour${hours === 1 ? '' : 's'}`
  }
  const chargingStop = route.chargingStop ?? route.stops.find((stop) => stop.mandatory)
  const chargingPlanConfirmed = Boolean(
    route.sessionFacts?.chargingPlanConfirmed || route.chargingPlan?.confirmed,
  )
  const telemetryRequiresCharging = route.telemetry
    ? route.stats.totalDistanceKm > route.telemetry.estimatedRangeKm
    : false
  const chargingRequired = Boolean(
    (chargingPlanConfirmed ? false : route.chargingRequired ?? Boolean(chargingStop))
    || (!chargingPlanConfirmed && telemetryRequiresCharging),
  )
  const routeWeatherAlert = route.alerts.find(
    (alert) => alert.type === 'WEATHER' && alert.locationName === 'Route average',
  )
  const weatherFacts = routeWeatherAlert?.message.match(
    /Current route conditions:\s*([^;]+);\s*average temperature about\s+(-?\d+(?:\.\d+)?)°C/i,
  )
  const routeWeatherSummary = routeWeatherAlert
    ? weatherFacts
      ? `${weatherFacts[1].trim()}, around ${Math.round(Number(weatherFacts[2]))}°C`
      : routeWeatherAlert.message
    : null
  const remainingRequirements = route.sessionFacts?.remainingRequirements ?? route.routeRequirements
  const vignetteCount = remainingRequirements.filter(
    (requirement) => requirement.kind === 'vignette',
  ).length
  const tollRequired = remainingRequirements.some(
    (requirement) => requirement.kind === 'toll',
  )
  const compactChargingPlan = route.chargingPlan?.confirmed
    ? {
        stops: route.chargingPlan.stops.map((stop, index) => ({
          order: index + 1,
          name: stop.name,
          chargingDurationMinutes: Math.round(stop.chargingDurationMinutes ?? 0),
          ...(stop.partner?.verified && stop.partner.benefit
            ? {
                partnerFact: {
                  benefit: stop.partner.benefit,
                  verified: true,
                },
              }
            : {}),
        })),
      }
    : null
  const preparedStops = route.chargingOptions?.filter(option => option.status !== 'confirmed') ?? []
  const chargingPlanReady = !chargingPlanConfirmed && preparedStops.length > 0

  return {
    status: 'success',
    routeStatus: route.routeStatus,
    origin: route.origin,
    destination: route.destination,
    distanceKm: Math.round(route.stats.totalDistanceKm),
    travelTime: formatDuration(route.stats.drivingDurationMinutes),
    ...(chargingRequired ? { chargingRequired: true } : {}),
    chargingPlanReady,
    ...(chargingPlanReady ? {
      preparedChargingStopCount: preparedStops.length,
      chargingAction: 'confirm_charging_stop',
    } : {}),
    routeWeatherSummary,
    ...(route.serviceReminder ? { serviceReminder: route.serviceReminder } : {}),
    ...(vignetteCount > 0 ? { vignetteCount } : {}),
    // Operational context is kept even though the spoken overview stays brief.
    routeRequirements: remainingRequirements.map(({ id, name, country, kind }) => ({ id, name, country, kind })),
    ...(tollRequired ? { tollRequired: true } : {}),
    ...(compactChargingPlan ? { chargingPlan: compactChargingPlan } : {}),
    ...(context.routeId ? { routeId: context.routeId } : {}),
    ...(context.searchId ? { searchId: context.searchId } : {}),
  }
}
