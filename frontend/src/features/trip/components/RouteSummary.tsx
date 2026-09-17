import type { RouteResponse } from '../../../types/contracts'

interface RouteSummaryProps {
  route: RouteResponse
}

function formatDuration(totalMinutes: number) {
  const roundedMinutes = Math.round(totalMinutes)
  const hours = Math.floor(roundedMinutes / 60)
  const minutes = roundedMinutes % 60

  return hours === 0 ? `${minutes} min` : `${hours} h ${minutes} min`
}

export function RouteSummary({ route }: RouteSummaryProps) {
  const stopCount = route.stops.length

  return (
    <section className="route-summary" aria-live="polite">
      <div className="trip-details-heading">
        <div>
          <p className="eyebrow">Trip details</p>
          <h2>{route.destination}</h2>
        </div>
        <span className="trip-status">ROUTE ACTIVE</span>
      </div>
      <p className="route-endpoints">
        {route.origin} to {route.destination}
      </p>
      <div className="trip-metrics">
        <div className="trip-metric">
          <span>Driving time</span>
          <strong>{formatDuration(route.stats.drivingDurationMinutes)}</strong>
        </div>
        <div className="trip-metric">
          <span>Distance</span>
          <strong>{Math.round(route.stats.totalDistanceKm)} km</strong>
        </div>
        <div className="trip-metric">
          <span>Stops</span>
          <strong>{stopCount}</strong>
        </div>
        <div className="trip-metric trip-cost-metric">
          <span>Total cost</span>
          <strong>{route.stats.totalPriceEur.toFixed(2)} EUR</strong>
        </div>
      </div>
    </section>
  )
}
