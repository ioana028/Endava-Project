// Optional browser acceptance: requires Playwright and Chromium, no new app dependency.
// PLAYWRIGHT_MODULE_PATH may point to the bundled Playwright package.
import assert from 'node:assert/strict'
import { createRequire } from 'node:module'
const require = createRequire(import.meta.url)
const { chromium } = require(process.env.PLAYWRIGHT_MODULE_PATH || 'playwright')
const frontend = process.env.TEST_FRONTEND_URL || 'http://127.0.0.1:5173'
const backend = process.env.TEST_BACKEND_URL || 'http://127.0.0.1:8001'
const browser = await chromium.launch({ headless: true, channel: process.env.TEST_BROWSER_CHANNEL || 'msedge', args: [
  '--use-fake-device-for-media-stream', '--use-fake-ui-for-media-stream',
] })
try {
  const page = await browser.newPage()
  await page.route(`${frontend}/`, route => route.fulfill({ contentType: 'text/html', body: '<html><body><div id="root"></div></body></html>' }))
  await page.goto(frontend)
  await page.evaluate(async () => {
    window.sent = []; window.requests = []; window.tracks = []; window.jingles = 0
    class AudioMock extends EventTarget {
      constructor(src) { super(); this.src = src }
      play() {
        if (this.src) { window.jingles++; setTimeout(() => this.dispatchEvent(new Event('ended')), 30) }
        return Promise.resolve()
      }
      pause() { this.dispatchEvent(new Event('pause')) }
      remove() {}
    }
    window.Audio = AudioMock
    Object.defineProperty(navigator.mediaDevices, 'getUserMedia', { value: async () => {
      const track = { enabled: true, stopped: false, stop() { this.stopped = true } }
      window.tracks.push(track)
      return { getTracks: () => [track], getAudioTracks: () => [track] }
    } })
    class Channel extends EventTarget {
      readyState = 'connecting'
      send(value) { window.sent.push(JSON.parse(value)) }
      close() { this.readyState = 'closed'; this.dispatchEvent(new Event('close')) }
      emit(event) { this.onmessage?.({ data: JSON.stringify(event) }) }
    }
    window.RTCPeerConnection = class {
      iceGatheringState = 'gathering'
      addTrack() {}
      createDataChannel() { this.channel = new Channel(); window.channel = this.channel; return this.channel }
      async createOffer() { return { type: 'offer', sdp: 'v=0\r\nm=audio 9 UDP/TLS/RTP/SAVPF 111\r\nm=application 9 UDP/DTLS/SCTP webrtc-datachannel\r\n' } }
      async setLocalDescription(offer) { this.localDescription = offer }
      async setRemoteDescription() {
        this.channel.readyState = 'open'; this.channel.onopen?.(); this.channel.dispatchEvent(new Event('open'))
      }
      close() { this.channel?.close() }
    }
    window.routeResult = { origin: 'Vienna', destination: 'Budapest', stats: {
      totalDistanceKm: 243, drivingDurationMinutes: 165, totalDurationMinutes: 165, totalPriceEur: 0,
    }, geometry: [], stops: [], alerts: [], chargingOptions: [],
      routeRequirements: [{ id: 'hungarian-motorway-vignette', name: 'Hungarian motorway vignette', country: 'HU', kind: 'vignette' }],
    }
    window.fetch = async (url, options) => {
      window.requests.push({ url: String(url), body: options?.body })
      if (String(url).endsWith('/realtime/call')) return new Response('v=0\r\nm=audio 9 UDP/TLS/RTP/SAVPF 111\r\n')
      if (String(url).endsWith('/plan-route')) {
        await new Promise(resolve => { window.resolvePlan = resolve })
        return Response.json({ route: window.routeResult, routeId: 'route1' })
      }
      if (String(url).endsWith('/purchase-vignette')) return Response.json({
        status: 'completed', routeId: 'route1', requirementId: 'hungarian-motorway-vignette',
        transactionId: 'txn1', walletStatus: 'completed', amountEur: 16.5, currency: 'EUR',
        sessionFacts: { chargingPlanConfirmed: false, confirmedChargingStopIds: [],
          purchasedVignetteRequirementIds: ['hungarian-motorway-vignette'], remainingRequirements: [] },
      })
      if (String(url).endsWith('/reroute-through-poi')) return Response.json({ routeId: 'route2', route: {
        ...window.hook.response.route,
        stats: { ...window.hook.response.route.stats, drivingDurationMinutes: 173 },
        stops: [...window.hook.response.route.stops, { id: 'view1', name: 'River Viewpoint', category: 'attraction', coords: [17, 48] }],
      } })
      if (String(url).endsWith('/confirm-charging-stop')) {
        const stop = { id: 'charger1', name: 'Route Charger', category: 'charging', coords: [17, 48], chargingDurationMinutes: 25 }
        return Response.json({ route: { ...window.routeResult, chargingStop: stop, stops: [stop],
          chargingPlan: { stops: [stop], complete: true, confirmed: true, totalChargingMinutes: 25 } },
          routeId: 'route1', selectedStopName: stop.name, radiusMeters: 500, amenitiesAvailable: true,
          results: window.emptyAmenities ? [] : [{ id: 'cafe1', name: 'Cafe', category: 'coffee', coords: [17, 48] }],
        })
      }
      throw new Error(`Unexpected request: ${url}`)
    }
    const reactModule = await import('/node_modules/.vite/deps/react.js')
    const React = reactModule.default ?? reactModule
    const clientModule = await import('/node_modules/.vite/deps/react-dom_client.js')
    const { createRoot } = clientModule.default ?? clientModule
    const { useRealtimeAssistant } = await import('/src/features/assistant/hooks/useRealtimeAssistant.ts')
    function Probe() { window.hook = useRealtimeAssistant(); return React.createElement('span', null, window.hook.state) }
    window.root = createRoot(document.getElementById('root'))
    window.root.render(React.createElement(Probe))
  })
  await page.waitForFunction(() => window.hook)
  await page.evaluate(() => window.hook.enable())
  await page.waitForFunction(() => window.hook.enabled)
  assert.equal(await page.evaluate(() => window.jingles), 1)
  assert.equal(await page.evaluate(() => window.tracks.at(-1).enabled), true)
  assert.deepEqual(await page.evaluate(() => window.requests.map(r => new URL(r.url).pathname)), ['/api/assistant/realtime/call'])
  await page.evaluate(() => {
    window.channel.emit({ type: 'input_audio_buffer.committed' })
    window.channel.emit({ type: 'response.created', response: { id: 'ack1' } })
    window.channel.emit({ type: 'output_audio_buffer.started', response_id: 'ack1' })
    const event = { type: 'response.function_call_arguments.done', call_id: 'plan1', name: 'plan_route',
      arguments: JSON.stringify({ destination: 'Budapest', priority: 'FASTEST' }) }
    window.channel.emit(event); window.channel.emit(event)
    window.channel.emit({ type: 'response.done', response: { id: 'ack1', status: 'cancelled', output: [{ content: [{ type: 'audio' }] }] } })
    window.channel.emit({ type: 'output_audio_buffer.stopped', response_id: 'ack1' })
  })
  await page.waitForFunction(() => window.resolvePlan)
  assert.equal(await page.evaluate(() => window.hook.state), 'PROCESSING')
  assert.equal(await page.evaluate(() => window.sent.filter(e => e.type === 'response.create').length), 1)
  assert.equal(await page.evaluate(() => window.requests.filter(r => r.url.endsWith('/plan-route')).length), 1)
  await page.evaluate(() => window.resolvePlan())
  await page.waitForFunction(() => window.sent.filter(e => e.type === 'response.create').length === 2)
  const facts = await page.evaluate(() => JSON.parse(window.sent.find(e => e.item?.call_id === 'plan1').item.output))
  assert.equal(facts.routeRequirements[0].id, 'hungarian-motorway-vignette')
  assert.equal(await page.evaluate(() => window.hook.response.route.destination), 'Budapest')
  await page.evaluate(() => {
    window.channel.emit({ type: 'response.created', response: { id: 'route-result' } })
    window.channel.emit({ type: 'output_audio_buffer.started', response_id: 'route-result' })
    window.channel.emit({ type: 'response.done', response: { id: 'route-result', status: 'completed', output: [{ content: [{ type: 'audio' }] }] } })
  })
  assert.equal(await page.evaluate(() => window.hook.state), 'SPEAKING')
  await page.evaluate(() => window.channel.emit({ type: 'output_audio_buffer.stopped', response_id: 'route-result' }))
  await page.waitForFunction(() => window.hook.state === 'LISTENING')
  await page.evaluate(() => {
    window.channel.emit({ type: 'input_audio_buffer.committed' })
    window.channel.emit({ type: 'response.created', response: { id: 'buy-request' } })
    window.channel.emit({ type: 'response.function_call_arguments.done', call_id: 'buy1', name: 'purchase_vignette',
      arguments: JSON.stringify({ routeId: 'route1', confirmation: 'confirmed' }) })
    window.channel.emit({ type: 'response.done', response: { id: 'buy-request', status: 'cancelled', output: [] } })
  })
  await page.waitForFunction(() => window.hook.purchase?.status === 'completed')
  assert.deepEqual(await page.evaluate(() => window.hook.response.route.sessionFacts.remainingRequirements), [])
  assert.match(await page.evaluate(() => window.sent.filter(e => e.type === 'response.create').at(-1).response.instructions), /Say only "Got it\."/)
  await page.evaluate(() => {
    window.channel.emit({ type: 'response.created', response: { id: 'purchase-ack' } })
    window.channel.emit({ type: 'response.done', response: { id: 'purchase-ack', status: 'completed', output: [{ content: [{ type: 'audio' }] }] } })
    window.channel.emit({ type: 'output_audio_buffer.stopped', response_id: 'purchase-ack' })
  })
  assert.match(await page.evaluate(() => window.sent.filter(e => e.type === 'response.create').at(-1).response.instructions), /Never separately narrate walletStatus/)
  await page.evaluate(() => {
    window.channel.emit({ type: 'response.created', response: { id: 'purchase-result' } })
    window.channel.emit({ type: 'response.done', response: { id: 'purchase-result', status: 'completed', output: [{ content: [{ type: 'audio' }] }] } })
    window.channel.emit({ type: 'output_audio_buffer.stopped', response_id: 'purchase-result' })
    window.channel.emit({ type: 'input_audio_buffer.committed' })
    window.channel.emit({ type: 'response.created', response: { id: 'poi-ack' } })
    window.channel.emit({ type: 'output_audio_buffer.started', response_id: 'poi-ack' })
    window.channel.emit({ type: 'response.function_call_arguments.done', call_id: 'poi1', name: 'reroute_through_poi',
      arguments: JSON.stringify({ poi_id: 'view1', routeId: 'route1', searchId: 'search1', confirmation: 'confirmed' }) })
    window.channel.emit({ type: 'response.done', response: { id: 'poi-ack', status: 'cancelled', output: [{ content: [{ type: 'audio' }] }] } })
    window.channel.emit({ type: 'output_audio_buffer.stopped', response_id: 'poi-ack' })
  })
  await page.waitForFunction(() => window.sent.some(e => e.item?.call_id === 'poi1'))
  const update = await page.evaluate(() => JSON.parse(window.sent.find(e => e.item?.call_id === 'poi1').item.output).updateFacts)
  assert.equal(update.travelTimeChangeMinutes, 8)
  assert.deepEqual(update.addedPlaces, [{ name: 'River Viewpoint', category: 'attraction' }])
  assert.match(await page.evaluate(() => window.sent.filter(e => e.type === 'response.create').at(-1).response.instructions), /Use only updateFacts/)
  await page.evaluate(() => window.hook.disable())
  await page.waitForFunction(() => !window.hook.enabled)
  await page.evaluate(() => window.hook.enable())
  await page.waitForFunction(() => window.hook.enabled)
  assert.equal(await page.evaluate(() => window.jingles), 1)
  assert.equal(await page.evaluate(() => window.tracks[0].stopped), true)

  for (const empty of [false, true]) {
    const suffix = empty ? 'empty' : 'nearby'
    await page.evaluate(({ empty, suffix }) => {
      window.emptyAmenities = empty
      window.channel.emit({ type: 'input_audio_buffer.committed' })
      window.channel.emit({ type: 'response.created', response: { id: `charging-ack-${suffix}` } })
      window.channel.emit({ type: 'output_audio_buffer.started', response_id: `charging-ack-${suffix}` })
      window.channel.emit({ type: 'response.function_call_arguments.done', call_id: `charge-${suffix}`, name: 'confirm_charging_stop',
        arguments: JSON.stringify({ routeId: 'route1', confirmation: 'confirmed' }) })
    }, { empty, suffix })
    await page.waitForFunction(suffix => window.sent.some(e => e.item?.call_id === `charge-${suffix}`), suffix)
    assert.equal(await page.evaluate(() => window.hook.chargingStopFocus), null)
    assert.equal(await page.evaluate(() => window.hook.response.route.stops[0].id), 'charger1')
    await page.evaluate(suffix => {
      window.channel.emit({ type: 'response.done', response: { id: `charging-ack-${suffix}`, status: 'cancelled', output: [{ content: [{ type: 'audio' }] }] } })
      window.channel.emit({ type: 'output_audio_buffer.stopped', response_id: `charging-ack-${suffix}` })
      window.channel.emit({ type: 'response.created', response: { id: `charging-result-${suffix}` } })
      window.channel.emit({ type: 'output_audio_buffer.started', response_id: `charging-result-${suffix}` })
      window.channel.emit({ type: 'response.done', response: { id: `charging-result-${suffix}`, status: 'completed', output: [{ content: [{ type: 'audio' }] }] } })
    }, suffix)
    assert.equal(await page.evaluate(() => window.hook.chargingStopFocus), null)
    await page.evaluate(suffix => {
      window.channel.emit({ type: 'output_audio_buffer.stopped', response_id: `charging-result-${suffix}` })
      window.channel.emit({ type: 'response.created', response: { id: `amenities-${suffix}` } })
      window.channel.emit({ type: 'output_audio_buffer.started', response_id: `amenities-${suffix}` })
    }, suffix)
    assert.match(await page.evaluate(() => window.sent.filter(e => e.type === 'response.create').at(-1).response.instructions), /never repeat the charger name/)
    await page.waitForFunction(empty => empty ? window.hook.chargingStopFocus === null : window.hook.chargingStopFocus?.id === 'charger1', empty)
    await page.evaluate(suffix => window.channel.emit({ type: 'response.done', response: {
      id: `amenities-${suffix}`, status: 'completed', output: [{ content: [{ type: 'audio' }] }],
    } }), suffix)
    assert.equal(await page.evaluate(() => window.hook.chargingStopFocus?.id ?? null), empty ? null : 'charger1')
    await page.evaluate(suffix => window.channel.emit({ type: 'output_audio_buffer.stopped', response_id: `amenities-${suffix}` }), suffix)
    await page.waitForFunction(() => window.hook.chargingStopFocus === null && window.hook.state === 'LISTENING')
  }
  await page.evaluate(() => { window.hook.disable(); window.root.unmount() })
  console.log('PASS: mounted hook, unified startup without ICE wait, single jingle, tool deduplication, processing silence, result playback, vignette context/state, reconnect cleanup, charger overview/amenities playback focus, no-results no-zoom')

  if (process.env.LIVE_REALTIME === '1') {
    const live = await browser.newPage()
    await live.route(`${frontend}/`, route => route.fulfill({ contentType: 'text/html', body: '<html><body>Voice handshake test</body></html>' }))
    await live.goto(frontend)
    const started = Date.now()
    const offer = await live.evaluate(async () => {
      window.livePeer = new RTCPeerConnection()
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      window.liveStream = stream
      stream.getTracks().forEach(track => { track.enabled = false; window.livePeer.addTrack(track, stream) })
      window.liveChannel = window.livePeer.createDataChannel('oai-events')
      window.liveErrors = []
      window.liveChannel.onmessage = message => {
        const event = JSON.parse(message.data)
        if (event.type === 'error') window.liveErrors.push(event.error?.message)
        if (event.type === 'session.created') window.liveSession = event.session
      }
      const offer = await window.livePeer.createOffer()
      await window.livePeer.setLocalDescription(offer)
      return offer.sdp
    })
    const response = await live.request.post(`${backend}/api/assistant/realtime/call`, {
      data: offer, headers: { 'Content-Type': 'application/sdp' }, timeout: 20_000,
    })
    assert.equal(response.status(), 200, `Live call failed: ${await response.text()}`)
    const callMs = Date.now() - started
    await live.evaluate(answer => window.livePeer.setRemoteDescription({ type: 'answer', sdp: answer }), await response.text())
    await live.waitForFunction(() => window.liveChannel.readyState === 'open' && window.liveSession, { timeout: 20_000 })
    assert.deepEqual(await live.evaluate(() => window.liveErrors), [])
    assert.equal(await live.evaluate(() => window.liveSession.audio.input.turn_detection.create_response), false)
    console.log(`PASS: live configured Realtime WebRTC handshake; call+offer=${callMs}ms; ready=${Date.now() - started}ms; no real microphone or Google calls`)
    await live.evaluate(() => { window.liveChannel.close(); window.livePeer.close(); window.liveStream.getTracks().forEach(t => t.stop()) })
  }
} finally {
  await browser.close()
}
