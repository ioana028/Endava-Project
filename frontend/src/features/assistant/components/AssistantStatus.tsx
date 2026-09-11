import type { AssistantState } from '../hooks/useVoiceAssistant'

interface AssistantStatusProps {
  enabled: boolean
  state: AssistantState
  transcript: string
  error: string | null
  onEnable: () => void
}

export function AssistantStatus({
  enabled,
  state,
  transcript,
  error,
  onEnable,
}: AssistantStatusProps) {
  return (
    <section aria-live="polite">
      {!enabled && (
        <button type="button" onClick={onEnable}>
          Enable Suzanne
        </button>
      )}

      <p>Assistant state: {state}</p>

      {enabled && state === 'IDLE' && (
        <p>Say “Hey Suzanne” when you need help.</p>
      )}

      {state === 'LISTENING' && (
        <>
          <h2>Listening</h2>
          <p>{transcript || "I'm listening..."}</p>
        </>
      )}

      {state === 'PROCESSING' && (
        <>
          <h2>Planning route</h2>
          <p>Calculating your route...</p>
        </>
      )}

      {error && <p role="alert">{error}</p>}
    </section>
  )
}
