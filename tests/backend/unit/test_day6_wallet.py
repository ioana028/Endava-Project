import asyncio

import pytest

from backend.app.core.errors import APIError
from backend.app.services.wallet.models import PhoneConfirmationStatus, WalletStatus
from backend.app.services.wallet.service import WalletService


def test_wallet_purchase_is_idempotent() -> None:
    wallet = WalletService()

    first = asyncio.run(
        wallet.process_purchase(
            route_id="route-1", requirement_id="hu-vignette-10d"
        )
    )
    duplicate = asyncio.run(
        wallet.process_purchase(
            route_id="route-1", requirement_id="hu-vignette-10d"
        )
    )

    assert first.transaction_id == duplicate.transaction_id
    assert first.wallet_status == WalletStatus.COMPLETED
    assert duplicate.status == WalletStatus.DUPLICATE


def test_phone_confirmation_can_be_sent_for_transaction() -> None:
    wallet = WalletService()
    transaction = asyncio.run(
        wallet.process_purchase(route_id="route-1", requirement_id="req-1")
    )

    updated = asyncio.run(wallet.send_phone_confirmation(transaction.transaction_id))

    assert updated.phone_confirmation_status == PhoneConfirmationStatus.SENT


def test_declined_purchase_and_failed_phone_confirmation_are_simulated() -> None:
    wallet = WalletService()
    declined = asyncio.run(
        wallet.decline_purchase(route_id="route-1", requirement_id="req-1")
    )
    transaction = asyncio.run(
        wallet.process_purchase(route_id="route-2", requirement_id="req-2")
    )
    failed = asyncio.run(wallet.fail_phone_confirmation(transaction.transaction_id))

    assert declined.wallet_status == WalletStatus.DECLINED
    assert declined.phone_confirmation_status == PhoneConfirmationStatus.FAILED
    assert failed.phone_confirmation_status == PhoneConfirmationStatus.FAILED


def test_wallet_purchase_transitions_from_processing_to_completed() -> None:
    wallet = WalletService()
    transaction = asyncio.run(
        wallet.initiate_purchase(route_id="route-1", requirement_id="req-1")
    )
    completed = asyncio.run(wallet.complete_purchase(transaction.transaction_id))

    assert transaction.wallet_status == WalletStatus.PROCESSING
    assert completed.wallet_status == WalletStatus.COMPLETED


def test_wallet_can_prepare_purchase_in_ready_state() -> None:
    transaction = asyncio.run(
        WalletService().prepare_purchase(route_id="route-1", requirement_id="req-1")
    )

    assert transaction.wallet_status == WalletStatus.READY
    assert transaction.phone_confirmation_status == PhoneConfirmationStatus.PENDING


def test_booking_requires_guests_and_restaurant_time() -> None:
    wallet = WalletService()

    with pytest.raises(APIError) as guest_error:
        asyncio.run(
            wallet.process_booking(
                route_id="route-1", search_id="search-1", result_id="hotel-1",
                booking_type="hotel_room", guests=0, booking_date="2026-09-17",
            )
        )
    assert guest_error.value.code == "INVALID_GUEST_COUNT"

    with pytest.raises(APIError) as time_error:
        asyncio.run(
            wallet.process_booking(
                route_id="route-1", search_id="search-1", result_id="restaurant-1",
                booking_type="restaurant_table", guests=2, booking_date="2026-09-17",
            )
        )
    assert time_error.value.code == "MISSING_BOOKING_TIME"


def test_hotel_booking_preserves_guest_count() -> None:
    booking = asyncio.run(
        WalletService().process_booking(
            route_id="route-1", search_id="search-1", result_id="hotel-1",
            booking_type="hotel_room", guests=2, booking_date="2026-09-17",
        )
    )

    assert booking.guests == 2
    assert booking.wallet_status == WalletStatus.COMPLETED
