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
      <p>{formatDuration(route.stats.totalDurationMinutes)}</p>

      {route.alerts.map((alert) => (
        <p key={`${alert.type}-${alert.message}`} role="alert">
          {alert.message}
        </p>
      ))}
    </section>
  )
}
