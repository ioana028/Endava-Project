import type { RouteResponse } from '../../../types/contracts'

export function toGooglePath(
  geometry: RouteResponse['geometry'],
): google.maps.LatLngLiteral[] {
  return geometry.map(([lng, lat]) => ({
    lat,
    lng,
  }))
}