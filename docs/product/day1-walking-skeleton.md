# Day 1 Walking Skeleton

## Acceptance goal

By the end of Day 1, the team can run the stack locally with one Docker
command, press the microphone button, say `Suzanne, take me to Budapest fast`,
see the extracted intent returned by the backend, and hear Suzanne say:
`Calculating route based on your preferences, hold on`.

Day 1 stops there. It does not calculate or display a route. It has no
on-screen confirmation buttons; confirmation is voice-only.

## Deliverables

### Person A

React/Vite/Tailwind shell on 5173, assistant state visuals, MediaRecorder
capture, voice upload, read-only intent display, base64 audio playback, and
text fallback UI. Do not add confirmation buttons.

### Person B

FastAPI on 8000, voice and text endpoints, fixture loading, intent echo to the
frontend, and `AssistantResponse` output with no route result yet.

### Person C

Whisper `whisper-1`, destination/priority extraction, the fixed Day 1 spoken
response, and TTS `tts-1` with `nova`.

### Person D

Docker Compose, hot reload, root `.env` loading, explicit CORS, health endpoint,
and a fresh-start verification.

## Definition of done

- `docker compose up --build` starts both services.
- `GET /health` returns `status: ok`.
- Text fallback works without microphone access.
- Voice upload reaches the backend and returns a transcript, intent, and
  documented provider error when applicable.
- A successful response contains `transcript`, `intent`, and
  `spokenResponse` equal to `Calculating route based on your preferences, hold
  on`.
- TTS audio is played when available and text remains visible when it is not.
- No confirmation button is rendered; voice is the only confirmation channel.
- No API key is present in frontend source, Git, browser requests, or logs.
- `route` is absent or `null`; no Day 1 code calculates or invents route facts.