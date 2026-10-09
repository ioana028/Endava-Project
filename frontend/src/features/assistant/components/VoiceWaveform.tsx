import type { RealtimeAssistantState } from '../hooks/useRealtimeAssistant'

interface VoiceWaveformProps {
  state: RealtimeAssistantState
  bands: number[]
}

const BAR_WEIGHTS = [
  0.28, 0.4, 0.56, 0.72, 0.88, 0.68, 0.46,
  0.62, 0.82, 1, 0.78, 0.58, 0.9, 0.7,
  0.5, 0.74, 0.92, 0.64, 0.44, 0.34, 0.24,
]

export function VoiceWaveform({ state, bands }: VoiceWaveformProps) {
  const responsive = state === 'LISTENING' || state === 'SPEAKING'
  const amplitude = state === 'SPEAKING' ? 42 : 34
  const baseline = state === 'SPEAKING' ? 7 : 5

  return (
    <div className={`suzanne-voice-visual state-${state.toLowerCase()}`} aria-hidden="true">
      {BAR_WEIGHTS.map((weight, index) => (
        <span
          key={index}
          style={responsive ? {
            height: `${baseline + Math.round(
              5 * weight + Math.pow(bands[index] ?? 0, 0.72) * amplitude,
            )}px`,
          } : undefined}
        />
      ))}
    </div>
  )
}
