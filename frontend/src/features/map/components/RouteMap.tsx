import { useEffect, useRef, useState } from 'react'
import { importLibrary, setOptions } from '@googlemaps/js-api-loader'
import type { RouteResponse } from '../../../types/contracts'
import { toGooglePath } from '../utils/routeGeometry'

interface RouteMapProps {
  route: RouteResponse
}

export function RouteMap({ route }: RouteMapProps) {
  const mapElementRef = useRef<HTMLDivElement | null>(null)
  const mapRef = useRef<google.maps.Map | null>(null)
  const polylineRef = useRef<google.maps.Polyline | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false

    polylineRef.current?.setMap(null)
    polylineRef.current = null
    mapRef.current = null

    async function renderMap() {
      const apiKey = import.meta.env.VITE_GOOGLE_MAPS_BROWSER_KEY

      if (!apiKey) {
        setError('Google Maps browser key is missing.')
        return
      }

      if (!mapElementRef.current || route.geometry.length === 0) {
        return
      }

      try {
        setOptions({
          key: apiKey,
          v: 'weekly',
        })

        const { Map } = (await importLibrary('maps')) as google.maps.MapsLibrary

        if (cancelled || !mapElementRef.current) {
          return
        }

        const path = toGooglePath(route.geometry)
        const map = new Map(mapElementRef.current, {
          center: path[0],
          zoom: 7,
          mapTypeControl: false,
          streetViewControl: false,
          fullscreenControl: false,
        })
        mapRef.current = map

        const bounds = new google.maps.LatLngBounds()

        for (const point of path) {
          bounds.extend(point)
        }

        map.fitBounds(bounds, 48)

        polylineRef.current = new google.maps.Polyline({
          map,
          path,
          strokeColor: '#0b57d0',
          strokeOpacity: 0.95,
          strokeWeight: 6,
        })
      } catch {
        if (!cancelled) {
          setError('Unable to load Google Maps.')
        }
      }
    }

    void renderMap()

    return () => {
      cancelled = true
      polylineRef.current?.setMap(null)
      polylineRef.current = null
      mapRef.current = null
    }
  }, [route])

  if (error) {
    return <p role="alert">{error}</p>
  }

  if (route.geometry.length === 0) {
    return <p role="status">No route geometry is available.</p>
  }

  return <div ref={mapElementRef} className="route-map" />
}