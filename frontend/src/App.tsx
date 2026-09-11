import { AssistantStatus } from './features/assistant/components/AssistantStatus'
import { useVoiceAssistant } from './features/assistant/hooks/useVoiceAssistant'
import { useWakeWord } from './features/assistant/hooks/useWakeWord'
import { RouteMap } from './features/map/components/RouteMap'
import { RouteSummary } from './features/trip/components/RouteSummary'

function App() {
  const assistant = useVoiceAssistant()
  const wakeWord = useWakeWord({
    state: assistant.state,
    startListening: assistant.startListening,
    stopListening: assistant.stopListening,
  })

  const route = assistant.response?.route

  return (
    <main>
      <header>
        <h1>Suzanne</h1>
        <p>Voice-first route planning</p>
      </header>

      <AssistantStatus
        enabled={wakeWord.enabled}
        state={assistant.state}
        transcript={wakeWord.transcript}
        error={wakeWord.error}
        onEnable={() => void wakeWord.enable()}
      />

      {assistant.response && (
        <section aria-live="polite">
          <h2>Final transcript</h2>
          <p>{assistant.response.transcript}</p>
          <h2>Suzanne</h2>
          <p>{assistant.response.spokenResponse}</p>
        </section>
      )}

      {route && (
        <>
          <RouteMap route={route} />
          <RouteSummary route={route} />
        </>
      )}

      {assistant.error && <p role="alert">{assistant.error}</p>}
    </main>
  )
}

export default App
