import { AssistantStatus } from './features/assistant/components/AssistantStatus'
import { PoiResults } from './features/assistant/components/PoiResults'
import { useRealtimeAssistant } from './features/assistant/hooks/useRealtimeAssistant'
import { RouteMap } from './features/map/components/RouteMap'
import { RouteSummary } from './features/trip/components/RouteSummary'

function App() {
  const assistant = useRealtimeAssistant()

  const route = assistant.response?.route

  return (
    <main>
      <header className="app-header">
        <div>
          <p className="eyebrow">Mobility concierge</p>
          <h1>Suzanne</h1>
          <p className="header-subtitle">Your route, thoughtfully handled.</p>
        </div>
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
          <RouteMap
            route={route}
            poiResults={assistant.poiResults}
            selectedPoiId={assistant.selectedPoi?.id}
            onPoiSelect={assistant.selectPoi}
          />
          <RouteSummary route={route} />
        </>
      )}

      <PoiResults
        results={assistant.poiResults}
        selectedPoiId={assistant.selectedPoi?.id}
        actionState={assistant.poiActionState}
        onSelect={assistant.selectPoi}
      />

    </main>
  )
}

export default App
