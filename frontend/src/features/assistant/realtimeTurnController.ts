type Event = Record<string, unknown>
type Purpose = 'user' | 'acknowledgement' | 'result'
type Turn = {
  id: string | null
  purpose: Purpose
  generationDone: boolean
  audioExpected: boolean
  audioStopped: boolean
  status: string
}

/** WebRTC generation and speaker playback finish independently. Never overlap them. */
export class RealtimeTurnController {
  private send: (event: Event) => void
  private settled: (id: string, status: string) => void
  private active: Turn | null = null
  private queue: Array<{ event: Event; purpose: Purpose }> = []
  private calls = new Set<string>()
  private pendingTool: string | null = null
  private deferredUser = false
  private userSpeaking = false

  constructor(send: (event: Event) => void, settled: (id: string, status: string) => void) {
    this.send = send
    this.settled = settled
  }

  isResult(id: string) { return this.active?.id === id && this.active.purpose === 'result' }

  request(event: Event, purpose: Purpose) {
    if (purpose === 'user' && (this.pendingTool || this.active || this.queue.length)) {
      this.deferredUser = true
      return
    }
    const response = (event.response ?? {}) as Event
    this.queue.push({
      event: purpose !== 'user'
        ? { ...event, response: { ...response, tool_choice: 'none' } }
        : event,
      purpose,
    })
    this.flush()
  }

  beginTool(callId: string, toolName?: string): 'accepted' | 'duplicate' | 'busy' {
    if (this.calls.has(callId)) return 'duplicate'
    this.calls.add(callId)
    if (this.pendingTool) return 'busy'
    this.pendingTool = callId
    if (!this.active?.audioExpected) {
      // Some model turns call a tool without any speech. Supply one acknowledgement,
      // in the same voice, before the result; never narrate speculative progress.
      this.queue.unshift({ purpose: 'acknowledgement', event: {
        type: 'response.create', response: { tool_choice: 'none',
          instructions: toolName === 'purchase_vignette'
            ? 'Say only "Got it." This is an acknowledgement, not a result. Do not add anything else.'
            : 'Say only "I\'ll check that for you." This is an acknowledgement, not a result. Do not add progress updates, tool calls, or factual claims.',
        },
      } })
    }
    // Keep already-buffered acknowledgement audio, but stop further progress chatter.
    if (this.active?.id && !this.active.generationDone) {
      this.send({ type: 'response.cancel', response_id: this.active.id })
    }
    this.flush()
    return 'accepted'
  }

  finishTool(callId: string) {
    if (this.pendingTool !== callId) return
    this.pendingTool = null
    this.flush()
  }

  handle(event: Event) {
    const response = event.response as { id?: string; status?: string; output?: Array<{ content?: Array<{ type?: string }> }> } | undefined
    if (event.type === 'input_audio_buffer.speech_started') {
      this.userSpeaking = true
    } else if (event.type === 'input_audio_buffer.speech_stopped') {
      // Wait for committed: it guarantees the user message exists in the conversation.
    } else if (event.type === 'input_audio_buffer.committed') {
      this.userSpeaking = false
      this.request({ type: 'response.create' }, 'user')
    } else if (event.type === 'response.created' && response?.id) {
      if (this.active?.id === null) {
        this.active.id = response.id
      } else {
        // Automatic/unsolicited responses are never allowed during an app-owned turn.
        this.send({ type: 'response.cancel', response_id: response.id })
        return
      }
    } else if (this.active && (event.response_id === this.active.id || response?.id === this.active.id)) {
      if (event.type === 'output_audio_buffer.started' || event.type === 'response.output_audio.done' || event.type === 'response.output_audio.delta' || event.type === 'response.output_audio_transcript.delta') {
        this.active.audioExpected = true
      } else if (event.type === 'output_audio_buffer.stopped' || event.type === 'output_audio_buffer.cleared') {
        this.active.audioStopped = true
        if (event.type === 'output_audio_buffer.cleared') this.active.status = 'cancelled'
      } else if (event.type === 'response.done') {
        this.active.generationDone = true
        if (this.active.status !== 'cancelled') this.active.status = response?.status ?? 'failed'
        this.active.audioExpected ||= Boolean(response?.output?.some(item =>
          item.content?.some(content => content.type === 'audio' || content.type === 'output_audio'),
        ))
      }
    }
    const turn = this.active
    if (turn?.id && turn.generationDone && (!turn.audioExpected || turn.audioStopped)) {
      this.active = null
      this.settled(turn.id, turn.status)
    }
    this.flush()
  }

  reset() {
    this.active = null
    this.queue = []
    this.calls.clear()
    this.pendingTool = null
    this.deferredUser = false
    this.userSpeaking = false
  }

  private flush() {
    if (this.active || this.userSpeaking) return
    if (this.pendingTool && this.queue[0]?.purpose !== 'acknowledgement') return
    if (!this.queue.length && this.deferredUser) {
      this.deferredUser = false
      this.queue.push({ event: { type: 'response.create' }, purpose: 'user' })
    }
    const next = this.queue.shift()
    if (!next) return
    this.active = { id: null, purpose: next.purpose, generationDone: false, audioExpected: false, audioStopped: false, status: 'in_progress' }
    this.send(next.event)
  }
}
