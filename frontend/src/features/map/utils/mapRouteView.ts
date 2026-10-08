import type { RouteResponse, StopPinpoint } from '../../../types/contracts'

export type MapStop = Pick<StopPinpoint, 'id' | 'name' | 'category' | 'coords'>
export interface MapRouteView {
  origin: string
  destination: string
  geometry: RouteResponse['geometry']
  stops: MapStop[]
  chargingStop?: MapStop | null
  stats: Pick<RouteResponse['stats'], 'drivingDurationMinutes' | 'totalDurationMinutes'>
}

/** Only map-visible facts participate; wallet/session metadata cannot replay effects. */
export function serializeMapRoute(route: RouteResponse | undefined): string | undefined {
  if (!route) return undefined
  const stopView = ({ id, name, category, coords }: StopPinpoint): MapStop => ({ id, name, category, coords })
  return JSON.stringify({
    origin: route.origin,
    destination: route.destination,
    geometry: route.geometry,
    stops: route.stops.map(stopView),
    chargingStop: route.chargingStop ? stopView(route.chargingStop) : null,
    stats: {
      drivingDurationMinutes: route.stats.drivingDurationMinutes,
      totalDurationMinutes: route.stats.totalDurationMinutes,
    },
  } satisfies MapRouteView)
}

export function routePathChanged(previous: MapRouteView | null, next: MapRouteView): boolean {
  return previous === null || JSON.stringify([previous.origin, previous.destination, previous.geometry])
    !== JSON.stringify([next.origin, next.destination, next.geometry])
}
