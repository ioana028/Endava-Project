from backend.app.models.contracts import StopPinpoint
from backend.app.models.fixtures import Partner
from backend.app.services.trip.deterministic import enrich_partner


def partner(**updates: object) -> Partner:
    values = {
        "id": "partner-1",
        "name": "ChargePoint Parndorf",
        "brand": "ChargePoint",
        "category": "charging",
        "provider_brands": ("ChargePoint",),
        "coords": (16.86, 47.99),
        "benefit": "10% off charging sessions",
    }
    values.update(updates)
    return Partner.model_validate(values)


def stop(**updates: object) -> StopPinpoint:
    values = {
        "id": "provider-result",
        "name": "ChargePoint Parndorf",
        "category": "charging",
        "coords": (16.86, 47.99),
    }
    values.update(updates)
    return StopPinpoint.model_validate(values)


def test_stable_id_match_takes_precedence_over_name_match() -> None:
    result = enrich_partner(
        stop(id="partner-1", name="Different Provider Name"),
        [partner(name="Different Provider Name", benefit="10% off charging sessions")],
    )

    assert result.partner is not None
    assert result.partner.id == "partner-1"


def test_provider_brand_match_requires_an_exact_normalized_prefix() -> None:
    result = enrich_partner(stop(), [partner()])

    assert result.partner is not None
    assert result.partner.benefit == "10% off charging sessions"


def test_partial_brand_overlap_does_not_create_a_commercial_match() -> None:
    result = enrich_partner(
        stop(name="Charge station Parndorf"),
        [partner()],
    )

    assert result.partner is None


def test_vague_partner_benefit_is_not_returned_as_a_claim() -> None:
    result = enrich_partner(
        stop(id="partner-1"),
        [partner(benefit="partner access")],
    )

    assert result.partner is not None
    assert result.partner.benefit is None
