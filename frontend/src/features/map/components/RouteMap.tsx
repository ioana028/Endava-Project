import { useEffect, useRef, useState } from 'react'
import { importLibrary, setOptions } from '@googlemaps/js-api-loader'
import type { RoutePriority, RouteResponse, StopPinpoint } from '../../../types/contracts'
import attractionPin from '../../../assets/attractionpin.png'
import chargingPin from '../../../assets/chargingpin.png'
import destinationPin from '../../../assets/destinationpin.png'
import foodPin from '../../../assets/foodpin.png'
import hotelPin from '../../../assets/hotelpin.png'
import servicePin from '../../../assets/servicepin.png'
import { toGooglePath } from '../utils/routeGeometry'

const browserKey = import.meta.env.VITE_GOOGLE_MAPS_BROWSER_KEY
const mapId = import.meta.env.VITE_GOOGLE_MAPS_MAP_ID

function formatDuration(totalMinutes: number) {
  const roundedMinutes = Math.round(totalMinutes)
  const hours = Math.floor(roundedMinutes / 60)
  const minutes = roundedMinutes % 60

  if (hours === 0) {
    return `${minutes} min`
  }

  return minutes === 0 ? `${hours} h` : `${hours} h ${minutes} min`
}

function getCalloutPosition(
  path: google.maps.LatLngLiteral[],
  markers: StopPinpoint[],
) {
  if (path.length < 2 || markers.length === 0) {
    return path[Math.floor(path.length / 2)]
  }

  const candidates = Array.from({ length: 11 }, (_, index) => {
    const progress = 0.15 + index * 0.07
    return path[Math.min(path.length - 1, Math.floor((path.length - 1) * progress))]
  })

  return candidates.reduce((best, candidate) => {
    const candidateScore = markerClearanceScore(candidate, markers)
    const bestScore = markerClearanceScore(best, markers)
    return candidateScore > bestScore ? candidate : best
  })
}

function markerClearanceScore(
  point: google.maps.LatLngLiteral,
  markers: StopPinpoint[],
) {
  const latitudeScale = Math.cos((point.lat * Math.PI) / 180)

  return Math.min(
    ...markers.map((marker) => {
      const longitudeDistance = (point.lng - marker.coords[0]) * latitudeScale
      const latitudeDistance = point.lat - marker.coords[1]
      return longitudeDistance ** 2 + latitudeDistance ** 2
    }),
  )
}

function routeHeading(path: google.maps.LatLngLiteral[]) {
  if (path.length < 2) {
    return 0
  }

  const from = path[0]
  const to = path[1]
  const latitude = ((from.lat + to.lat) / 2) * Math.PI / 180
  const longitude = (to.lng - from.lng) * Math.cos(latitude)
  const north = to.lat - from.lat
  return (Math.atan2(longitude, north) * 180 / Math.PI + 360) % 360
}

if (browserKey) {
  setOptions({
    key: browserKey,
    v: 'weekly',
  })
}

interface RouteMapProps {
  route?: RouteResponse
  poiResults?: StopPinpoint[]
  amenityResults?: StopPinpoint[]
  amenityFocusName?: string | null
  drivingActive?: boolean
  showChargingStop?: boolean
  routePriority?: RoutePriority
  selectedPoiId?: string | null
  onPoiSelect?: (poiId: string) => void
}

