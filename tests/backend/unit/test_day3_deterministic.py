import asyncio

from backend.app.models.contracts import StopPinpoint
from backend.app.models.fixtures import Partner
from backend.app.services.recommendation.poi import POIService
from backend.app.services.trip.country_rules import (
    derive_requirements,
    detect_border_crossings,
)
from backend.app.services.trip.deterministic import enrich_partner, rank_pois, select_charger
from backend.app.services.trip.ports import ChargingCandidate, POICandidate, ProviderRoute


def stop(stop_id: str, category: str = "charging", detour: float = 1) -> StopPinpoint:
    return StopPinpoint(
        id=stop_id,
        name=stop_id,
        category=category,
        coords=(17.0, 47.0),
        detour_minutes=detour,
    )


def test_charger_selection_filters_unsafe_candidates_before_ranking() -> None:
    selected = select_charger(
        [
            ChargingCandidate(stop("incompatible"), compatible=False),
            ChargingCandidate(stop("unavailable"), available=False),
            ChargingCandidate(stop("far"), distance_from_route_km=4),
            ChargingCandidate(stop("near"), distance_from_route_km=1),
        ]
    )

    assert selected is not None
    assert selected.stop.id == "near"


def test_partner_enrichment_does_not_create_vignette_benefit() -> None:
    vignette = Partner(
        id="vignette",
        name="Hungarian vignette",
        category="vignette",
        coords=(17, 47),
        tag="Automated Toll Clearing",
        detour_minutes=0,
    )

    enriched = enrich_partner(stop("vignette", "vignette"), [vignette])

    assert enriched.partner is not None
    assert enriched.partner.benefit is None


def test_country_rules_detect_borders_and_requirements() -> None:
    crossings = detect_border_crossings(["AT", "HU"])
    requirements = derive_requirements(["AT", "HU"])

    assert crossings[0].from_country == "Austria"
    assert crossings[0].to_country == "Hungary"
    assert {requirement.id for requirement in requirements} == {
        "at-motorway-vignette",
        "hu-motorway-vignette",
    }


class FakePOIProvider:
    def __init__(self, candidates: tuple[POICandidate, ...]) -> None:
        self.candidates = candidates

    async def search_pois(self, route, category, preference):
        del route, category, preference
        return self.candidates


def test_poi_search_ranks_without_mutating_route() -> None:
    route = ProviderRoute(1000, 60, ((17, 47), (18, 48)))
    service = POIService(
        FakePOIProvider(
            (
                POICandidate(stop("restaurant-b", "restaurant", 3), 0.8, 4),
                POICandidate(stop("restaurant-a", "restaurant", 1), 0.8, 4),
            )
        )
    )

    result = asyncio.run(service.search(route, "restaurant"))

    assert [item.id for item in result] == ["restaurant-a", "restaurant-b"]
    assert route.geometry == ((17, 47), (18, 48))