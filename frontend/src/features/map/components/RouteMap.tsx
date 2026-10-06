import { useEffect, useMemo, useRef, useState } from 'react'
import { importLibrary, setOptions } from '@googlemaps/js-api-loader'
import type { RoutePriority, RouteResponse, StopPinpoint } from '../../../types/contracts'
import attractionPin from '../../../assets/attractionpin.png'
import chargingPin from '../../../assets/chargingpin.png'
import destinationPin from '../../../assets/destinationpin.png'
import foodPin from '../../../assets/foodpin.png'
import hotelPin from '../../../assets/hotelpin.png'
import servicePin from '../../../assets/servicepin.png'
import { toGooglePath } from '../utils/routeGeometry'
import { routePathChanged, serializeMapRoute } from '../utils/mapRouteView'
import type { MapRouteView } from '../utils/mapRouteView'

const markerAssets = [
  attractionPin,
  chargingPin,
  destinationPin,
  foodPin,
  hotelPin,
  servicePin,
]

function preloadMarkerAssets(): Promise<void> {
  if (typeof Image === 'undefined') {
    return Promise.resolve()
  }
  return Promise.all(
    markerAssets.map((src) => new Promise<void>((resolve) => {
      const image = new Image()
      image.onload = () => resolve()
      image.onerror = () => resolve()
      image.src = src
    })),
  ).then(() => undefined)
}

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
  markers: Pick<StopPinpoint, 'coords'>[],
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
  markers: Pick<StopPinpoint, 'coords'>[],
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

function routeOverviewCamera(map: google.maps.Map, path: google.maps.LatLngLiteral[]) {
  const bounds = new google.maps.LatLngBounds()
  path.forEach((point) => bounds.extend(point))
  const northEast = bounds.getNorthEast()
  const southWest = bounds.getSouthWest()
  const mercatorY = (latitude: number) => {
    const radians = Math.max(-85.051, Math.min(85.051, latitude)) * Math.PI / 180
    return (1 - Math.log(Math.tan(radians) + 1 / Math.cos(radians)) / Math.PI) / 2
  }
  const longitudeSpan = ((northEast.lng() - southWest.lng() + 360) % 360) / 360
  const latitudeSpan = Math.abs(mercatorY(northEast.lat()) - mercatorY(southWest.lat()))
  const width = Math.max(1, map.getDiv().clientWidth - 96)
  const height = Math.max(1, map.getDiv().clientHeight - 96)
  const zoom = Math.min(
    Math.log2(width / (256 * Math.max(longitudeSpan, 1e-6))),
    Math.log2(height / (256 * Math.max(latitudeSpan, 1e-6))),
  )
  return {
    center: bounds.getCenter().toJSON(),
    zoom: Math.max(3, Math.min(17, zoom)),
    tilt: 25,
    heading: 0,
  }
}

const overviewMapStyles: google.maps.MapTypeStyle[] = [
  {
    featureType: 'landscape.man_made',
    elementType: 'geometry',
    stylers: [{ visibility: 'on' }],
  },
]

const drivingMapStyles: google.maps.MapTypeStyle[] = [
  {
    featureType: 'building',
    elementType: 'geometry',
    stylers: [{ visibility: 'off' }],
  },
  {
    featureType: 'landscape.man_made',
    elementType: 'geometry',
    stylers: [{ visibility: 'off' }],
  },
]

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
  focusStop?: Pick<StopPinpoint, 'id' | 'name' | 'coords'> | null
  focusDestination?: boolean
  drivingActive?: boolean
  showChargingStop?: boolean
  routePriority?: RoutePriority
  selectedPoiId?: string | null
  onPoiSelect?: (poiId: string) => void
}

