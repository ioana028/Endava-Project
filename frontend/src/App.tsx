import { useEffect, useState } from 'react'
import { AssistantStatus } from './features/assistant/components/AssistantStatus'
import { useRealtimeAssistant } from './features/assistant/hooks/useRealtimeAssistant'
import { RouteMap } from './features/map/components/RouteMap'
import { RouteSummary } from './features/trip/components/RouteSummary'
import type { VehicleTelemetry } from './types/contracts'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

function App() {
  const assistant = useRealtimeAssistant()
  const [telemetry, setTelemetry] = useState<VehicleTelemetry | null>(null)

  const route = assistant.response?.route

  useEffect(() => {
    let cancelled = false

    fetch(`${API_BASE_URL}/api/vehicle/telemetry`)
      .then((response) => {
        if (!response.ok) {
          throw new Error('Telemetry unavailable')
        }
        return response.json() as Promise<VehicleTelemetry>
      })
      .then((value) => {
        if (!cancelled) {
          setTelemetry(value)
        }
      })
      .catch(() => {
        if (!cancelled) {
          setTelemetry(null)
        }
      })

    return () => {
      cancelled = true
    }
  }, [])

  return (
    <main className="cockpit-shell">
      <header className="cockpit-topbar">
        <div className="status-time">10:42</div>
        <div className="status-weather">Partly cloudy <strong>18°C</strong></div>
        <div className="status-device">4G <strong>82%</strong> <span aria-hidden="true">▰</span></div>
      </header>

      <section className="cockpit-grid">
        <div className="map-stage">
          <RouteMap
            route={route}
            poiResults={assistant.poiResults}
            amenityResults={assistant.amenityResults}
            amenityFocusName={assistant.amenitySearchContext?.selectedStopName}
            drivingActive={assistant.driving?.active ?? false}
            selectedPoiId={assistant.selectedPoi?.id}
            onPoiSelect={assistant.selectPoi}
          />
          {assistant.driving?.active && (
            <section className="driving-status" aria-live="polite">
              <p className="panel-kicker">Driving mode</p>
              <strong>{Math.round(assistant.driving.remainingDistanceKm)} km remaining</strong>
              <span>{Math.round(assistant.driving.remainingDurationMinutes)} min · ETA {assistant.driving.eta}</span>
              <span>{assistant.driving.nextStop ? `Next stop: ${assistant.driving.nextStop.name}` : 'No mandatory stop ahead'}</span>
            </section>
          )}
          {assistant.amenitySearchState !== 'IDLE' && assistant.amenitySearchContext && (
            <section className="amenity-results" aria-live="polite">
              <div className="section-heading">
                <div>
                  <p className="panel-kicker">Nearby amenities</p>
                  <h2>{assistant.amenitySearchContext.selectedStopName}</h2>
                </div>
                <span className="result-count">within {assistant.amenitySearchContext.radiusMeters} m</span>
              </div>
              {assistant.amenitySearchState === 'LOADING' && <p>Searching nearby places...</p>}
              {assistant.amenitySearchState === 'EMPTY' && <p>No returned amenities in this radius.</p>}
              {assistant.amenitySearchState === 'SUCCESS' && (
                <ul>
                  {assistant.amenityResults.map((amenity) => (
                    <li key={amenity.id}>
                      <strong>{amenity.name}</strong>
                      <span>{amenity.category} {amenity.distanceMeters ? `· ${Math.round(amenity.distanceMeters)} m` : ''}</span>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          )}
        </div>

        <aside className="cockpit-rail">
          <section className="suzanne-orb-panel">
            {assistant.successFeedback && (assistant.successFeedback.action === 'booking' || assistant.successFeedback.action === 'purchase') ? (
              <div className="action-confirmation" role="status" aria-live="assertive">
                <span className="confirmation-check" aria-hidden="true">✓</span>
                <p className="eyebrow">Complete</p>
                <h1>{assistant.successFeedback.label}</h1>
                <strong>Confirmation ready</strong>
                <span>Reference: {assistant.successFeedback.reference}</span>
              </div>
            ) : (
              <>
                <div className={`suzanne-orb state-${assistant.state.toLowerCase()}`} aria-hidden="true" />
                <p className="eyebrow">Suzanne</p>
                <h1>{assistant.transcript || 'Your route, thoughtfully handled.'}</h1>
                <AssistantStatus
                  enabled={assistant.enabled}
                  state={assistant.state}
                  transcript={assistant.transcript}
                  error={assistant.error}
                  onEnable={() => void assistant.enable()}
                  onDisable={assistant.disable}
                />
              </>
            )}
          </section>

          <section className="cockpit-card vehicle-card">
            <div className="card-heading"><span>Battery</span><span>Range</span></div>
            <div className="vehicle-values"><strong>{telemetry ? `${Math.round(telemetry.batteryPercent)}%` : '--'}</strong><strong>{telemetry ? `${Math.round(telemetry.estimatedRangeKm)} km` : '--'}</strong></div>
            <div className="battery-track" aria-label={`${Math.round(telemetry?.batteryPercent ?? 0)} percent battery`}><span style={{ width: `${telemetry?.batteryPercent ?? 0}%` }} /></div>
            <div className="vehicle-footnote"><span>Current charge</span><span>{telemetry ? `${telemetry.consumptionRateKwh.toFixed(1)} kWh / 100 km` : 'Telemetry loading'}</span></div>
          </section>

          <div className={`utility-panel-stage${route && !assistant.driving?.active ? ' has-route' : ''}`} aria-live="polite">
            <section className="cockpit-card media-card utility-panel">
              <div className="media-art" aria-hidden="true" />
              <div><strong>Crystal Sky</strong><span>Luminous · Suzanne mix</span></div>
              <div className="song-progress" aria-label="Song progress"><span /></div>
              <div className="song-time"><span>1:24</span><span>3:47</span></div>
              <div className="media-controls" aria-label="Media controls"><button type="button" aria-label="Previous track">|◀</button><button type="button" aria-label="Pause">Ⅱ</button><button type="button" aria-label="Next track">▶|</button></div>
            </section>
            {route && (
              <section className="cockpit-card cost-panel utility-panel">
                <RouteSummary route={route} />
              </section>
            )}
          </div>
        </aside>
      </section>

      {assistant.response && <section className="sr-only" aria-live="polite">{assistant.response.spokenResponse}</section>}

      <nav className="cockpit-nav" aria-label="Main navigation">
        <button className="active" type="button"><span aria-hidden="true">➤</span>Map</button>
        <button type="button"><span aria-hidden="true">♫</span>Media</button>
        <button type="button"><span aria-hidden="true">✣</span>Climate</button>
        <button type="button"><span aria-hidden="true">▱</span>Vehicle</button>
        <button type="button"><span aria-hidden="true">⊞</span>Apps</button>
      </nav>
    </main>
  )
}

export default App
