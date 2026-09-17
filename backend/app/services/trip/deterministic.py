import re
from collections.abc import Iterable
from math import cos, radians, sqrt

from ...models.contracts import PartnerEnrichment, StopPinpoint
from ...models.fixtures import Partner
from .ports import ChargingCandidate, POICandidate


POI_MAX_RESULTS = 2
POI_CORRIDOR_RADIUS_KM = 7.5
POI_ORIGIN_EXCLUSION_KM = 10.0
POI_DESTINATION_EXCLUSION_KM = 10.0
STOP_AMENITY_RADIUS_KM = 0.5
STOP_AMENITY_MAX_RESULTS = 4
POI_DIVERSITY_DISTANCE_KM = 15.0
POI_COORDINATE_TOLERANCE = 0.01
DEFAULT_CHARGING_POWER_KW = 50.0
MIN_CHARGER_PROGRESS_KM = 20.0


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
    return min(
        _distance_to_segment_km(point, start, end)
        for start, end in zip(geometry, geometry[1:])
    ) if len(geometry) > 1 else distance_km(point, geometry[0])


def _distance_to_segment_km(
    point: tuple[float, float],
    start: tuple[float, float],
    end: tuple[float, float],
) -> float:
    latitude = radians((start[1] + end[1]) / 2)
    longitude_scale = 111.32 * cos(latitude)
    start_x = start[0] * longitude_scale
    end_x = end[0] * longitude_scale
    point_x = point[0] * longitude_scale
    start_y = start[1] * 111.32
    end_y = end[1] * 111.32
    point_y = point[1] * 111.32
    segment_x = end_x - start_x
    segment_y = end_y - start_y
    length_squared = segment_x**2 + segment_y**2
    if length_squared == 0:
        return sqrt((point_x - start_x) ** 2 + (point_y - start_y) ** 2)
    projection = (
        (point_x - start_x) * segment_x + (point_y - start_y) * segment_y
    ) / length_squared
    projection = max(0, min(1, projection))
    closest_x = start_x + projection * segment_x
    closest_y = start_y + projection * segment_y
    return sqrt((point_x - closest_x) ** 2 + (point_y - closest_y) ** 2)


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


def select_route_stops(
    stops: Iterable[StopPinpoint],
    geometry: tuple[tuple[float, float], ...],
    preference: str | None = None,
    location: str = "route",
) -> list[StopPinpoint]:
    candidates = [
        POICandidate(
            stop=stop,
            route_relevance=1 / (1 + distance_to_route_km(stop.coords, geometry)),
            quality=stop.rating or 0,
        )
        for stop in stops
        if _matches_search_scope(stop.coords, geometry, location)
    ]
    return [candidate.stop for candidate in select_route_pois(candidates, preference)]


def _matches_search_scope(
    point: tuple[float, float],
    geometry: tuple[tuple[float, float], ...],
    location: str,
) -> bool:
    if location == "destination":
        return True
    if location == "legacy-route":
        return distance_to_route_km(point, geometry) <= 35.0
    if location == "stop":
        return distance_km(point, geometry[-1]) <= STOP_AMENITY_RADIUS_KM if geometry else False
    if distance_to_route_km(point, geometry) > POI_CORRIDOR_RADIUS_KM:
        return False
    route_length_km = sum(distance_km(start, end) for start, end in zip(geometry, geometry[1:]))
    progress_km = route_progress_km(point, geometry)
    return (
        progress_km >= POI_ORIGIN_EXCLUSION_KM
        and progress_km <= route_length_km - POI_DESTINATION_EXCLUSION_KM
    )


def select_stop_amenities(
    stops: Iterable[StopPinpoint],
    center: tuple[float, float],
) -> list[StopPinpoint]:
    nearby = [
        stop for stop in stops if distance_km(stop.coords, center) <= STOP_AMENITY_RADIUS_KM
    ]
    return sorted(
        nearby,
        key=lambda stop: (
            distance_km(stop.coords, center),
            -(stop.rating or 0),
            stop.id,
        ),
    )[:STOP_AMENITY_MAX_RESULTS]


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
                candidate.distance_from_origin_km is None
                or candidate.distance_from_origin_km >= MIN_CHARGER_PROGRESS_KM
            )
            and (
                max_distance_km is None
                or candidate.distance_from_origin_km is None
                or candidate.distance_from_origin_km <= max_distance_km
            )
        )
    ]
    return min(
        suitable,
        key=lambda candidate: (
            0 if candidate.stop.partner else 1,
            -(candidate.distance_from_origin_km or 0),
            candidate.distance_from_route_km,
            candidate.stop.detour_minutes,
            -(candidate.stop.rating or 0),
            candidate.stop.id,
        ),
        default=None,
    )


