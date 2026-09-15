import { useEffect, useRef, useState } from 'react'
import { importLibrary, setOptions } from '@googlemaps/js-api-loader'
import type { RouteResponse, StopPinpoint } from '../../../types/contracts'
import { toGooglePath } from '../utils/routeGeometry'

const browserKey = import.meta.env.VITE_GOOGLE_MAPS_BROWSER_KEY

function formatDuration(totalMinutes: number) {
  const roundedMinutes = Math.round(totalMinutes)
  const hours = Math.floor(roundedMinutes / 60)
  const minutes = roundedMinutes % 60

  if (hours === 0) {
    return `${minutes} min`
  }

  return minutes === 0 ? `${hours} h` : `${hours} h ${minutes} min`
}

if (browserKey) {
  setOptions({
    key: browserKey,
    v: 'weekly',
  })
}

interface RouteMapProps {
  route: RouteResponse
  poiResults?: StopPinpoint[]
  selectedPoiId?: string | null
  onPoiSelect?: (poiId: string) => void
}

export function RouteMap({
  route,
  poiResults = [],
  selectedPoiId = null,
  onPoiSelect,
}: RouteMapProps) {
  const mapElementRef = useRef<HTMLDivElement | null>(null)
  const mapRef = useRef<google.maps.Map | null>(null)
  const polylineRef = useRef<google.maps.Polyline | null>(null)
  const markersRef = useRef<google.maps.Marker[]>([])
  const durationOverlayRef = useRef<google.maps.OverlayView | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false

    polylineRef.current?.setMap(null)
    polylineRef.current = null
    markersRef.current.forEach((marker) => marker.setMap(null))
    markersRef.current = []
    durationOverlayRef.current?.setMap(null)
    durationOverlayRef.current = null
    mapRef.current = null

    async function renderMap() {
      if (!browserKey) {
        setError('Google Maps browser key is missing.')
        return
      }

      if (!mapElementRef.current || route.geometry.length === 0) {
        return
      }

      try {
        const { Map } = (await importLibrary('maps')) as google.maps.MapsLibrary

        class DurationOverlay extends google.maps.OverlayView {
          private readonly position: google.maps.LatLngLiteral
          private readonly text: string
          private container: HTMLDivElement | null = null
          private connector: HTMLDivElement | null = null
          private bubble: HTMLDivElement | null = null

          constructor(position: google.maps.LatLngLiteral, text: string) {
            super()
            this.position = position
            this.text = text
          }

          onAdd() {
            this.container = document.createElement('div')
            this.container.style.position = 'absolute'
            this.container.style.pointerEvents = 'none'

            this.connector = document.createElement('div')
            this.connector.style.position = 'absolute'
            this.connector.style.left = '0'
            this.connector.style.top = '18px'
            this.connector.style.width = '42px'
            this.connector.style.borderTop = '2px solid #16324f'

            this.bubble = document.createElement('div')
            this.bubble.textContent = this.text
            this.bubble.style.position = 'absolute'
            this.bubble.style.left = '42px'
            this.bubble.style.top = '0'
            this.bubble.style.padding = '7px 11px'
            this.bubble.style.borderRadius = '5px'
            this.bubble.style.background = '#16324f'
            this.bubble.style.border = '2px solid #ffffff'
            this.bubble.style.boxShadow = '0 2px 5px rgba(0, 0, 0, 0.3)'
            this.bubble.style.color = '#ffffff'
            this.bubble.style.font = '700 13px/1.2 system-ui, sans-serif'
            this.bubble.style.whiteSpace = 'nowrap'

            this.container.append(this.connector, this.bubble)
            this.getPanes()?.floatPane.appendChild(this.container)
          }

          draw() {
            const projection = this.getProjection()
            const pixel = projection.fromLatLngToDivPixel(this.position)

            if (!pixel || !this.container) {
              return
            }

            this.container.style.left = `${pixel.x}px`
            this.container.style.top = `${pixel.y - 18}px`
          }

          onRemove() {
            this.container?.remove()
            this.container = null
            this.connector = null
            this.bubble = null
          }
        }

        if (cancelled || !mapElementRef.current) {
          return
        }

        const path = toGooglePath(route.geometry)
        const map = new Map(mapElementRef.current, {
          center: path[0],
          zoom: 7,
          colorScheme: google.maps.ColorScheme.DARK,
          mapTypeControl: false,
          streetViewControl: false,
          fullscreenControl: false,
          styles: [
  // Keep the land flat and quiet.
  {
    featureType: 'landscape',
    elementType: 'geometry',
    stylers: [{ color: '#202a35' }],
  },
  {
    featureType: 'landscape.man_made',
    elementType: 'geometry',
    stylers: [{ visibility: 'off' }],
  },

  // Keep roads visible and readable.
  {
    featureType: 'road',
    elementType: 'geometry',
    stylers: [{ color: '#46515c' }],
  },
  {
    featureType: 'road',
    elementType: 'labels.text',
    stylers: [{ visibility: 'on' }],
  },
  {
    featureType: 'road',
    elementType: 'labels.text.fill',
    stylers: [{ color: '#d5dde5' }],
  },
  {
    featureType: 'road.highway',
    elementType: 'geometry',
    stylers: [{ color: '#657482' }],
  },
  {
    featureType: 'road.highway',
    elementType: 'geometry.stroke',
    stylers: [{ color: '#17212b' }],
  },

  // Keep water and its major labels.
  {
    featureType: 'water',
    elementType: 'geometry',
    stylers: [{ color: '#102b43' }],
  },
  {
    featureType: 'water',
    elementType: 'labels.text',
    stylers: [{ visibility: 'on' }],
  },
  {
    featureType: 'water',
    elementType: 'labels.text.fill',
    stylers: [{ color: '#8ec5df' }],
  },

  // Keep country, region, and city names.
  {
    featureType: 'administrative.country',
    elementType: 'labels.text',
    stylers: [{ visibility: 'on' }],
  },
  {
    featureType: 'administrative.province',
    elementType: 'labels.text',
    stylers: [{ visibility: 'on' }],
  },
  {
    featureType: 'administrative.locality',
    elementType: 'labels.text',
    stylers: [{ visibility: 'on' }],
  },

  // Keep borders visible.
  {
    featureType: 'administrative.country',
    elementType: 'geometry.stroke',
    stylers: [{ visibility: 'on' }, { color: '#8793a0' }, { weight: 1 }],
  },
  {
    featureType: 'administrative.province',
    elementType: 'geometry.stroke',
    stylers: [{ visibility: 'off' }, { color: '#596673' }, { weight: 1 }],
  },

  // Remove clutter, but do not hide administrative labels.
  {
    featureType: 'poi',
    stylers: [{ visibility: 'off' }],
  },
  {
    featureType: 'transit',
    stylers: [{ visibility: 'off' }],
  },
  {
    featureType: 'administrative.neighborhood',
    elementType: 'labels',
    stylers: [{ visibility: 'off' }],
  },
],
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

        const originMarker = new google.maps.Marker({
          map,
          position: path[0],
          title: route.origin,
          icon: {
            path: google.maps.SymbolPath.CIRCLE,
            scale: 8,
            fillColor: '#1677ff',
            fillOpacity: 1,
            strokeColor: '#ffffff',
            strokeWeight: 3,
          },
          zIndex: 3,
        })

        const destinationMarker = new google.maps.Marker({
          map,
          position: path[path.length - 1],
          title: route.destination,
          zIndex: 3,
        })

        const stopMarkers = route.stops.map(
          (stop) =>
            new google.maps.Marker({
              map,
              position: { lat: stop.coords[1], lng: stop.coords[0] },
              title: stop.name,
              label: stop.category === 'charging' ? 'C' : undefined,
              zIndex: 2,
            }),
        )

        const poiMarkers = poiResults.map(
          (poi) => {
            const marker = new google.maps.Marker({
              map,
              position: { lat: poi.coords[1], lng: poi.coords[0] },
              title: poi.name,
              icon: {
                path: google.maps.SymbolPath.CIRCLE,
                scale: poi.id === selectedPoiId ? 9 : 7,
                fillColor: poi.id === selectedPoiId ? '#f97316' : '#facc15',
                fillOpacity: 1,
                strokeColor: '#ffffff',
                strokeWeight: poi.id === selectedPoiId ? 3 : 2,
              },
              zIndex: poi.id === selectedPoiId ? 5 : 4,
              clickable: Boolean(onPoiSelect),
            })
            if (onPoiSelect) {
              marker.addListener('click', () => onPoiSelect(poi.id))
            }
            return marker
          },
        )

        const durationOverlay = new DurationOverlay(
          path[Math.floor(path.length / 2)],
          formatDuration(route.stats.totalDurationMinutes),
        )
        durationOverlay.setMap(map)

        markersRef.current = [
          originMarker,
          destinationMarker,
          ...stopMarkers,
          ...poiMarkers,
        ]
        durationOverlayRef.current = durationOverlay
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
      markersRef.current.forEach((marker) => marker.setMap(null))
      markersRef.current = []
      durationOverlayRef.current?.setMap(null)
      durationOverlayRef.current = null
      mapRef.current = null
    }
  }, [onPoiSelect, poiResults, route, selectedPoiId])

  if (error) {
    return <p role="alert">{error}</p>
  }

  if (route.geometry.length === 0) {
    return <p role="status">No route geometry is available.</p>
  }

  return <div ref={mapElementRef} className="route-map" />
}