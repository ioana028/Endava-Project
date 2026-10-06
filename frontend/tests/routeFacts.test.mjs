import test from 'node:test'
import assert from 'node:assert/strict'
import { compactRouteFacts } from '../src/features/assistant/routeFacts.ts'

const vignette = { id: 'hungarian-motorway-vignette', name: 'Hungarian motorway vignette', country: 'HU', kind: 'vignette' }
function route(extra = {}) {
  return { origin: 'Vienna', destination: 'Budapest', stops: [], alerts: [],
    routeRequirements: [vignette], stats: { totalDistanceKm: 243, drivingDurationMinutes: 165 }, ...extra }
}
test('brief route summary preserves exact operational requirement IDs', () => {
  const facts = compactRouteFacts(route(), { routeId: 'route1' })
  assert.equal(facts.vignetteCount, 1)
  assert.deepEqual(facts.routeRequirements, [vignette])
  assert.equal(facts.routeId, 'route1')
})
test('purchased vignettes are not offered again, including after rerouting', () => {
  const facts = compactRouteFacts(route({ sessionFacts: { remainingRequirements: [] } }))
  assert.deepEqual(facts.routeRequirements, [])
  assert.equal(facts.vignetteCount, undefined)
})
test('confirmed charging is not presented as still requiring action', () => {
  const facts = compactRouteFacts(route({ chargingRequired: true,
    telemetry: { estimatedRangeKm: 95 }, sessionFacts: { chargingPlanConfirmed: true, remainingRequirements: [] } }))
  assert.equal(facts.chargingRequired, undefined)
  assert.equal(facts.chargingPlanReady, false)
})

test('prepared charging plan survives purchase metadata without exposing unconfirmed names', () => {
  const pending = route({ chargingRequired: true, chargingOptions: [
    { status: 'suggested', stop: { id: 'first', name: 'First Charger' } },
    { status: 'suggested', stop: { id: 'second', name: 'Second Charger' } },
  ], sessionFacts: { remainingRequirements: [] } })
  const facts = compactRouteFacts(pending)
  assert.equal(facts.chargingPlanReady, true)
  assert.equal(facts.preparedChargingStopCount, 2)
  assert.equal(facts.chargingAction, 'confirm_charging_stop')
  assert.equal(JSON.stringify(facts).includes('First Charger'), false)
})

test('short routes do not advertise a prepared charger', () => {
  const facts = compactRouteFacts(route({ chargingRequired: false, chargingOptions: [] }))
  assert.equal(facts.chargingPlanReady, false)
  assert.equal(facts.chargingAction, undefined)
})
test('weather summary stays concise without sample counts', () => {
  const facts = compactRouteFacts(route({ alerts: [{ type: 'WEATHER', locationName: 'Route average',
    message: 'Current route conditions: generally clear; average temperature about 23.4°C; 3 samples.' }] }))
  assert.equal(facts.routeWeatherSummary, 'generally clear, around 23°C')
})
