import type { RouteResponse } from '../types/contracts'

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

interface RealtimeSessionResponse {
  clientSecret: string
  model: string
}

interface PlanRouteToolResponse {
  route: RouteResponse
}

export async function createRealtimeSession(): Promise<RealtimeSessionResponse> {
  const response = await fetch(`${API_BASE_URL}/api/assistant/realtime/session`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  })

  if (!response.ok) {
    throw new Error(`Realtime session failed with HTTP ${response.status}`)
  }

  const payload = (await response.json()) as RealtimeSessionResponse
  if (!payload.clientSecret) {
    throw new Error('Realtime session did not return a client secret.')
  }

  if (!payload.model) {
    throw new Error('Realtime session did not return a model.')
  }

  return payload
}

export async function planRouteWithTool(
  argumentsJson: string,
  signal?: AbortSignal,
): Promise<PlanRouteToolResponse> {
  const response = await fetch(
    `${API_BASE_URL}/api/assistant/realtime/tools/plan-route`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: argumentsJson,
      signal,
    },
  )

  if (!response.ok) {
    throw new Error(`Route tool failed with HTTP ${response.status}`)
  }

  return (await response.json()) as PlanRouteToolResponse
}