import type { RouteResponse } from '../../../types/contracts'

interface RouteSummaryProps {
  route: RouteResponse
}

function formatDuration(totalMinutes: number) {
  const hours = Math.floor(totalMinutes / 60)
  const minutes = totalMinutes % 60

  return hours === 0 ? `${minutes} min` : `${hours} h ${minutes} min`
}

export function RouteSummary({ route }: RouteSummaryProps) {
  return (
    <section aria-live="polite">
      <h2>Route</h2>
      <p>
        {route.origin} to {route.destination}
      </p>
      <p>{route.stats.totalDistanceKm} km</p>
      <p>Driving: {formatDuration(route.stats.drivingDurationMinutes)}</p>
      <p>Total journey: {formatDuration(route.stats.totalDurationMinutes)}</p>

      {route.chargingStop && (
        <section>
          <h3>Automatic charging stop</h3>
          <p>{route.chargingStop.name}</p>
          <p>
            {route.chargingStop.partner ? 'Partner location' : 'Non-partner location'}
          </p>
          <p>{route.chargingStop.detourMinutes} min detour</p>
          {(route.chargingStop.chargingDurationMinutes ?? 0) > 0 && (
            <p>{route.chargingStop.chargingDurationMinutes} min charging</p>
          )}
          {(route.chargingStop.partner?.benefit ?? route.chargingStop.partnerBenefit) && (
            <p>
              {route.chargingStop.partner?.benefit ?? route.chargingStop.partnerBenefit}
            </p>
          )}
        </section>
      )}

      {route.borderCrossings.length > 0 && (
        <section>
          <h3>Border crossings</h3>
          {route.borderCrossings.map((crossing) => (
            <p key={`${crossing.fromCountry}-${crossing.toCountry}`}>
              {crossing.fromCountry} to {crossing.toCountry}
            </p>
          ))}
        </section>
      )}

      {route.routeRequirements.length > 0 && (
        <section>
          <h3>Route requirements</h3>
          {route.routeRequirements.map((requirement) => (
            <p key={requirement.id}>{requirement.name}</p>
          ))}
        </section>
      )}

      {route.alerts.map((alert) => (
        <p key={`${alert.type}-${alert.message}`} role="alert">
          {alert.message}
        </p>
      ))}
    </section>
  )
}