def estimate_charging_duration_minutes(
    candidate: ChargingCandidate,
    route_distance_km: float,
    charger_progress_km: float,
    current_range_km: float,
    safety_buffer_km: float,
    consumption_rate_kwh: float,
) -> float:
    if candidate.charging_duration_minutes > 0:
        return candidate.charging_duration_minutes
    remaining_distance_km = max(0.0, route_distance_km - charger_progress_km)
    additional_range_km = max(
        0.0, remaining_distance_km + safety_buffer_km - max(0.0, current_range_km - charger_progress_km)
    )
    power_kw = candidate.charging_power_kw or DEFAULT_CHARGING_POWER_KW
    energy_kwh = additional_range_km * consumption_rate_kwh / 100
    return round(energy_kwh / power_kw * 60, 1)


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


def _normalize_partner_name(value: str | None) -> str:
    if not value:
        return ""
    normalized = value.casefold().replace("&", " and ")
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
    return " ".join(normalized.split())


def _normalized_tokens(value: str | None) -> set[str]:
    text = _normalize_partner_name(value)
    return set(text.split())


def enrich_partner(stop: StopPinpoint, partners: Iterable[Partner]) -> StopPinpoint:
    partner_list = tuple(partners)
    stop_text = " ".join(part for part in (stop.name, stop.tag) if part)
    stop_tokens = _normalized_tokens(stop_text)

    partner = next((item for item in partner_list if item.id == stop.id), None)
    if partner is None:
        partner = next(
            (
                item
                for item in partner_list
                if item.category == stop.category
                and _normalize_partner_name(item.name) == _normalize_partner_name(stop.name)
            ),
            None,
        )
    if partner is None:
        for item in partner_list:
            item_tokens = set(_normalized_tokens(item.name))
            for provider_brand in (item.brand, *tuple(item.provider_brands or ())):
                if provider_brand:
                    item_tokens.update(_normalized_tokens(provider_brand))
            if item_tokens.intersection(stop_tokens):
                partner = item
                break
    if partner is None:
        return stop

    benefit = partner.benefit or partner.tag or None
    return stop.model_copy(
        update={
            "partner": PartnerEnrichment(
                id=partner.id, name=partner.name, benefit=benefit
            )
        }
    )


def route_progress_km(
    point: tuple[float, float], geometry: tuple[tuple[float, float], ...]
) -> float:
    """Return the approximate distance from the route origin to a point."""
    if not geometry:
        return float("inf")
    if len(geometry) == 1:
        return 0.0

    progress = 0.0
    best_distance = float("inf")
    best_progress = 0.0
    for start, end in zip(geometry, geometry[1:]):
        segment_length = distance_km(start, end)
        if segment_length == 0:
            continue
        latitude = radians((start[1] + end[1] + point[1]) / 3)
        longitude_scale = 111.32 * cos(latitude)
        start_xy = (start[0] * longitude_scale, start[1] * 111.32)
        end_xy = (end[0] * longitude_scale, end[1] * 111.32)
        point_xy = (point[0] * longitude_scale, point[1] * 111.32)
        segment_x = end_xy[0] - start_xy[0]
        segment_y = end_xy[1] - start_xy[1]
        projection = (
            (point_xy[0] - start_xy[0]) * segment_x
            + (point_xy[1] - start_xy[1]) * segment_y
        ) / (segment_length * segment_length)
        projection = max(0.0, min(1.0, projection))
        closest = (
            start_xy[0] + projection * segment_x,
            start_xy[1] + projection * segment_y,
        )
        distance = sqrt(
            (point_xy[0] - closest[0]) ** 2 + (point_xy[1] - closest[1]) ** 2
        )
        if distance < best_distance:
            best_distance = distance
            best_progress = progress + projection * segment_length
        progress += segment_length
    return best_progress