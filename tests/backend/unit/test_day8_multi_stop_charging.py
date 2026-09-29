from backend.app.models.contracts import RoutePriority, StopPinpoint
from backend.app.services.trip.deterministic import select_chargers_iteratively
from backend.app.services.trip.ports import ChargingCandidate


def candidate(stop_id: str, progress_km: float, minutes: float = 20) -> ChargingCandidate:
    return ChargingCandidate(
        stop=StopPinpoint(
            id=stop_id,
            name=stop_id,
            category="charging",
            coords=(16.0 + progress_km / 100, 48.0),
        ),
        distance_from_origin_km=progress_km,
        distance_from_route_km=1,
        charging_duration_minutes=minutes,
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


def test_fastest_plan_does_not_add_a_second_charge_20km_after_the_first() -> None:
    plan = select_chargers_iteratively(
        [
            candidate("early-fast", 65, 5),
            candidate("first", 80, 20),
            candidate("nearby-fast", 100, 4),
            candidate("second", 315, 22),
            candidate("third", 550, 22),
        ],
        route_distance_km=650,
        vehicle_range_km=95,
        safety_buffer_km=10,
        max_charged_range_km=250,
        priority=RoutePriority.FASTEST,
    )

    assert plan is not None
    assert [item.stop.id for item in plan] == ["first", "second", "third"]


def test_fastest_uses_quicker_station_within_well_spaced_safe_options() -> None:
    plan = select_chargers_iteratively(
        [candidate("quicker", 78, 15), candidate("slower", 82, 30)],
        route_distance_km=250,
        vehicle_range_km=95,
        safety_buffer_km=10,
        max_charged_range_km=250,
        priority=RoutePriority.FASTEST,
    )

    assert plan is not None
    assert [item.stop.id for item in plan] == ["quicker"]


def test_earlier_charger_remains_eligible_when_it_is_the_only_safe_path() -> None:
    plan = select_chargers_iteratively(
        [candidate("first", 70), candidate("second", 295)],
        route_distance_km=500,
        vehicle_range_km=95,
        safety_buffer_km=10,
        max_charged_range_km=250,
        priority=RoutePriority.FASTEST,
    )

    assert plan is not None
    assert [item.stop.id for item in plan] == ["first", "second"]


def test_four_stops_are_kept_when_the_long_route_really_requires_them() -> None:
    plan = select_chargers_iteratively(
        [
            candidate("first", 80),
            candidate("second", 315),
            candidate("third", 550),
            candidate("fourth", 785),
        ],
        route_distance_km=900,
        vehicle_range_km=95,
        safety_buffer_km=10,
        max_charged_range_km=250,
        priority=RoutePriority.FASTEST,
    )

    assert plan is not None
    assert [item.stop.id for item in plan] == [
        "first", "second", "third", "fourth"
    ]
