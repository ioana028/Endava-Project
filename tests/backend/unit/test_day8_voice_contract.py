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


def test_day8_realtime_instructions_require_verified_benefits_and_returned_eur() -> None:
    instructions = " ".join(REALTIME_INSTRUCTIONS.split())
    assert "Mention partner benefits only when returned and verified" in instructions
    assert "Do not label actions or results as demos, simulations, or fixtures" in instructions
    assert "in EUR, without hard-coded amounts" in instructions
    assert "Mention a returned opportunity only when the driver asks about it or it is clearly relevant" in instructions
    assert "Speak prices only when returned by a tool" in instructions
