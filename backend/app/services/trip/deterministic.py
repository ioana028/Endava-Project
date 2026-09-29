import re
import unicodedata
from collections.abc import Iterable
from functools import lru_cache
from math import cos, radians, sqrt

from ...models.contracts import PartnerEnrichment, RoutePriority, StopPinpoint
from ...models.fixtures import Partner
from .ports import ChargingCandidate, POICandidate


POI_MAX_RESULTS = 10
BOOKING_POI_MAX_RESULTS = 2
ATTRACTION_MAX_RESULTS = 10
POI_CORRIDOR_RADIUS_KM = 7.5
POI_ORIGIN_EXCLUSION_KM = 10.0
POI_DESTINATION_EXCLUSION_KM = 10.0
STOP_AMENITY_RADIUS_KM = 0.5
STOP_AMENITY_MAX_RESULTS = 4
_AMENITY_CHAIN_NAMES = (
    "burger king",
    "mcdonalds",
    "mc donalds",
    "starbucks",
    "costa coffee",
    "dunkin donuts",
    "pizza hut",
    "dominos",
    "subway",
    "taco bell",
    "five guys",
    "wendys",
    "pret a manger",
    "shell",
    "omv",
    "mol",
    "circle k",
    "bp",
    "esso",
    "eni",
    "totalenergies",
    "tesco",
    "lidl",
    "aldi",
    "spar",
    "penny",
    "auchan",
    "carrefour",
    "decathlon",
    "ikea",
    "ibis",
    "hilton",
    "marriott",
    "radisson",
)
POI_DIVERSITY_DISTANCE_KM = 8.0
POI_COORDINATE_TOLERANCE = 0.01
DEFAULT_CHARGING_POWER_KW = 50.0
MIN_CHARGER_PROGRESS_KM = 20.0
SCENIC_TAGS = frozenset({"scenic", "landmark", "lake", "river", "forest", "viewpoint"})


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
    scenic: bool = False,
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
    selected = (
        rank_scenic_pois(candidates)
        if scenic
        else select_route_pois(candidates, preference)
    )[:POI_MAX_RESULTS]
    if location == "route" and any(
        candidate.stop.category == "attraction" for candidate in candidates
    ):
        selected = _select_route_attractions(candidates, preference, scenic)
    return [candidate.stop for candidate in selected]


def _select_route_attractions(
    candidates: Iterable[POICandidate],
    preference: str | None = None,
    scenic: bool = False,
) -> list[POICandidate]:
    ranked = rank_scenic_pois(candidates) if scenic else rank_pois(candidates, preference)
    selected: list[POICandidate] = []
    for candidate in ranked:
        if any(
            distance_km(candidate.stop.coords, chosen.stop.coords)
            < POI_DIVERSITY_DISTANCE_KM
            for chosen in selected
        ):
            continue
        selected.append(candidate)
        if len(selected) == ATTRACTION_MAX_RESULTS:
            break
    return selected


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
    return progress_km >= POI_ORIGIN_EXCLUSION_KM and progress_km <= route_length_km - POI_DESTINATION_EXCLUSION_KM


def select_stop_amenities(
    stops: Iterable[StopPinpoint],
    center: tuple[float, float],
) -> list[StopPinpoint]:
    nearby = [
        stop for stop in stops if distance_km(stop.coords, center) <= STOP_AMENITY_RADIUS_KM
    ]
    ranked = sorted(
        nearby,
        key=lambda stop: (
            distance_km(stop.coords, center),
            -(stop.rating or 0),
            stop.id,
        ),
    )
    selected: list[StopPinpoint] = []
    seen: set[str] = set()
    for stop in ranked:
        key = _amenity_deduplication_key(stop.name)
        if key in seen:
            continue
        seen.add(key)
        selected.append(stop)
        if len(selected) == STOP_AMENITY_MAX_RESULTS:
            break
    return selected


