import { useState } from 'react'
import type { StopPinpoint } from '../../../types/contracts'
import type { PoiActionState } from '../hooks/useRealtimeAssistant'

interface PoiResultsProps {
  results: StopPinpoint[]
  selectedPoiId?: string | null
  actionState?: PoiActionState
  onSelect?: (poiId: string) => void
}

export function PoiResults({
  results,
  selectedPoiId = null,
  actionState = 'IDLE',
  onSelect,
}: PoiResultsProps) {
  const [visibleCount, setVisibleCount] = useState(3)

  if (results.length === 0) {
    return null
  }

  return (
    <section className="poi-results" aria-live="polite">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Along your route</p>
          <h2>Suggested stops</h2>
        </div>
        <span className="result-count">{results.length} found</span>
      </div>
      <div className="poi-list">
        {results.slice(0, visibleCount).map((result) => {
          const selected = result.id === selectedPoiId
          const partnerBenefit = result.partner?.benefit ?? result.partnerBenefit
          const partnerScope = result.partner?.benefitScope
          const partnerVerified = result.partner?.verified
          const partnerSource = result.partner?.benefitSource
          const partnerStatus = result.partner?.status ?? 'suggested'
          return (
            <button
              className={`poi-card${selected ? ' poi-card-selected' : ''}`}
              key={result.id}
              type="button"
              aria-pressed={selected}
              onClick={() => onSelect?.(result.id)}
            >
              <span className="poi-card-topline">
                <span className="poi-category">{result.category}</span>
                {result.rating !== undefined && <span>{result.rating.toFixed(1)} / 5</span>}
              </span>
              <strong>{result.name}</strong>
              <span className="poi-tag">{result.tag}</span>
              {result.details && <span className="poi-details">{result.details}</span>}
              {result.keywords?.length ? <span className="poi-amenities">{result.keywords.slice(0, 3).join(' · ')}</span> : null}
              {result.partner?.name && (
                <span className="partner-label">
                  Partner location · {result.partner.name}
                  {partnerVerified ? ' · verified' : ' · unverified'}
                </span>
              )}
              {partnerBenefit && (
                <span className="partner-benefit">{partnerBenefit}</span>
              )}
              {partnerBenefit && (
                <span className="partner-meta">
                  {partnerScope ?? 'scope unavailable'}
                  {partnerSource ? ` · ${partnerSource} offer` : ''}
                </span>
              )}
              {result.partner?.name && (
                <span className={`partner-state partner-state-${partnerStatus}`}>
                  {partnerStatus === 'suggested'
                    ? 'Recommendation'
                    : partnerStatus === 'confirmed'
                      ? 'Added to route'
                      : 'Completed'}
                </span>
              )}
              {result.amenities && result.amenities.length > 0 && (
                <span className="poi-amenities">
                  {result.amenities.join(' · ')}
                </span>
              )}
              {result.estimatedDrivingDetourMinutes !== undefined && (
                <span className="poi-detour">+{Math.round(result.estimatedDrivingDetourMinutes)} min detour</span>
              )}
              {selected && <span className="poi-selected-label">Selected for voice confirmation</span>}
            </button>
          )
        })}
      </div>
      {visibleCount < results.length && (
        <button
          className="poi-reveal-more"
          type="button"
          onClick={() => setVisibleCount((count) => Math.min(count + 3, results.length))}
        >
          Show more cached results
        </button>
      )}
      {actionState === 'CONFIRMATION_PENDING' && (
        <p className="poi-action-message" role="status">
          Say yes to Suzanne to add the selected stop to your route.
        </p>
      )}
      {actionState === 'REROUTING_IN_PROGRESS' && (
        <p className="poi-action-message" role="status">Updating your route through this stop...</p>
      )}
      {actionState === 'REROUTE_SUCCESS' && (
        <p className="poi-action-message" role="status">Route updated successfully.</p>
      )}
      {actionState === 'REROUTE_FAILED' && (
        <p className="poi-action-message poi-action-error" role="alert">
          That stop could not be added. Your previous route is unchanged.
        </p>
      )}
    </section>
  )
}