export function RouteMap({
  route: suppliedRoute,
  poiResults = [],
  amenityResults = [],
  amenityFocusName = null,
  focusStop = null,
  focusDestination = false,
  drivingActive = false,
  showChargingStop = true,
  routePriority = 'BALANCED',
  selectedPoiId = null,
  onPoiSelect,
}: RouteMapProps) {
  const serializedRoute = serializeMapRoute(suppliedRoute)
  const route = useMemo(() => serializedRoute
    ? JSON.parse(serializedRoute) as MapRouteView : undefined, [serializedRoute])
  const mapElementRef = useRef<HTMLDivElement | null>(null)
  const mapRef = useRef<google.maps.Map | null>(null)
  const polylineRef = useRef<google.maps.Polyline | null>(null)
  const routeMarkersRef = useRef<Map<string, google.maps.Marker>>(new Map())
  const markerTimersRef = useRef<number[]>([])
  const routeDrawFrameRef = useRef<number | null>(null)
  const previousRouteRef = useRef<MapRouteView | null>(null)
  const poiMarkersRef = useRef<Map<string, google.maps.Marker>>(new Map())
  const poiMarkerTimersRef = useRef<number[]>([])
  const onPoiSelectRef = useRef(onPoiSelect)
  const amenityMarkersRef = useRef<google.maps.Marker[]>([])
  const poiResultsRef = useRef(poiResults)
  const durationOverlayRef = useRef<google.maps.OverlayView | null>(null)
  const durationOverlayClassRef = useRef<(new (
    position: google.maps.LatLngLiteral,
    text: string,
    placement: 'above' | 'below',
  ) => google.maps.OverlayView) | null>(null)
  const mapStylesRef = useRef<google.maps.MapTypeStyle[]>([])
  const initialRouteRef = useRef(route)
  const cameraFrameRef = useRef<number | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [mapReady, setMapReady] = useState(false)

  poiResultsRef.current = poiResults
  onPoiSelectRef.current = onPoiSelect

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
    const routeMarkers = routeMarkersRef.current
    const poiMarkers = poiMarkersRef.current

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
        await preloadMarkerAssets()

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

        durationOverlayClassRef.current = DurationOverlay

        if (cancelled || !mapElementRef.current) {
          return
        }

        const initialRoute = initialRouteRef.current
        const path = initialRoute && initialRoute.geometry.length > 0
          ? toGooglePath(initialRoute.geometry)
          : [{ lat: 48.2082, lng: 16.3738 }]
        const map = new Map(mapElementRef.current, {
          center: path[0],
          zoom: initialRoute ? 7 : 17,
          tilt: 0,
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
  ...overviewMapStyles,
],
        })
        mapRef.current = map
        mapStylesRef.current = (map.get('styles') as google.maps.MapTypeStyle[] | undefined) ?? []

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
      if (cameraFrameRef.current !== null) {
        window.cancelAnimationFrame(cameraFrameRef.current)
      }
      if (routeDrawFrameRef.current !== null) {
        window.cancelAnimationFrame(routeDrawFrameRef.current)
      }
      markerTimersRef.current.forEach(window.clearTimeout)
      markerTimersRef.current = []
      poiMarkerTimersRef.current.forEach(window.clearTimeout)
      poiMarkerTimersRef.current = []
      polylineRef.current?.setMap(null)
      polylineRef.current = null
      disposeMap()
      routeMarkers.forEach(disposeMarker)
      routeMarkers.clear()
      previousRouteRef.current = null
      poiMarkers.forEach(disposeMarker)
      poiMarkers.clear()
      amenityMarkersRef.current.forEach(disposeMarker)
      amenityMarkersRef.current = []
      durationOverlayRef.current?.setMap(null)
      durationOverlayRef.current = null
      setMapReady(false)
    }
  }, [])

  useEffect(() => {
    const map = mapRef.current
    if (!mapReady || !map) return
    const path = route && route.geometry.length > 0
      ? toGooglePath(route.geometry)
      : [{ lat: 48.2082, lng: 16.3738 }]
    const previousRoute = previousRouteRef.current
    const isNewRoute = Boolean(
      route && routePathChanged(previousRoute, route),
    )
    previousRouteRef.current = route ?? null
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches

    if (routeDrawFrameRef.current !== null) {
      window.cancelAnimationFrame(routeDrawFrameRef.current)
      routeDrawFrameRef.current = null
    }
    markerTimersRef.current.forEach(window.clearTimeout)
    markerTimersRef.current = []
    durationOverlayRef.current?.setMap(null)
    map.setOptions({
      styles: [...mapStylesRef.current, ...(drivingActive ? drivingMapStyles : [])],
    })

    if (!route) {
      polylineRef.current?.setMap(null)
      polylineRef.current = null
    } else {
      const polyline = polylineRef.current ?? new google.maps.Polyline({ map })
      polyline.setOptions({
        strokeColor: routePriority === 'SCENIC' ? '#f2cc61' : '#19a7ff',
        strokeOpacity: 0.95,
        strokeWeight: 6,
      })
      polylineRef.current = polyline
      if (isNewRoute && !reducedMotion && !drivingActive && path.length > 1) {
        polyline.setPath([path[0]])
        let startedAt: number | null = null
        let lastUpdatedAt = 0
        const draw = (now: number) => {
          startedAt ??= now
          const progress = Math.min(1, (now - startedAt) / 950)
          const eased = 1 - (1 - progress) ** 2
          if (now - lastUpdatedAt >= 28 || progress === 1) {
            const visibleCount = Math.max(2, Math.ceil(1 + (path.length - 1) * eased))
            polyline.setPath(progress === 1 ? path : path.slice(0, visibleCount))
            lastUpdatedAt = now
          }
          if (progress < 1) {
            routeDrawFrameRef.current = window.requestAnimationFrame(draw)
          } else {
            routeDrawFrameRef.current = null
          }
        }
        routeDrawFrameRef.current = window.requestAnimationFrame(draw)
      } else {
        polyline.setPath(path)
      }
    }

    type RouteMarkerSpec = { key: string; position: google.maps.LatLngLiteral; title: string; icon: google.maps.Icon | google.maps.Symbol | undefined; zIndex: number }
    const markerSpecs: RouteMarkerSpec[] = [{
      key: 'origin',
      position: path[0],
      title: route?.origin ?? 'Current vehicle position',
      icon: drivingActive
        ? {
            path: google.maps.SymbolPath.FORWARD_CLOSED_ARROW,
            scale: 7,
            rotation: routeHeading(path),
            fillColor: '#61e4c1',
            fillOpacity: 1,
            strokeColor: '#ffffff',
            strokeWeight: 2,
          }
        : {
            path: google.maps.SymbolPath.CIRCLE,
            scale: 8,
            fillColor: '#1677ff',
            fillOpacity: 1,
            strokeColor: '#ffffff',
            strokeWeight: 3,
          },
      zIndex: 3,
    }]
    if (route) {
      markerSpecs.push({
        key: 'destination',
        position: path[path.length - 1],
        title: route.destination,
        icon: createMarkerIcon(destinationPin, 30, 46),
        zIndex: 3,
      })
      route.stops.filter(
        (stop) => showChargingStop || stop.category !== 'charging',
      ).forEach((stop) => markerSpecs.push({
        key: `stop:${stop.id}`,
        position: { lat: stop.coords[1], lng: stop.coords[0] },
        title: stop.name,
        icon: markerIconForCategory(stop.category),
        zIndex: 2,
      }))
    }

    const desiredKeys = new Set(markerSpecs.map((spec) => spec.key))
    for (const [key, marker] of routeMarkersRef.current) {
      if (!desiredKeys.has(key) || (isNewRoute && key !== 'origin')) {
        disposeMarker(marker)
        routeMarkersRef.current.delete(key)
      }
    }
    let newMarkerIndex = 0
    for (const spec of markerSpecs) {
      const existing = routeMarkersRef.current.get(spec.key)
      if (existing) {
        existing.setOptions({
          position: spec.position,
          title: spec.title,
          icon: spec.icon,
          zIndex: spec.zIndex,
        })
        if (!existing.getMap()) existing.setMap(map)
        continue
      }
      const shouldDrop = spec.key !== 'origin' && !reducedMotion && !drivingActive
      const marker = new google.maps.Marker({
        map: shouldDrop ? null : map,
        position: spec.position,
        title: spec.title,
        icon: spec.icon,
        zIndex: spec.zIndex,
      })
      routeMarkersRef.current.set(spec.key, marker)
      if (shouldDrop) {
        const delay = (isNewRoute ? 950 : 0) + newMarkerIndex * 110
        const timer = window.setTimeout(() => {
          if (routeMarkersRef.current.get(spec.key) === marker && mapRef.current === map) {
            marker.setMap(map)
            marker.setAnimation(google.maps.Animation.DROP)
          }
        }, delay)
        markerTimersRef.current.push(timer)
        newMarkerIndex += 1
      }
    }

    const DurationOverlay = durationOverlayClassRef.current
    const durationOverlay = route && DurationOverlay ? new DurationOverlay(
      getCalloutPosition(path, [...route.stops, ...poiResultsRef.current]),
      formatDuration(showChargingStop
        ? route.stats.totalDurationMinutes
        : route.stats.drivingDurationMinutes),
      Math.abs(path[path.length - 1].lng - path[0].lng)
        >= Math.abs(path[path.length - 1].lat - path[0].lat)
        ? 'above' : 'below',
    ) : null
    durationOverlay?.setMap(map)
    durationOverlayRef.current = durationOverlay
  }, [drivingActive, mapReady, route, routePriority, showChargingStop])

  useEffect(() => {
    if (!mapReady || !mapRef.current || !route) {
      return
    }

    const map = mapRef.current
    const path = toGooglePath(route.geometry)
    if (path.length === 0) return
    let target: { center: google.maps.LatLngLiteral; zoom: number; tilt: number; heading: number }

    if (drivingActive) {
      target = { center: path[0], zoom: 18, tilt: 67.5, heading: routeHeading(path) }
    } else if (focusStop) {
      target = {
        center: { lat: focusStop.coords[1], lng: focusStop.coords[0] },
        zoom: 17,
        tilt: 0,
        heading: 0,
      }
    } else if (amenityFocusName) {
      const selectedStop = (route.chargingStop?.name === amenityFocusName
        ? route.chargingStop
        : route.stops.find(
        (stop) => stop.category === 'charging' && stop.name === amenityFocusName,
          ))
      if (!selectedStop) {
        return
      }
      target = {
        center: { lat: selectedStop.coords[1], lng: selectedStop.coords[0] },
        zoom: 17,
        tilt: 0,
        heading: 0,
      }
    } else if (focusDestination) {
      target = { center: path[path.length - 1], zoom: 15, tilt: 0, heading: 0 }
    } else {
      target = routeOverviewCamera(map, path)
    }

    if (cameraFrameRef.current !== null) {
      window.cancelAnimationFrame(cameraFrameRef.current)
    }
    const currentCenter = map.getCenter()?.toJSON() ?? target.center
    const currentZoom = map.getZoom() ?? target.zoom
    const currentTilt = map.getTilt() ?? 0
    const currentHeading = map.getHeading() ?? 0
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    if (reducedMotion) {
      map.moveCamera(target)
      return
    }
    const duration = 1050
    let startedAt: number | null = null
    const shortestArc = (from: number, to: number) => ((to - from + 540) % 360) - 180
    const longitudeDelta = shortestArc(currentCenter.lng, target.center.lng)
    const headingDelta = shortestArc(currentHeading, target.heading)
    const animate = (now: number) => {
      startedAt ??= now
      const progress = Math.min(1, (now - startedAt) / duration)
      const eased = progress < 0.5
        ? 4 * progress ** 3
        : 1 - (-2 * progress + 2) ** 3 / 2
      map.moveCamera({
        center: {
          lat: currentCenter.lat + (target.center.lat - currentCenter.lat) * eased,
          lng: currentCenter.lng + longitudeDelta * eased,
        },
        zoom: currentZoom + (target.zoom - currentZoom) * eased,
        tilt: currentTilt + (target.tilt - currentTilt) * eased,
        heading: currentHeading + headingDelta * eased,
      })
      if (progress < 1) {
        cameraFrameRef.current = window.requestAnimationFrame(animate)
      } else {
        cameraFrameRef.current = null
      }
    }
    cameraFrameRef.current = window.requestAnimationFrame(animate)
    return () => {
      if (cameraFrameRef.current !== null) {
        window.cancelAnimationFrame(cameraFrameRef.current)
        cameraFrameRef.current = null
      }
    }
  }, [amenityFocusName, drivingActive, focusDestination, focusStop, mapReady, route])

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
    const map = mapRef.current
    if (!mapReady || !map) return

    poiMarkerTimersRef.current.forEach(window.clearTimeout)
    poiMarkerTimersRef.current = []
    const currentIds = new Set(poiResults.map((poi) => poi.id))
    for (const [id, marker] of poiMarkersRef.current) {
      if (!currentIds.has(id)) {
        disposeMarker(marker)
        poiMarkersRef.current.delete(id)
      }
    }
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    let newMarkerIndex = 0
    for (const poi of poiResults) {
      const options = {
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
        clickable: Boolean(onPoiSelectRef.current),
      }
      const existing = poiMarkersRef.current.get(poi.id)
      if (existing) {
        existing.setOptions(options)
        if (!existing.getMap()) existing.setMap(map)
        continue
      }
      const marker = new google.maps.Marker({
        ...options,
        map: reducedMotion ? map : null,
      })
      marker.addListener('click', () => onPoiSelectRef.current?.(poi.id))
      poiMarkersRef.current.set(poi.id, marker)
      if (!reducedMotion) {
        const timer = window.setTimeout(() => {
          if (poiMarkersRef.current.get(poi.id) === marker && mapRef.current === map) {
            marker.setMap(map)
            marker.setAnimation(google.maps.Animation.DROP)
          }
        }, newMarkerIndex * 110)
        poiMarkerTimersRef.current.push(timer)
        newMarkerIndex += 1
      }
    }
  }, [mapReady, poiResults, selectedPoiId])

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