def _amenity_deduplication_key(name: str) -> str:
    normalized = unicodedata.normalize("NFKD", name).casefold()
    normalized = "".join(
        character for character in normalized if not unicodedata.combining(character)
    )
    normalized = normalized.replace("'", "").replace("’", "")
    tokens = re.findall(r"[a-z0-9]+", normalized)
    if not tokens:
        return ""

    for brand in sorted(_AMENITY_CHAIN_NAMES, key=len, reverse=True):
        brand_tokens = brand.split()
        if any(
            tokens[index : index + len(brand_tokens)] == brand_tokens
            for index in range(len(tokens))
        ):
            return f"chain:{brand}"
    return f"name:{' '.join(tokens)}"


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


def select_chargers_iteratively(
    candidates: Iterable[ChargingCandidate],
    route_distance_km: float,
    vehicle_range_km: float,
    safety_buffer_km: float,
    max_charged_range_km: float | None = None,
    priority: RoutePriority = RoutePriority.BALANCED,
) -> list[ChargingCandidate] | None:
    """Find a safe whole-route plan without unnecessary short charging legs."""
    candidate_list = list(candidates)
    candidate_ids = [candidate.stop.id for candidate in candidate_list]
    if len(candidate_ids) != len(set(candidate_ids)):
        return None
    if route_distance_km < 0 or vehicle_range_km < 0 or safety_buffer_km < 0:
        return None
    if max_charged_range_km is not None and max_charged_range_km < 0:
        return None

    ordered = sorted(
        (
            candidate
            for candidate in candidate_list
            if candidate.compatible
            and candidate.available
            and candidate.stop.detour_minutes >= 0
            and candidate.distance_from_origin_km is not None
            and MIN_CHARGER_PROGRESS_KM <= candidate.distance_from_origin_km < route_distance_km
        ),
        key=lambda candidate: (
            candidate.distance_from_origin_km or 0,
            candidate.distance_from_route_km,
            candidate.stop.id,
        ),
    )
    charged_range_km = max_charged_range_km or vehicle_range_km
    initial_safe_leg_km = max(0.0, vehicle_range_km - safety_buffer_km)
    charged_safe_leg_km = max(0.0, charged_range_km - safety_buffer_km)
    if route_distance_km <= initial_safe_leg_km:
        return []
    if initial_safe_leg_km <= 0 or charged_safe_leg_km <= 0:
        return None

    # Search the candidate graph once. A cheap early charge must not force an
    # extra stop shortly afterwards when a safe, better-spaced plan exists.
    @lru_cache(maxsize=None)
    def best_from(previous_index: int) -> tuple[tuple[float, ...], tuple[int, ...]] | None:
        previous_progress = (
            0.0 if previous_index < 0
            else ordered[previous_index].distance_from_origin_km or 0.0
        )
        safe_leg = initial_safe_leg_km if previous_index < 0 else charged_safe_leg_km
        if route_distance_km - previous_progress <= safe_leg:
            return (0.0, 0.0, 0.0, 0.0, 0.0, 0.0), ()

        best: tuple[tuple[float, ...], tuple[int, ...]] | None = None
        for index in range(previous_index + 1, len(ordered)):
            candidate = ordered[index]
            progress = candidate.distance_from_origin_km or 0.0
            leg_distance = progress - previous_progress
            if leg_distance <= 0:
                continue
            if leg_distance > safe_leg:
                break
            suffix = best_from(index)
            if suffix is None:
                continue

            # Prefer chargers in the latter part of each usable battery leg.
            # Earlier stations remain eligible when they are the only safe path.
            shortfall = max(0.0, safe_leg * 0.85 - leg_distance)
            detour = candidate.stop.detour_minutes + candidate.distance_from_route_km * 2
            charge_time = (
                candidate.charging_duration_minutes
                if candidate.charging_duration_minutes > 0 else 60.0
            )
            score = (
                suffix[0][0] + 1,
                round(suffix[0][1] + shortfall, 3),
                round(suffix[0][2] + (
                    charge_time + detour if priority == RoutePriority.FASTEST else detour
                ), 3),
                round(suffix[0][3] + detour, 3),
                suffix[0][4] - (candidate.charging_power_kw or 0),
                suffix[0][5] - progress,
            )
            plan = (score, (index, *suffix[1]))
            if best is None or plan < best:
                best = plan
        return best

    plan = best_from(-1)
    return [ordered[index] for index in plan[1]] if plan is not None else None


