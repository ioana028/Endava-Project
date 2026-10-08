import test from 'node:test'
import assert from 'node:assert/strict'
import { serializeMapRoute, routePathChanged } from '../src/features/map/utils/mapRouteView.ts'

function route(extra = {}) {
  return { origin: 'Vienna', destination: 'Budapest', geometry: [[16, 48], [19, 47]],
    stops: [], stats: { drivingDurationMinutes: 165, totalDurationMinutes: 165 },
    routeStatus: 'ROUTE_READY', sessionFacts: { remainingRequirements: ['hu'] }, ...extra }
}

test('vignette purchase and cloned metadata leave the map view unchanged', () => {
  const before = route()
  const after = structuredClone(before)
  after.sessionFacts = { remainingRequirements: [], purchasedVignetteRequirementIds: ['hu'] }
  after.routeStatus = 'CHARGING_OPTIONS_READY'
  assert.equal(serializeMapRoute(before), serializeMapRoute(after))
})
test('real geometry changes trigger route drawing regardless of route status', () => {
  const before = JSON.parse(serializeMapRoute(route()))
  const after = JSON.parse(serializeMapRoute(route({ geometry: [[16, 48], [17, 48], [19, 47]], routeStatus: 'REROUTING' })))
  assert.equal(routePathChanged(before, after), true)
  assert.equal(routePathChanged(null, after), true)
})
test('new stop on the same path updates markers without replaying the whole route', () => {
  const before = route()
  const after = route({ stops: [{ id: 'view', name: 'View', category: 'attraction', coords: [17, 48] }] })
  assert.notEqual(serializeMapRoute(before), serializeMapRoute(after))
  assert.equal(routePathChanged(JSON.parse(serializeMapRoute(before)), JSON.parse(serializeMapRoute(after))), false)
})
test('duration changes update the callout; route removal clears the map', () => {
  assert.notEqual(serializeMapRoute(route()), serializeMapRoute(route({ stats: { drivingDurationMinutes: 172, totalDurationMinutes: 172 } })))
  assert.equal(serializeMapRoute(undefined), undefined)
})
