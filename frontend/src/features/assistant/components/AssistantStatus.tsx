import type { RealtimeAssistantState } from '../hooks/useRealtimeAssistant'

interface AssistantStatusProps {
  enabled: boolean
  state: RealtimeAssistantState
  error: string | null
  onEnable: () => void
  onDisable: () => void
}

export function AssistantStatus({
  enabled,
  state,
  error,
  onEnable,
  onDisable,
}: AssistantStatusProps) {
  const stateLabel = {
    IDLE: 'Ready',
    CONNECTING: 'Connecting',
    LISTENING: 'Listening',
    PROCESSING: 'Working on your request',
    SPEAKING: 'Speaking',
    ERROR: 'Needs attention',
  }[state]

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

      <p className="assistant-state"><span className={`state-dot state-${state.toLowerCase()}`} /> {stateLabel}</p>

      {error && <p className="error-message" role="alert">{error}</p>}
    </section>
  )
}
