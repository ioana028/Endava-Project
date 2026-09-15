from collections.abc import Iterable
from math import cos, radians, sqrt

from ...models.contracts import PartnerEnrichment, StopPinpoint
from ...models.fixtures import Partner
from .ports import ChargingCandidate, POICandidate


POI_MAX_RESULTS = 2
POI_CORRIDOR_RADIUS_KM = 35.0
POI_DIVERSITY_DISTANCE_KM = 15.0


def distance_km(first: tuple[float, float], second: tuple[float, float]) -> float:
    latitude = radians((first[1] + second[1]) / 2)
    longitude_km = (first[0] - second[0]) * 111.32 * cos(latitude)
    latitude_km = (first[1] - second[1]) * 111.32
    return sqrt(longitude_km**2 + latitude_km**2)


def distance_to_route_km(
    point: tuple[float, float], geometry: tuple[tuple[float, float], ...]
) -> float:
    if not geometry:
        return float("inf")
    return min(distance_km(point, vertex) for vertex in geometry)


def select_route_pois(
    candidates: Iterable[POICandidate], preference: str | None = None
) -> list[POICandidate]:
    ranked = rank_pois(candidates, preference)
    selected: list[POICandidate] = []
    deferred: list[POICandidate] = []
    for candidate in ranked:
        if any(
            distance_km(candidate.stop.coords, chosen.stop.coords)
            < POI_DIVERSITY_DISTANCE_KM
            for chosen in selected
        ):
            deferred.append(candidate)
            continue
        selected.append(candidate)
        if len(selected) == POI_MAX_RESULTS:
            break
    for candidate in deferred:
        if len(selected) == POI_MAX_RESULTS:
            break
        selected.append(candidate)
    return selected


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
    partner_list = tuple(partners)
    partner = next((item for item in partner_list if item.id == stop.id), None)
    if partner is None:
        normalized_name = " ".join(stop.name.casefold().split())
        partner = next(
            (
                item
                for item in partner_list
                if item.category == stop.category
                and " ".join(item.name.casefold().split()) == normalized_name
            ),
            None,
        )
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