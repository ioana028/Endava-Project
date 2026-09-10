import type { AssistantResponse } from '../types/contracts'

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

export async function sendVoice(
  audioBlob: Blob,
  sessionId?: string,
): Promise<AssistantResponse> {
  const formData = new FormData()

  formData.append('audio', audioBlob, 'suzanne-recording.webm')

  if (sessionId) {
    formData.append('sessionId', sessionId)
  }

  const response = await fetch(`${API_BASE_URL}/api/assistant/voice`, {
    method: 'POST',
    body: formData,
  })

  if (!response.ok) {
    throw new Error(`Voice request failed with HTTP ${response.status}`)
  }

  return response.json() as Promise<AssistantResponse>
}

export async function sendText(
  text: string,
  sessionId?: string,
): Promise<AssistantResponse> {
  const response = await fetch(`${API_BASE_URL}/api/assistant/interact`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ text, sessionId }),
  })

  if (!response.ok) {
    throw new Error(`Text request failed with HTTP ${response.status}`)
  }

  return response.json() as Promise<AssistantResponse>
}