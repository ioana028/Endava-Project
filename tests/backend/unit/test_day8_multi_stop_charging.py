from backend.app.models.contracts import StopPinpoint
from backend.app.services.trip.deterministic import select_chargers_iteratively
from backend.app.services.trip.ports import ChargingCandidate


def candidate(stop_id: str, progress_km: float) -> ChargingCandidate:
    return ChargingCandidate(
        stop=StopPinpoint(
            id=stop_id,
            name=stop_id,
            category="charging",
            coords=(16.0 + progress_km / 100, 48.0),
        ),
        distance_from_origin_km=progress_km,
        distance_from_route_km=1,
        charging_duration_minutes=20,
    )


def test_selector_returns_ordered_two_stop_plan_when_one_charge_is_insufficient() -> None:
    plan = select_chargers_iteratively(
        [candidate("charger-a", 80), candidate("charger-b", 160)],
        route_distance_km=240,
        vehicle_range_km=95,
        safety_buffer_km=10,
        max_charged_range_km=95,
    )

    assert plan is not None
    assert [item.stop.id for item in plan] == ["charger-a", "charger-b"]


def test_selector_returns_ordered_three_stop_plan_for_long_route() -> None:
    plan = select_chargers_iteratively(
        [
            candidate("charger-a", 80),
            candidate("charger-b", 160),
            candidate("charger-c", 240),
        ],
        route_distance_km=320,
        vehicle_range_km=95,
        safety_buffer_km=10,
        max_charged_range_km=95,
    )

    assert plan is not None
    assert [item.stop.id for item in plan] == [
        "charger-a", "charger-b", "charger-c"
    ]


def test_selector_rejects_duplicate_or_unreachable_progress() -> None:
    plan = select_chargers_iteratively(
        [candidate("charger-a", 80), candidate("charger-a", 80)],
        route_distance_km=240,
        vehicle_range_km=95,
        safety_buffer_km=10,
        max_charged_range_km=95,
    )

    assert plan is None
