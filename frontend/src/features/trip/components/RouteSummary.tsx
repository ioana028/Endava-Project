import type { RouteResponse } from '../../../types/contracts'

interface RouteSummaryProps {
  route: RouteResponse
  showChargingStop?: boolean
}

function formatDuration(totalMinutes: number) {
  const roundedMinutes = Math.round(totalMinutes)
  const hours = Math.floor(roundedMinutes / 60)
  const minutes = roundedMinutes % 60

  if (hours === 0) return `${minutes} min`
  return minutes === 0 ? `${hours} h` : `${hours} h ${minutes} min`
}

function formatEur(amount: number) {
  return `${amount.toFixed(2)} EUR`
}

export function RouteSummary({
  route,
  showChargingStop = true,
}: RouteSummaryProps) {
  const confirmedStops = route.stops.filter(
    (stop) => showChargingStop || stop.category !== 'charging',
  )
  const journeyMinutes = showChargingStop
    ? route.stats.totalDurationMinutes
    : route.stats.drivingDurationMinutes

  return (
    <section className="route-summary" aria-live="polite">
      <div className="trip-details-heading">
        <div>
          <p className="eyebrow">Route overview</p>
          <h2>Trip details</h2>
        </div>
        {confirmedStops.length > 0 && (
          <span className="trip-stop-count" aria-label={`${confirmedStops.length} confirmed stops added to the route`}>
            {confirmedStops.length} {confirmedStops.length === 1 ? 'stop' : 'stops'}
          </span>
        )}
      </div>
      <div className="trip-details-body">
        <ol className="trip-timeline" aria-label="Route stops">
          <li className="trip-timeline-item trip-timeline-endpoint">
            <span className="trip-timeline-node" aria-hidden="true" />
            <div className="trip-timeline-copy">
              <span>Start</span>
              <strong title={route.origin}>{route.origin}</strong>
            </div>
          </li>
          {confirmedStops.map((stop) => (
            <li className={`trip-timeline-item trip-timeline-${stop.category}`} key={stop.id}>
              <span className="trip-timeline-node" aria-hidden="true" />
              <div className="trip-timeline-copy">
                <span>{stop.category === 'charging' ? 'Charging' : stop.category}</span>
                <strong title={stop.name}>{stop.name}</strong>
              </div>
            </li>
          ))}
          <li className="trip-timeline-item trip-timeline-endpoint trip-timeline-arrival">
            <span className="trip-timeline-node" aria-hidden="true" />
            <div className="trip-timeline-copy">
              <span>Destination</span>
              <strong title={route.destination}>{route.destination}</strong>
            </div>
          </li>
        </ol>
        <div className="trip-metrics" aria-label="Trip metrics">
          <div className="trip-metric">
            <span>{showChargingStop ? 'Journey time' : 'Drive time'}</span>
            <strong>{formatDuration(journeyMinutes)}</strong>
          </div>
          <div className="trip-metric">
            <span>Distance</span>
            <strong>{Math.round(route.stats.totalDistanceKm)} km</strong>
          </div>
          <div className="trip-metric trip-cost-metric">
            <span>Est. cost</span>
            <strong>{formatEur(route.stats.totalPriceEur)}</strong>
          </div>
        </div>
      </div>
    </section>
  )
}
