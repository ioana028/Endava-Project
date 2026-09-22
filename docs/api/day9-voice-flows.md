# Day 9 Voice Flows

This document defines the Person C Realtime contract for the final Suzanne
prototype pass.

## Connection lifecycle

The browser creates a new session generation for every Start attempt. Stop
invalidates the generation, aborts the session and tool requests, closes the
peer connection and data channel, stops microphone tracks, and releases audio.
Async work from an invalid generation must not publish state, audio, events, or
connection references into a later session.

The authoritative browser readiness point is the
`suzanne:connection-confirmed` event. It is emitted only after the OpenAI
remote description has been applied and the Realtime data channel is open. The
listening jingle plays once at that point, never on button press or after a
failed handshake.

## Route narration

Route planning may receive one short acknowledgement while the tool runs. The
returned deterministic result is spoken once and does not repeat the
acknowledgement or announce intermediate processing.

Route narration may use only returned facts:

- travel time, distance, requirements, and border facts;
- telemetry battery, range, consumption, maximum charged range, and charging
  feasibility;
- returned weather or severity alerts;
- verified partner benefits and route opportunities.

Missing facts are stated as unavailable. Suzanne never estimates range,
weather, pricing, availability, or charging feasibility.

## Place narration

Attractions and other Google Places results may include an optional summary,
photo reference, rating, review count, top keywords, provider, and source.
Suzanne may describe what can be seen or done only from the returned summary,
details, or keywords. Review counts and ratings are reported as facts; review
sentiment is never invented.

Search results are suggestions. They do not change the route until the driver
authorizes a reroute, booking, or other mutation.

## Charging and amenities

A confirmed charging response contains the complete ordered charging plan.
Suzanne names every returned stop and duration once, then states every verified
charging partner benefit. Nearby amenities are read-only and any verified
partner benefit is stated with its returned brand and exact benefit.

The voice layer must not describe only the first charger as the complete plan.

## Statement-first policy

Statements are the default for route results, telemetry, weather, prices,
requirements, partner facts, errors, and completed actions. Suzanne asks one
question only when explicit authorization or missing required booking details
are needed. An answered authorization question is never repeated.
