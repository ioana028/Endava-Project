from collections.abc import Iterable

from ...models.contracts import PartnerEnrichment, StopPinpoint
from ...models.fixtures import Partner
from .ports import ChargingCandidate, POICandidate


def select_charger(
    candidates: Iterable[ChargingCandidate],
    max_distance_km: float | None = None,
) -> ChargingCandidate | None:
    suitable = [
        candidate
        for candidate in candidates
        if (
            candidate.compatible
            and candidate.available
            and candidate.stop.detour_minutes >= 0
            and (
                max_distance_km is None
                or candidate.distance_from_route_km <= max_distance_km
            )
        )
    ]
    return min(
        suitable,
        key=lambda candidate: (
            candidate.distance_from_route_km,
            candidate.stop.detour_minutes,
            -(candidate.stop.rating or 0),
            candidate.stop.id,
        ),
        default=None,
    )


def rank_pois(
    candidates: Iterable[POICandidate], preference: str | None = None
) -> list[POICandidate]:
    normalized_preference = (preference or "").casefold()
    return sorted(
        candidates,
        key=lambda candidate: (
            -candidate.route_relevance,
            candidate.stop.detour_minutes,
            0 if normalized_preference and normalized_preference in candidate.stop.name.casefold() else 1,
            -candidate.quality,
            candidate.stop.id,
        ),
    )


def enrich_partner(stop: StopPinpoint, partners: Iterable[Partner]) -> StopPinpoint:
    partner = next((item for item in partners if item.id == stop.id), None)
    if partner is None:
        return stop
    benefit = None if partner.category == "vignette" else partner.tag or None
    return stop.model_copy(
        update={
            "partner": PartnerEnrichment(
                id=partner.id, name=partner.name, benefit=benefit
            )
        }
    )