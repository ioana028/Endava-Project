import test from 'node:test'
import assert from 'node:assert/strict'
import { compactPoiUpdateFacts, AMENITIES_RESULT_INSTRUCTIONS, POI_UPDATE_INSTRUCTIONS, VIGNETTE_RESULT_INSTRUCTIONS } from '../src/features/assistant/actionNarration.ts'

const vignette = { id: 'hu', name: 'Hungarian vignette', country: 'HU', kind: 'vignette' }
function route(minutes = 150, extra = {}) {
  return { stats: { drivingDurationMinutes: minutes }, stops: [{ id: 'charger', name: 'Charger', category: 'charging' }],
    routeRequirements: [vignette], telemetry: { chargingFeasible: true }, ...extra }
}

test('POI narration reports the driving-time delta, not a route summary', () => {
  const before = route()
  const after = route(158, { stops: [...before.stops, { id: 'view', name: 'River viewpoint', category: 'attraction' }] })
  assert.deepEqual(compactPoiUpdateFacts(before, after), { status: 'success',
    addedPlaces: [{ name: 'River viewpoint', category: 'attraction' }], travelTimeChangeMinutes: 8, newRequirements: [] })
})

test('POI narration preserves zero and negative deltas', () => {
  assert.equal(compactPoiUpdateFacts(route(), route()).travelTimeChangeMinutes, 0)
  assert.equal(compactPoiUpdateFacts(route(), route(147)).travelTimeChangeMinutes, -3)
})

test('missing baseline cannot invent added time or new requirements', () => {
  const facts = compactPoiUpdateFacts(undefined, route())
  assert.equal(facts.travelTimeChangeMinutes, undefined)
  assert.deepEqual(facts.newRequirements, [])
})

test('only genuinely changed requirements and feasibility are narrated', () => {
  const newRequirement = { id: 'at', name: 'Austrian vignette', country: 'AT', kind: 'vignette' }
  const facts = compactPoiUpdateFacts(route(), route(153, { routeRequirements: [vignette, newRequirement], telemetry: { chargingFeasible: false } }))
  assert.deepEqual(facts.newRequirements, [{ name: 'Austrian vignette', country: 'AT', kind: 'vignette' }])
  assert.equal(facts.chargingFeasibilityChanged, false)
})

test('action speech excludes repeated wallet, charger and route summaries', () => {
  assert.match(VIGNETTE_RESULT_INSTRUCTIONS, /Your vignette is purchased/)
  assert.match(VIGNETTE_RESULT_INSTRUCTIONS, /already purchased/)
  assert.match(VIGNETTE_RESULT_INSTRUCTIONS, /phoneConfirmationStatus simulated_sent/)
  assert.match(VIGNETTE_RESULT_INSTRUCTIONS, /confirmation has been sent to your phone/)
  assert.match(VIGNETTE_RESULT_INSTRUCTIONS, /Do not imply a new purchase or another notification for a duplicate/)
  assert.match(VIGNETTE_RESULT_INSTRUCTIONS, /Never separately narrate walletStatus/)
  assert.match(AMENITIES_RESULT_INSTRUCTIONS, /those places and their own verified partner benefits/)
  assert.match(AMENITIES_RESULT_INSTRUCTIONS, /never repeat the charger name/)
  assert.match(POI_UPDATE_INSTRUCTIONS, /Never repeat the complete route summary/)
})
