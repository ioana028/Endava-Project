# Day 8 Voice Flows

Person C's Realtime layer may speak only the compact, typed facts returned by
deterministic services. Route geometry and raw provider payloads stay outside
Realtime messages.

## Verified partner opportunities

After route, POI, or amenity results, Suzanne proactively mentions the
highest-value returned opportunity. A benefit is commercial only when the
returned partner fact has an exact benefit and `verified: true`. Benefits from
fixture data are described as simulated. A provider brand, nearby place, or
unverified partner name is not a benefit.

## Route memory

The active route session distinguishes `suggested`, `confirmed`, and
`completed`. Suzanne does not ask for charging after `chargingPlanConfirmed`
is true, or for a vignette after its requirement ID is purchased, duplicated,
or completed. A partially completed charging plan names the next remaining
requirement. One confirmation describes every charging stop in route order.

## Currency and errors

Amounts come from typed tool responses and use one EUR convention, such as
`16.50 euros` or `16 euros and 50 cents`. Suzanne never mixes dollars and
euros or invents a price. Every successful tool call receives one concise
spoken result; every failure receives one actionable error based on its stable
error code and message.