export function RouteMap({
  route,
  poiResults = [],
  amenityResults = [],
  amenityFocusName = null,
  drivingActive = false,
  showChargingStop = true,
  routePriority = 'BALANCED',
  selectedPoiId = null,
  onPoiSelect,
}: RouteMapProps) {
  const mapElementRef = useRef<HTMLDivElement | null>(null)
  const mapRef = useRef<google.maps.Map | null>(null)
  const polylineRef = useRef<google.maps.Polyline | null>(null)
  const markersRef = useRef<google.maps.Marker[]>([])
  const poiMarkersRef = useRef<google.maps.Marker[]>([])
  const amenityMarkersRef = useRef<google.maps.Marker[]>([])
  const poiResultsRef = useRef(poiResults)
  const durationOverlayRef = useRef<google.maps.OverlayView | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [mapReady, setMapReady] = useState(false)

  poiResultsRef.current = poiResults

  function disposeMap() {
    const map = mapRef.current
    if (map && typeof google !== 'undefined') {
      google.maps.event.clearInstanceListeners(map)
      map.unbindAll()
      map.getDiv().replaceChildren()
    }
    mapRef.current = null
  }

  function disposeMarker(marker: google.maps.Marker) {
    if (typeof google !== 'undefined') {
      google.maps.event.clearInstanceListeners(marker)
    }
    marker.setMap(null)
  }

  useEffect(() => {
    let cancelled = false

    polylineRef.current?.setMap(null)
    polylineRef.current = null
    disposeMap()
    markersRef.current.forEach(disposeMarker)
    markersRef.current = []
    poiMarkersRef.current.forEach(disposeMarker)
    poiMarkersRef.current = []
    amenityMarkersRef.current.forEach(disposeMarker)
    amenityMarkersRef.current = []
    durationOverlayRef.current?.setMap(null)
    durationOverlayRef.current = null
    setMapReady(false)

    async function renderMap() {
      if (!browserKey) {
        setError('Google Maps browser key is missing.')
        return
      }

      if (!mapElementRef.current) {
        return
      }

      try {
        const { Map } = (await importLibrary('maps')) as google.maps.MapsLibrary

        class DurationOverlay extends google.maps.OverlayView {
          private readonly position: google.maps.LatLngLiteral
          private readonly text: string
          private readonly placement: 'above' | 'below'
          private container: HTMLDivElement | null = null
          private connector: HTMLDivElement | null = null
          private bubble: HTMLDivElement | null = null

          constructor(
            position: google.maps.LatLngLiteral,
            text: string,
            placement: 'above' | 'below',
          ) {
            super()
            this.position = position
            this.text = text
            this.placement = placement
          }

          onAdd() {
            this.container = document.createElement('div')
            this.container.style.position = 'absolute'
            this.container.style.pointerEvents = 'none'

            this.connector = document.createElement('div')
            this.connector.style.position = 'absolute'
            this.connector.style.left = '50%'
            this.connector.style.top = this.placement === 'above' ? '-24px' : '0'
            this.connector.style.width = '3px'
            this.connector.style.height = '24px'
            this.connector.style.transform = 'translateX(-50%)'
            this.connector.style.background = 'linear-gradient(#62e6dc, #1b8795)'
            this.connector.style.borderRadius = '3px'
            this.connector.style.boxShadow = '0 0 8px rgba(98, 230, 220, 0.75)'

            this.bubble = document.createElement('div')
            this.bubble.style.position = 'absolute'
            this.bubble.style.left = '50%'
            this.bubble.style.top = this.placement === 'above' ? '-78px' : '25px'
            this.bubble.style.transform = 'translateX(-50%)'
            this.bubble.style.display = 'flex'
            this.bubble.style.flexDirection = 'column'
            this.bubble.style.gap = '2px'
            this.bubble.style.minWidth = '112px'
            this.bubble.style.padding = '8px 11px 9px'
            this.bubble.style.borderRadius = '8px'
            this.bubble.style.background = 'rgba(4, 17, 27, 0.94)'
            this.bubble.style.border = '1px solid rgba(98, 230, 220, 0.7)'
            this.bubble.style.boxShadow = '0 8px 24px rgba(0, 0, 0, 0.35), 0 0 14px rgba(82, 230, 232, 0.12)'
            this.bubble.style.color = '#edf7ff'
            this.bubble.style.whiteSpace = 'nowrap'

            const label = document.createElement('span')
            label.textContent = 'TOTAL JOURNEY'
            label.style.color = '#62e6dc'
            label.style.font = '500 9px/1.1 "DM Mono", monospace'
            label.style.letterSpacing = '0.08em'

            const value = document.createElement('strong')
            value.textContent = this.text
            value.style.font = '700 16px/1.1 Manrope, sans-serif'

            const note = document.createElement('span')
            note.textContent = 'including stops'
            note.style.color = '#91a9b4'
            note.style.font = '500 9px/1.1 "DM Mono", monospace'

            this.bubble.append(label, value, note)

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
            this.container.style.top = `${pixel.y}px`
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

        const path = route && route.geometry.length > 0
          ? toGooglePath(route.geometry)
          : [{ lat: 48.2082, lng: 16.3738 }]
        const map = new Map(mapElementRef.current, {
          center: path[0],
          zoom: route ? 7 : 17,
          tilt: 25,
          heading: 0,
          mapId: mapId || undefined,
          colorScheme: google.maps.ColorScheme.DARK,
          zoomControl: true,
          zoomControlOptions: {
            position: google.maps.ControlPosition.RIGHT_BOTTOM,
          },
          mapTypeControl: false,
          streetViewControl: false,
          fullscreenControl: false,
          styles: [
  // Keep the navigation view flat and uncluttered.
  {
    featureType: 'building',
    elementType: 'geometry',
    stylers: [{ visibility: 'off' }],
  },
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

        if (route) {
          map.fitBounds(bounds, 48)
        }

        if (route) {
          polylineRef.current = new google.maps.Polyline({
            map,
            path,
            strokeColor: routePriority === 'SCENIC' ? '#f2cc61' : '#19a7ff',
            strokeOpacity: 0.95,
            strokeWeight: 6,
          })
        }

        const originMarker = new google.maps.Marker({
          map,
          position: path[0],
          title: route?.origin ?? 'Current vehicle position',
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

        const destinationMarker = route ? new google.maps.Marker({
          map,
          position: path[path.length - 1],
          title: route.destination,
          icon: createMarkerIcon(destinationPin, 30, 46),
          zIndex: 3,
        }) : null

        const stopMarkers = route?.stops.filter(
          (stop) => showChargingStop || stop.category !== 'charging',
        ).map(
          (stop) =>
            new google.maps.Marker({
              map,
              position: { lat: stop.coords[1], lng: stop.coords[0] },
              title: stop.name,
              icon: markerIconForCategory(stop.category),
              zIndex: 2,
            }),
        ) ?? []

        const durationOverlay = route ? new DurationOverlay(
          getCalloutPosition(path, [...route.stops, ...poiResultsRef.current]),
          formatDuration(
            showChargingStop
              ? route.stats.totalDurationMinutes
              : route.stats.drivingDurationMinutes,
          ),
          Math.abs(path[path.length - 1].lng - path[0].lng)
            >= Math.abs(path[path.length - 1].lat - path[0].lat)
            ? 'above'
            : 'below',
        ) : null
        durationOverlay?.setMap(map)

        markersRef.current = [
          originMarker,
          ...(destinationMarker ? [destinationMarker] : []),
          ...stopMarkers,
        ]
        durationOverlayRef.current = durationOverlay
        setMapReady(true)
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
      disposeMap()
      markersRef.current.forEach(disposeMarker)
      markersRef.current = []
      poiMarkersRef.current.forEach(disposeMarker)
      poiMarkersRef.current = []
      amenityMarkersRef.current.forEach(disposeMarker)
      amenityMarkersRef.current = []
      durationOverlayRef.current?.setMap(null)
      durationOverlayRef.current = null
      setMapReady(false)
    }
  }, [route, routePriority, showChargingStop])

  useEffect(() => {
    if (!mapReady || !mapRef.current || !route) {
      return
    }

    if (amenityFocusName) {
      const selectedStop = (route.chargingStop?.name === amenityFocusName
        ? route.chargingStop
        : route.stops.find(
        (stop) => stop.category === 'charging' && stop.name === amenityFocusName,
          ))
      if (!selectedStop) {
        return
      }

      mapRef.current.panTo({
        lat: selectedStop.coords[1],
        lng: selectedStop.coords[0],
      })
      mapRef.current.setTilt(25)
      mapRef.current.setHeading(0)
      mapRef.current.setZoom(16)
      return
    }

    const path = toGooglePath(route.geometry)
    const bounds = new google.maps.LatLngBounds()
    path.forEach((point) => bounds.extend(point))
    mapRef.current.setTilt(drivingActive ? 67.5 : 25)
    if (drivingActive) {
      mapRef.current.panTo(path[0])
      mapRef.current.setHeading(routeHeading(path))
      mapRef.current.setZoom(18)
    } else {
      mapRef.current.setHeading(0)
      mapRef.current.fitBounds(bounds, 48)
    }
  }, [amenityFocusName, drivingActive, mapReady, route])

  useEffect(() => {
    if (!mapReady || !mapRef.current) {
      return
    }

    amenityMarkersRef.current.forEach(disposeMarker)
    amenityMarkersRef.current = amenityResults.map((amenity) => {
      return new google.maps.Marker({
        map: mapRef.current,
        position: { lat: amenity.coords[1], lng: amenity.coords[0] },
        title: `${amenity.name} - ${amenity.category}`,
        icon: markerIconForCategory(amenity.category),
        zIndex: 6,
      })
    })

    return () => {
      amenityMarkersRef.current.forEach(disposeMarker)
      amenityMarkersRef.current = []
    }
  }, [amenityResults, mapReady])

  useEffect(() => {
    if (!mapReady || !mapRef.current) {
      return
    }

    poiMarkersRef.current.forEach(disposeMarker)
    poiMarkersRef.current = poiResults.map((poi) => {
      const marker = new google.maps.Marker({
        map: mapRef.current,
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
    })

    return () => {
      poiMarkersRef.current.forEach(disposeMarker)
      poiMarkersRef.current = []
    }
  }, [mapReady, onPoiSelect, poiResults, selectedPoiId])

  if (error) {
    return <p role="alert">{error}</p>
  }
  return <div ref={mapElementRef} className="route-map" />
}

const markerAssetByCategory: Partial<Record<StopPinpoint['category'], string>> = {
  charging: chargingPin,
  attraction: attractionPin,
  service: servicePin,
  food: foodPin,
  restaurant: foodPin,
  coffee: foodPin,
  hotel: hotelPin,
  rest: servicePin,
  toilets: servicePin,
  fuel: servicePin,
  shopping: servicePin,
}

function markerIconForCategory(category: StopPinpoint['category']): google.maps.Icon | undefined {
  const asset = markerAssetByCategory[category]
  return asset ? createMarkerIcon(asset, 26, 46) : undefined
}

function createMarkerIcon(url: string, width: number, height: number): google.maps.Icon {
  return {
    url,
    scaledSize: new google.maps.Size(width, height),
    anchor: new google.maps.Point(width / 2, height),
  }
}