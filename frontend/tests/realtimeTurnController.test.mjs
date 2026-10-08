import test from 'node:test'
import assert from 'node:assert/strict'
import { RealtimeTurnController } from '../src/features/assistant/realtimeTurnController.ts'

function setup() {
  const sent = [], settled = []
  const controller = new RealtimeTurnController(e => sent.push(e), (id, status) => settled.push({ id, status }))
  return { controller, sent, settled }
}
function create(c, id) { c.handle({ type: 'response.created', response: { id } }) }
function done(c, id, audio = true, status = 'completed') {
  c.handle({ type: 'response.done', response: { id, status,
    output: audio ? [{ content: [{ type: 'audio' }] }] : [],
  } })
}
function playback(c, type, id) { c.handle({ type: `output_audio_buffer.${type}`, response_id: id }) }
const result = { type: 'response.create', response: { instructions: 'Speak the verified result.' } }

test('tool-only vignette purchase acknowledges with Got it, once', () => {
  const { controller: c, sent } = setup()
  c.request({ type: 'response.create' }, 'user'); create(c, 'tool')
  c.beginTool('purchase1', 'purchase_vignette')
  c.request(result, 'result'); c.finishTool('purchase1')
  done(c, 'tool', false, 'cancelled')
  assert.match(sent.at(-1).response.instructions, /Say only "Got it\."/)
  create(c, 'ack'); done(c, 'ack'); playback(c, 'stopped', 'ack')
  assert.equal(sent.at(-1).response.instructions, result.response.instructions)
  assert.equal(sent.filter(e => e.type === 'response.create').length, 3)
})

for (const order of ['generation-first', 'playback-first']) {
  test(`result waits for acknowledgement generation AND playback (${order})`, () => {
    const { controller: c, sent } = setup()
    c.request({ type: 'response.create' }, 'user'); create(c, 'ack')
    playback(c, 'started', 'ack')
    assert.equal(c.beginTool('call1'), 'accepted')
    c.request(result, 'result'); c.finishTool('call1')
    assert.equal(sent.filter(e => e.type === 'response.create').length, 1)
    if (order === 'generation-first') { done(c, 'ack'); playback(c, 'stopped', 'ack') }
    else { playback(c, 'stopped', 'ack'); done(c, 'ack') }
    assert.equal(sent.filter(e => e.type === 'response.create').length, 2)
    assert.equal(sent.at(-1).response.tool_choice, 'none')
  })
}
test('slow tool stays silent after acknowledgement when another VAD turn commits', () => {
  const { controller: c, sent } = setup()
  c.request({ type: 'response.create' }, 'user'); create(c, 'ack')
  playback(c, 'started', 'ack'); c.beginTool('call1')
  done(c, 'ack'); playback(c, 'stopped', 'ack')
  c.handle({ type: 'input_audio_buffer.committed' })
  assert.equal(sent.filter(e => e.type === 'response.create').length, 1)
  c.request(result, 'result'); c.finishTool('call1')
  assert.equal(sent.at(-1).response.instructions, result.response.instructions)
  create(c, 'result'); done(c, 'result'); playback(c, 'stopped', 'result')
  assert.deepEqual(sent.at(-1), { type: 'response.create' })
})
test('tool-only turns get exactly one acknowledgement before the result', () => {
  const { controller: c, sent } = setup()
  c.request({ type: 'response.create' }, 'user'); create(c, 'tool')
  c.beginTool('call1'); c.request(result, 'result'); c.finishTool('call1')
  done(c, 'tool', false, 'cancelled')
  assert.match(sent.at(-1).response.instructions, /acknowledgement/)
  create(c, 'ack'); done(c, 'ack'); playback(c, 'stopped', 'ack')
  assert.equal(sent.at(-1).response.instructions, result.response.instructions)
  assert.equal(sent.filter(e => e.type === 'response.create').length, 3)
})
test('generated acknowledgement avoids a second one before playback starts', () => {
  const { controller: c, sent } = setup()
  c.request({ type: 'response.create' }, 'user'); create(c, 'tool')
  c.handle({ type: 'response.output_audio_transcript.delta', response_id: 'tool', delta: "I'll check." })
  c.beginTool('call1'); c.request(result, 'result'); c.finishTool('call1')
  done(c, 'tool'); playback(c, 'stopped', 'tool')
  assert.equal(sent.filter(e => e.type === 'response.create').length, 2)
})
test('duplicate calls are ignored and concurrent distinct mutations are rejected', () => {
  const { controller: c } = setup()
  assert.equal(c.beginTool('call1'), 'accepted')
  assert.equal(c.beginTool('call1'), 'duplicate')
  assert.equal(c.beginTool('call2'), 'busy')
})
test('stale completions and unsolicited responses cannot advance the queue', () => {
  const { controller: c, sent, settled } = setup()
  c.request(result, 'result'); create(c, 'current'); c.request(result, 'result')
  done(c, 'old', false); playback(c, 'stopped', 'old'); create(c, 'unsolicited')
  assert.equal(sent.at(-1).type, 'response.cancel')
  assert.equal(settled.length, 0)
  done(c, 'current'); playback(c, 'stopped', 'current')
  assert.equal(settled.length, 1)
  assert.equal(sent.filter(e => e.type === 'response.create').length, 2)
})
test('cleared audio settles as cancelled in either event order', () => {
  for (const first of ['done', 'cleared']) {
    const { controller: c, settled } = setup()
    c.request(result, 'result'); create(c, 'r'); playback(c, 'started', 'r')
    if (first === 'done') { done(c, 'r'); playback(c, 'cleared', 'r') }
    else { playback(c, 'cleared', 'r'); done(c, 'r') }
    assert.deepEqual(settled, [{ id: 'r', status: 'cancelled' }])
  }
})
test('no response starts between speech_stopped and input commit', () => {
  const { controller: c, sent } = setup()
  c.handle({ type: 'input_audio_buffer.speech_started' }); c.request(result, 'result')
  c.handle({ type: 'input_audio_buffer.speech_stopped' })
  assert.equal(sent.length, 0)
  c.handle({ type: 'input_audio_buffer.committed' })
  assert.equal(sent.at(-1).response.tool_choice, 'none')
})
test('reset discards pending work and late events from the closed session', () => {
  const { controller: c, sent } = setup()
  c.request(result, 'result'); create(c, 'old'); c.request(result, 'result')
  c.reset(); done(c, 'old'); playback(c, 'stopped', 'old')
  assert.equal(sent.length, 1)
  c.request(result, 'result'); assert.equal(sent.length, 2)
})
test('charging continuation waits for actual speaker completion', () => {
  const sent = [], stages = []
  const c = new RealtimeTurnController(e => sent.push(e), id => {
    stages.push(id)
    if (id === 'charger') c.request({ type: 'response.create', response: { instructions: 'Nearby you have...' } }, 'result')
  })
  c.request(result, 'result'); create(c, 'charger'); playback(c, 'started', 'charger')
  done(c, 'charger'); assert.equal(sent.length, 1)
  playback(c, 'stopped', 'charger'); assert.equal(sent.length, 2)
  create(c, 'amenities'); done(c, 'amenities'); assert.deepEqual(stages, ['charger'])
  playback(c, 'stopped', 'amenities'); assert.deepEqual(stages, ['charger', 'amenities'])
})
