import type { RouteResponse } from '../../../types/contracts'

interface RouteSummaryProps {
  route: RouteResponse
  showChargingStop?: boolean
}

function formatDuration(totalMinutes: number) {
  const roundedMinutes = Math.round(totalMinutes)
  const hours = Math.floor(roundedMinutes / 60)
  const minutes = roundedMinutes % 60

  return hours === 0 ? `${minutes} min` : `${hours} h ${minutes} min`
}

function formatEur(amount: number) {
  return `${amount.toFixed(2)} EUR`
}

export function RouteSummary({
  route,
  showChargingStop = true,
}: RouteSummaryProps) {
  const stopCount = route.stops.filter(
    (stop) => showChargingStop || stop.category !== 'charging',
  ).length
  return (
    <section className="route-summary" aria-live="polite">
      <div className="trip-details-heading">
        <div>
          <p className="eyebrow">Trip details</p>
          <h2>{route.origin} to {route.destination}</h2>
          {route.countries.length > 0 && (
            <p className="route-countries">{route.countries.join(' · ')}</p>
          )}
        </div>
      </div>
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
          <strong>{formatEur(route.stats.totalPriceEur)}</strong>
        </div>
      </div>
      {route.chargingOptions.length > 0 && (
        <div className="charging-options" aria-label="Charging options">
          <p className="eyebrow">Charging options</p>
          {route.chargingOptions.map((option) => (
            <div className="charging-option" key={option.stop.id}>
              <strong>#{option.optionNumber} {option.stop.name}</strong>
              <span>
                {Math.round(option.stop.chargingDurationMinutes ?? 0)} min charging
                {' · '}
                {option.status}
              </span>
            </div>
          ))}
        </div>
      )}
    </section>
  )
}
