# Day 1 Deliverables: The Walking Skeleton

## The Goal
By EOD Day 1, run the app with one Docker command, press the mic button in the UI, say *"Suzanne, take me to Budapest fast"*, see the extracted intent returned by the backend, and hear Suzanne say: *"Calculating route based on your preferences, hold on"*.

Day 1 ends after intent extraction and voice response. It does not calculate,
display, or confirm a route. All confirmations are voice-only; do not add
on-screen confirmation buttons.

---

## What Each Person Does

### Person A (Frontend & Voice HMI)
- Set up React + Vite + TailwindCSS on port 5173.
- Build the voice button with visual states (Idle, Recording, Processing, Speaking).
- Capture microphone audio into a blob and send it to the backend (`POST /api/assistant/voice`).
- Receive the extracted intent and base64 audio response, then play the voice
	output aloud via HTML5 Audio. Do not render confirmation buttons.

### Person B (Backend & Trip Engine)
- Set up FastAPI on port 8000.
- Create `POST /api/assistant/voice` to accept the audio file and forward it to Person C's AI module.
- Create `POST /api/assistant/interact` as a text-only fallback for easy testing.
- Load `telemetry.json` and `partners.json` into memory.
- Return the extracted intent and response adhering strictly to the
	`contracts.ts` schema. `route` is absent or `null` for Day 1.

### Person C (AI & Voice Lead)
- Integrate OpenAI Whisper (`whisper-1`) to transcribe incoming audio to text.
- Use OpenAI tool calling to extract `{ destination, priority }` from the transcript.
- Define Suzanne's persona prompt: concise executive concierge. The successful
	Day 1 response is exactly "Calculating route based on your preferences, hold
	on"; it must not claim route facts.
- Integrate OpenAI TTS (`tts-1`, voice `nova`) to synthesize Suzanne's spoken response into audio bytes.

### Person D (Platform & Orchestration)
- Create the root `docker-compose.yml` so the entire stack boots with `docker compose up --build`.
- Configure hot-reloading for both frontend and backend inside Docker.
- Set up FastAPI CORS so the frontend on port 5173 can talk to port 8000.
- Add a `GET /health` endpoint.
- Verify `.env` is loaded cleanly and never committed to Git, and verify the
	voice-only Day 1 acceptance flow.