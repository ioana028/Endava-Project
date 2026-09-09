# AI-Powered In-Car Mobility Concierge ("Suzanne")

A voice-first, telemetry-aware automotive infotainment experience demonstrating an in-cabin two-sided marketplace.

---

## 1. Executive Summary & Vision

Suzanne is an executive in-cabin concierge designed for luxury Battery Electric Vehicles (BEVs). Unlike standard navigation apps, Suzanne bridges deterministic vehicle intelligence with conversational AI:
- **Telemetry-Aware:** Monitors vehicle range, consumption, and tyre state to proactively prevent range anxiety.
- **Two-Sided Marketplace:** Seamlessly surfaces commercial partner services (charging, dining, digital vignettes) without disrupting the drive.
- **Advisory, Non-Enforced Monetization:** Partner perks (discounts, fast-charging priority) are suggested organically with driver benefit highlighted (e.g., "There is a partner location near your destination offering a 10% discount. Should I book that?"). The driver retains executive veto power—partners are never forced.

---

## 2. The Primary Demo Corridor

- **Route:** Vienna, Austria -> Budapest, Hungary (~243 km via the M1 motorway).
- **Vehicle Profile:** Honda E (35.5 kWh battery, starting at 42% battery / 95 km range).
- **Core Narrative:** Starting with 95 km of range to cover a 243 km distance creates an immediate, deterministic need for an automated mid-trip charging stop at Ionity Győr, crossing an international border (triggering toll/vignette handling), and an optional dining reservation upon arrival.

---

## 3. Architecture & Tech Stack

A local modular monolith designed for rapid iteration without cloud database overhead.

- **Frontend:** React 18, TypeScript, TailwindCSS, MapLibre GL, Lucide Icons.
- **Backend:** Python 3.11+, FastAPI, Pydantic v2, Uvicorn, HTTPX.
- **External Integrations:** OpenAI API (Structured Outputs / Tools), OpenRouteService (Routing & POIs).
- **Data Stores:** Flat JSON files (data/vehicles/telemetry.json, data/partners/partners.json). Zero remote DB dependencies.

---

## 4. Local Setup Quickstart

1. **Prerequisites:** Node.js 18+, Python 3.11+, Git.
2. **Environment:**
   cp .env.example .env
   # Populate OPENAI_API_KEY and OPENROUTESERVICE_API_KEY in .env
3. **Contracts Reference:** Review frontend/src/types/contracts.ts and docs/api/contracts.md before writing endpoints or UI state.