import { AssistantStatus } from './features/assistant/components/AssistantStatus'
import { useRealtimeAssistant } from './features/assistant/hooks/useRealtimeAssistant'
import { RouteMap } from './features/map/components/RouteMap'
import { RouteSummary } from './features/trip/components/RouteSummary'

function App() {
  const assistant = useRealtimeAssistant()

  const route = assistant.response?.route

  return (
    <main>
      <header>
        <h1>Suzanne</h1>
        <p>Voice-first route planning</p>
      </header>

      <AssistantStatus
        enabled={assistant.enabled}
        state={assistant.state}
        transcript={assistant.transcript}
        error={assistant.error}
        onEnable={() => void assistant.enable()}
        onDisable={assistant.disable}
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

    </main>
  )
}

export default App
