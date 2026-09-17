import asyncio
from types import SimpleNamespace

import pytest

from backend.app.core.errors import APIError
from backend.app.models.contracts import RouteRequirement, StopPinpoint
from backend.app.services.commerce.service import CommerceService
from backend.app.services.wallet.service import WalletService


class RouteContext:
    active_route_id = "route-1"
    active_search_id = "search-1"
    active_route_requirements = (
        RouteRequirement(
            id="hu-vignette-10d", name="Hungarian vignette", country="HU", kind="vignette"
        ),
    )
    active_search_results = {
        "hotel-1": StopPinpoint(
            id="hotel-1", name="Riverside Hotel", category="hotel", coords=(19.0, 47.5)
        ),
        "restaurant-1": StopPinpoint(
            id="restaurant-1", name="Italia", category="restaurant", coords=(19.0, 47.5)
        ),
    }


def service() -> CommerceService:
    return CommerceService(RouteContext(), WalletService())


def test_purchase_requires_explicit_confirmation() -> None:
    with pytest.raises(APIError) as error:
        asyncio.run(
            service().purchase_vignette("route-1", "hu-vignette-10d", "pending")
        )

    assert error.value.code == "CONFIRMATION_REQUIRED"


def test_duplicate_purchase_returns_existing_transaction() -> None:
    commerce = service()
    first = asyncio.run(
        commerce.purchase_vignette("route-1", "hu-vignette-10d", "confirmed")
    )
    duplicate = asyncio.run(
        commerce.purchase_vignette("route-1", "hu-vignette-10d", "confirmed")
    )

    assert first.transaction_id == duplicate.transaction_id
    assert duplicate.status.value == "duplicate"


def test_stale_requirement_and_search_are_rejected() -> None:
    commerce = service()

    with pytest.raises(APIError) as requirement_error:
        asyncio.run(commerce.purchase_vignette("route-1", "old-vignette", "confirmed"))
    assert requirement_error.value.code == "STALE_REQUIREMENT"

    with pytest.raises(APIError) as search_error:
        asyncio.run(
            commerce.book(
                route_id="route-1", search_id="old-search", result_id="hotel-1",
                booking_type="hotel_room", guests=2, booking_date="2026-09-17",
                confirmation="confirmed",
            )
        )
    assert search_error.value.code == "STALE_SEARCH"


def test_booking_requires_explicit_confirmation_and_selected_result() -> None:
    commerce = service()

    with pytest.raises(APIError) as confirmation_error:
        asyncio.run(
            commerce.book(
                route_id="route-1", search_id="search-1", result_id="hotel-1",
                booking_type="hotel_room", guests=2, booking_date="2026-09-17",
                confirmation="pending",
            )
        )
    assert confirmation_error.value.code == "CONFIRMATION_REQUIRED"

    with pytest.raises(APIError) as result_error:
        asyncio.run(
            commerce.book(
                route_id="route-1", search_id="search-1", result_id="missing",
                booking_type="hotel_room", guests=2, booking_date="2026-09-17",
                confirmation="confirmed",
            )
        )
    assert result_error.value.code == "STALE_RESULT"


def test_booking_does_not_change_route_context() -> None:
    context = RouteContext()
    commerce = CommerceService(context, WalletService())
    booking = asyncio.run(
        commerce.book(
            route_id="route-1", search_id="search-1", result_id="hotel-1",
            booking_type="hotel_room", guests=2, booking_date="2026-09-17",
            confirmation="confirmed",
        )
    )

    assert booking.booking_type == "hotel_room"
    assert context.active_route_id == "route-1"
