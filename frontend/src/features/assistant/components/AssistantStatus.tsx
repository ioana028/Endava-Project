import type { RealtimeAssistantState } from '../hooks/useRealtimeAssistant'

interface AssistantStatusProps {
  enabled: boolean
  state: RealtimeAssistantState
  transcript: string
  error: string | null
  onEnable: () => void
  onDisable: () => void
}

export function AssistantStatus({
  enabled,
  state,
  transcript,
  error,
  onEnable,
  onDisable,
}: AssistantStatusProps) {
  return (
    <section className="assistant-panel" aria-live="polite">
      {!enabled && state !== 'CONNECTING' && (
        <button type="button" onClick={onEnable}>
          Start Suzanne
        </button>
      )}

      {(enabled || state === 'CONNECTING') && (
        <button type="button" onClick={onDisable}>
          Stop Suzanne
        </button>
      )}

      <p className="assistant-state"><span className={`state-dot state-${state.toLowerCase()}`} /> {state}</p>

      {state === 'CONNECTING' && <p>Connecting Suzanne...</p>}

      {enabled && state === 'LISTENING' && (
        <p>Say what you need and Suzanne will help.</p>
      )}

      {state === 'SPEAKING' && (
        <>
          <h2>Suzanne</h2>
          <p>{transcript || 'Speaking...'}</p>
        </>
      )}

      {state === 'PROCESSING' && (
        <>
          <h2>Planning route</h2>
          <p>Calculating your route...</p>
        </>
      )}

      {state === 'ERROR' && <p>Realtime connection needs attention.</p>}

      {error && <p className="error-message" role="alert">{error}</p>}
    </section>
  )
}
