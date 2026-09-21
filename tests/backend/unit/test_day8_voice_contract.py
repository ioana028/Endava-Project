from backend.app.integrations.openai.realtime import REALTIME_INSTRUCTIONS
from backend.app.models.contracts import (
    ChargingPlan,
    PartnerFact,
    RouteOpportunity,
    RouteSessionFacts,
    StopPinpoint,
)


def test_day8_contracts_preserve_verified_partner_and_route_state() -> None:
    partner = PartnerFact(
        partner_id="shell",
        brand="Shell",
        benefit="5 cents off per litre",
        benefit_scope="charging",
        benefit_source="fixture",
        verified=True,
    )
    opportunity = RouteOpportunity(
        id="opportunity-1",
        type="charging",
        stop_id="charger-1",
        partner_fact=partner,
        reason="On route with a verified charging benefit",
        detour_minutes=4,
    )
    stop = StopPinpoint(
        id="charger-1",
        name="Shell Recharge",
        category="charging",
        coords=(16.0, 48.0),
    )
    plan = ChargingPlan(
        stops=[stop],
        complete=True,
        total_charging_minutes=25,
        confirmed=True,
    )
    session = RouteSessionFacts(
        charging_plan_confirmed=True,
        confirmed_charging_stop_ids=[stop.id],
    )

    assert opportunity.partner_fact == partner
    assert plan.stops[0].id == "charger-1"
    assert session.charging_plan_confirmed is True


def test_day8_realtime_instructions_require_verified_simulated_benefits_and_eur() -> None:
    assert "verified=true" in REALTIME_INSTRUCTIONS
    assert "simulated benefit" in REALTIME_INSTRUCTIONS
    assert "never mix dollars and euros" in REALTIME_INSTRUCTIONS
    assert "highest-value returned opportunity" in REALTIME_INSTRUCTIONS
    assert "Do not hard-code prices" in REALTIME_INSTRUCTIONS