def route_remaining_distance_km(
    route_distance_km: float, progress_km: float
) -> float:
    return round(max(0.0, route_distance_km - progress_km), 2)


def estimate_eta_minutes(
    remaining_distance_km: float, average_speed_kmh: float
) -> float:
    if average_speed_kmh <= 0:
        raise ValueError("Average speed must be positive")
    return round(remaining_distance_km / average_speed_kmh * 60, 1)


def estimate_charging_duration_minutes(
    candidate: ChargingCandidate,
    route_distance_km: float,
    charger_progress_km: float,
    current_range_km: float,
    safety_buffer_km: float,
    consumption_rate_kwh: float,
    max_charged_range_km: float | None = None,
) -> float:
    if candidate.charging_duration_minutes > 0:
        return candidate.charging_duration_minutes
    remaining_distance_km = max(0.0, route_distance_km - charger_progress_km)
    range_after_charge_km = max_charged_range_km or remaining_distance_km
    safe_charge_leg_km = max(0.0, range_after_charge_km - safety_buffer_km)
    required_leg_km = min(remaining_distance_km, safe_charge_leg_km)
    remaining_vehicle_range_km = max(0.0, current_range_km - charger_progress_km)
    additional_range_km = max(0.0, required_leg_km - remaining_vehicle_range_km)
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


def rank_scenic_pois(candidates: Iterable[POICandidate]) -> list[POICandidate]:
    """Rank offline route candidates by explicit scenic metadata and relevance."""
    return sorted(
        candidates,
        key=lambda candidate: (
            -sum(
                1
                for value in (candidate.stop.tag, *candidate.stop.amenities)
                if any(tag in _normalized_tokens(value) for tag in SCENIC_TAGS)
            ),
            -candidate.route_relevance,
            candidate.stop.detour_minutes,
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
    normalized_stop_name = _normalize_partner_name(stop.name)

    partner = next(
        (item for item in partner_list if item.id == stop.id and item.enabled),
        None,
    )
    if partner is None:
        exact_matches = [
            item
            for item in partner_list
            if item.enabled
            and _partner_matches_category(item, stop.category)
            and _normalize_partner_name(item.name) == normalized_stop_name
        ]
        partner = exact_matches[0] if len(exact_matches) == 1 else None
    if partner is None:
        brand_matches = [
            item
            for item in partner_list
            if item.enabled
            and _partner_matches_category(item, stop.category)
            and any(
                normalized_stop_name == normalized_brand
                or normalized_stop_name.startswith(f"{normalized_brand} ")
                for normalized_brand in (
                    _normalize_partner_name(item.brand),
                    *(_normalize_partner_name(value) for value in item.brand_aliases),
                    *(_normalize_partner_name(value) for value in item.provider_brands),
                )
                if normalized_brand
            )
        ]
        partner = brand_matches[0] if len(brand_matches) == 1 else None
    if partner is None:
        return stop

    candidate_benefit = partner.benefit
    if candidate_benefit is None and partner.category == "vignette":
        candidate_benefit = partner.tag
    benefit = (
        candidate_benefit
        if candidate_benefit and _has_concrete_benefit(candidate_benefit)
        else None
    )
    return stop.model_copy(
        update={
            "partner": PartnerEnrichment(
                id=partner.id,
                name=partner.name,
                benefit=benefit,
                benefit_scope=partner.benefit_scope,
                benefit_source=partner.benefit_source,
                verified=partner.verified and benefit is not None,
            ),
            "partner_benefit": benefit,
        }
    )


def _category_is_eligible(partner: Partner, category: str) -> bool:
    categories = tuple(partner.categories or ())
    return not categories or category in categories


def _partner_matches_category(partner: Partner, category: str) -> bool:
    return partner.category == category or _category_is_eligible(partner, category)


def _has_concrete_benefit(benefit: str) -> bool:
    normalized = _normalize_partner_name(benefit)
    return normalized not in {
        "",
        "partner access",
        "special offer",
        "preferred location",
        "convenience partner offer",
    }


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
