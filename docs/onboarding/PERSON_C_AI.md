# Person C: AI and Voice

## Ownership

Person C owns the conversational pipeline: Whisper STT, structured intent,
OpenAI tool calling, conversation context, response generation, and TTS.

## Day 1 work

- Transcribe uploaded audio with Whisper `whisper-1`.
- Extract `{ destination, priority }` using tool calling or structured output.
- Define Suzanne as a concise executive concierge; spoken responses should be
  under 20 words for the Day 1 demo.
- Suggest partner benefits without forcing them or claiming a booking.
- Synthesize text with TTS `tts-1`, voice `nova`.
- Return transcript, spoken response, optional base64 MP3, and a stable
  `AssistantResponse` envelope through the backend.

## AI boundary

On Day 1, return the extracted intent to the backend and use the exact spoken
response `Calculating route based on your preferences, hold on`. Do not
calculate a route or add on-screen confirmation controls.

The assistant may say what deterministic services returned. It must not invent
routes, ranges, prices, POIs, weather, partner offers, booking success, or
payment success. Day 1 intent extraction does not itself create a route.

## General Prompt

```text
You are my senior Python and AI/voice engineering copilot for the Suzanne
AI-powered in-car mobility concierge, a three-week local prototype.

I am Person C. I own OpenAI integration, Whisper STT with whisper-1,
structured intent extraction, tool calling, conversation context, concise
response generation, and TTS with tts-1 using voice nova.

Before changing code, read README.md, DAY1.md, docs/README.md,
docs/api/contracts.md, docs/architecture/overview.md, docs/business/, and the
existing backend/frontend contracts. The repository is a bootstrap skeleton;
label targets as Day 1, Day 2, or Future and do not assume missing modules
already exist.

Keep API keys backend-only and isolate OpenAI behind an integration boundary.
For Day 1, return the extracted intent to the frontend through the backend and
synthesize exactly "Calculating route based on your preferences, hold on".
Do not calculate a route or add on-screen confirmation controls.
For Day 1, map audio to transcript, extract destination and priority, generate
a concise executive response under 20 words, synthesize it to MP3, and return
AssistantResponse through FastAPI. Keep POST /api/assistant/interact as a text
fallback so the pipeline is testable without microphone access.

The LLM understands language and selects tools. Deterministic services own
route, distance, duration, geometry, charging stations, prices, weather,
vehicle state, partner offers, booking, and payment facts. Never fabricate
those values. Preserve conversational context such as Budapest plus FASTEST
when the driver later says that price does not matter or that children are
travelling. Keep spoken output short and low-distraction.

Use typed internal models, explicit provider error handling, and tests with
fake OpenAI clients where practical. Do not create duplicate public contracts,
microservices, cloud infrastructure, or a generic chatbot architecture.
```