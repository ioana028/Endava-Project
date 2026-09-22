from pathlib import Path

from backend.app.models.contracts import PartnerEnrichment, RoutePriority, StopPinpoint
from backend.app.core.fixture_repository import FixtureRepository
from backend.app.models.fixtures import Partner
from backend.app.services.recommendation.poi import rank_partner_opportunities
from backend.app.services.trip.deterministic import enrich_partner
from backend.app.services.trip.ports import ChargingCandidate
from backend.app.services.trip.service import RouteService


def test_brand_match_is_exact_and_applies_to_all_matching_locations() -> None:
    shell = Partner(
        id="brand-shell",
        kind="network",
        name="Shell partner network",
        brand="Shell",
        category="charging",
        categories=("charging",),
        provider_brands=("Shell", "Shell Recharge"),
        benefit="10% off charging costs",
        coords=None,
    )

    first = enrich_partner(
        StopPinpoint(id="shell-1", name="Shell Recharge Hegyeshalom", category="charging", coords=(17.1, 47.9)),
        [shell],
    )
    second = enrich_partner(
        StopPinpoint(id="shell-2", name="Shell Recharge Vienna", category="charging", coords=(16.4, 48.2)),
        [shell],
    )

    assert first.partner_benefit == "10% off charging costs"
    assert second.partner_benefit == first.partner_benefit


def test_brand_benefit_does_not_cross_categories() -> None:
    restaurant = Partner(
        id="brand-shell-food",
        kind="network",
        name="Shell food partner",
        brand="Shell",
        category="restaurant",
        categories=("restaurant",),
        provider_brands=("Shell",),
        benefit="Free coffee with a meal",
        coords=None,
    )

    result = enrich_partner(
        StopPinpoint(id="shell-charger", name="Shell Recharge", category="charging", coords=(17.1, 47.9)),
        [restaurant],
    )

    assert result.partner is None


def test_brand_benefit_applies_to_an_explicitly_eligible_secondary_category() -> None:
    coffee_brand = Partner(
        id="brand-coffee",
        kind="network",
        name="Coffee partner network",
        brand="Coffee Brand",
        category="restaurant",
        categories=("restaurant", "coffee"),
        provider_brands=("Coffee Brand",),
        benefit="Free pastry with coffee",
        coords=None,
    )

    result = enrich_partner(
        StopPinpoint(
            id="coffee-1",
            name="Coffee Brand Vienna",
            category="coffee",
            coords=(16.4, 48.2),
        ),
        [coffee_brand],
    )

    assert result.partner_benefit == "Free pastry with coffee"


def test_ambiguous_provider_identity_produces_no_commercial_claim() -> None:
    first = Partner(
        id="brand-one",
        kind="network",
        name="First network",
        brand="Same Brand",
        category="charging",
        provider_brands=("Same Brand",),
        benefit="10% off charging",
        coords=None,
    )
    second = first.model_copy(
        update={"id": "brand-two", "name": "Second network", "benefit": "Free coffee"}
    )

    result = enrich_partner(
        StopPinpoint(
            id="provider-result",
            name="Same Brand Station",
            category="charging",
            coords=(16.4, 48.2),
        ),
        [first, second],
    )

    assert result.partner is None


def test_disabled_brand_produces_no_claim() -> None:
    disabled = Partner(
        id="brand-disabled",
        kind="network",
        name="Disabled Shell network",
        brand="Shell",
        category="charging",
        provider_brands=("Shell",),
        benefit="10% off charging costs",
        enabled=False,
        coords=None,
    )

    result = enrich_partner(
        StopPinpoint(id="shell-charger", name="Shell Recharge", category="charging", coords=(17.1, 47.9)),
        [disabled],
    )

    assert result.partner is None


def test_opportunity_ranking_requires_a_verified_benefit_and_safe_stop() -> None:
    partner = Partner(
        id="brand-shell",
        kind="network",
        name="Shell partner network",
        brand="Shell",
        category="charging",
        provider_brands=("Shell",),
        benefit="10% off charging costs",
        coords=None,
    )
    safe = enrich_partner(
        StopPinpoint(id="safe", name="Shell Recharge Safe", category="charging", coords=(17.0, 48.0)),
        [partner],
    )
    unsafe = safe.model_copy(update={"id": "unsafe", "coords": (18.0, 48.0)})

    opportunities = rank_partner_opportunities(
        [safe, unsafe],
        ((16.0, 48.0), (19.0, 48.0)),
        safe_stop_ids={"safe"},
    )

    assert [item.stop.id for item in opportunities] == ["safe"]
    assert opportunities[0].requires_route_confirmation is True


def test_opportunity_ranking_honors_fastest_priority() -> None:
    partner = Partner(
        id="brand-shell",
        kind="network",
        name="Shell partner network",
        brand="Shell",
        category="charging",
        provider_brands=("Shell",),
        benefit="10% off charging costs",
        coords=None,
    )
    near = enrich_partner(
        StopPinpoint(
            id="near",
            name="Shell Near",
            category="charging",
            coords=(17.0, 48.0),
            detour_minutes=1,
        ),
        [partner],
    )
    far = enrich_partner(
        StopPinpoint(
            id="far",
            name="Shell Far",
            category="charging",
            coords=(17.0, 48.0),
            detour_minutes=8,
        ),
        [partner],
    )

    opportunities = rank_partner_opportunities(
        [far, near],
        ((16.0, 48.0), (19.0, 48.0)),
        priority=RoutePriority.FASTEST,
    )

    assert [item.stop.id for item in opportunities] == ["near", "far"]


def test_day8_partner_fixture_boundary_normalizes_legacy_records() -> None:
    repository = FixtureRepository(
        telemetry_path=Path("data/vehicles/telemetry.json"),
        partners_path=Path("data/partners/partners.json"),
    )

    partners = repository.load().partners

    assert partners
    assert all(partner.kind in {"brand", "location"} for partner in partners)
    assert all(partner.benefit_scope in {"brand-wide", "location", "none"} for partner in partners)
    assert all(partner.benefit_source == "fixture" for partner in partners)
    assert all(partner.verified for partner in partners)
    assert all(partner.brand_aliases for partner in partners)
    assert all(
        partner.coords is not None
        for partner in partners
        if partner.kind == "location"
    )


def test_nearby_partner_charger_is_offered_as_a_second_choice() -> None:
    selected = ChargingCandidate(
        stop=StopPinpoint(
            id="charger-selected",
            name="Fast Charger",
            category="charging",
            coords=(17.0, 48.0),
        ),
        distance_from_origin_km=100,
    )
    partner = ChargingCandidate(
        stop=StopPinpoint(
            id="charger-partner",
            name="Shell Recharge Nearby",
            category="charging",
            coords=(17.1, 48.0),
            partner=PartnerEnrichment(
                id="shell-brand",
                name="Shell",
                benefit="10% off charging costs",
                benefit_scope="brand-wide",
                benefit_source="fixture",
                verified=True,
            ),
            partner_benefit="10% off charging costs",
        ),
        distance_from_origin_km=112,
        distance_from_route_km=0.4,
    )

    opportunities = RouteService._nearby_partner_opportunities(
        (selected, partner),
        [selected],
    )

    assert len(opportunities) == 1
    assert opportunities[0].stop_id == "charger-partner"
    assert opportunities[0].partner_fact is not None
    assert opportunities[0].partner_fact.brand == "Shell"
    assert opportunities[0].requires_route_confirmation is True
