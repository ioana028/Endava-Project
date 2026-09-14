import type { StopPinpoint } from '../../../types/contracts'

interface PoiResultsProps {
  results: StopPinpoint[]
}

export function PoiResults({ results }: PoiResultsProps) {
  if (results.length === 0) {
    return null
  }

  return (
    <section aria-live="polite">
      <h2>Route suggestions</h2>
      {results.map((result) => (
        <article key={result.id}>
          <h3>{result.name}</h3>
          <p>{result.category}</p>
          {result.rating !== undefined && <p>Rating: {result.rating}</p>}
          <p>{result.detourMinutes} min detour</p>
          <p>{result.tag}</p>
        </article>
      ))}
    </section>
  )
}
