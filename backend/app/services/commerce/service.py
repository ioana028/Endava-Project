from collections.abc import Callable
from datetime import date, timedelta
import re

from ...core.errors import APIError
from ..wallet.service import WalletService
from .catalog import vignette_amount_eur


def normalize_booking_date(value: str | None, today: date | None = None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().casefold()
    today = today or date.today()
    if normalized == "today":
        return today.isoformat()
    if normalized == "tonight":
        return today.isoformat()
    if normalized == "tomorrow":
        return (today + timedelta(days=1)).isoformat()
    return value


def normalize_booking_time(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().casefold().replace(" ", "")
    match = re.fullmatch(r"(\d{1,2})(?::(\d{2}))?(am|pm)", normalized)
    if match:
        hour = int(match.group(1))
        minutes = int(match.group(2) or "00")
        if 1 <= hour <= 12 and 0 <= minutes <= 59:
            if match.group(3) == "pm" and hour != 12:
                hour += 12
            if match.group(3) == "am" and hour == 12:
                hour = 0
            return f"{hour:02d}:{minutes:02d}"
    match = re.fullmatch(r"(\d{1,2}):(\d{2})", normalized)
    if match and 0 <= int(match.group(1)) <= 23 and 0 <= int(match.group(2)) <= 59:
        return f"{int(match.group(1)):02d}:{int(match.group(2)):02d}"
    return value


class CommerceService:
    def __init__(
        self,
        route_service: object,
        wallet_service: WalletService,
        today: Callable[[], date] | None = None,
    ) -> None:
        self._route_service = route_service
        self._wallet = wallet_service
        self._today = today or date.today

    async def purchase_vignette(
        self,
        route_id: str,
        requirement_id: str,
        confirmation: str,
        request_key: str | None = None,
    ):
        if confirmation != "confirmed":
            raise APIError(422, "CONFIRMATION_REQUIRED", "Purchase confirmation is required.")
        self._require_active_route(route_id)
        requirements = getattr(self._route_service, "active_route_requirements", ())
        requirement = next((item for item in requirements if item.id == requirement_id), None)
        if requirement is None:
            raise APIError(422, "STALE_REQUIREMENT", "The vignette requirement is no longer current.")
        if requirement.kind != "vignette":
            raise APIError(422, "INVALID_REQUIREMENT", "The selected requirement is not a vignette.")
        transaction = await self._wallet.process_purchase(
            route_id=route_id,
            requirement_id=requirement_id,
            request_key=request_key,
            amount_eur=vignette_amount_eur(requirement_id),
        )
        if transaction.status.value in {"completed", "duplicate"}:
            mark_purchased = getattr(self._route_service, "mark_vignette_purchased", None)
            if mark_purchased is not None:
                mark_purchased(requirement_id)
        return transaction

    async def book(
        self,
        *,
        route_id: str,
        search_id: str,
        result_id: str,
        booking_type: str,
        guests: int,
        confirmation: str,
        booking_date: str | None = None,
        booking_time: str | None = None,
        request_key: str | None = None,
    ):
        if confirmation != "confirmed":
            raise APIError(422, "CONFIRMATION_REQUIRED", "Booking confirmation is required.")
        self._require_active_route(route_id)
        if search_id != getattr(self._route_service, "active_search_id", None):
            raise APIError(409, "STALE_SEARCH", "The selected search is no longer current.")
        results = getattr(self._route_service, "active_search_results", {})
        result = results.get(result_id)
        if result is None or result.category not in {"hotel", "restaurant"}:
            raise APIError(409, "STALE_RESULT", "The selected provider result is no longer current.")
        expected_category = "hotel" if booking_type == "hotel_room" else "restaurant"
        if result.category != expected_category:
            raise APIError(422, "INVALID_BOOKING_TYPE", "Booking type does not match the selected result.")
        return await self._wallet.process_booking(
            route_id=route_id, search_id=search_id, result_id=result_id,
            booking_type=booking_type, guests=guests, booking_date=booking_date,
            booking_time=normalize_booking_time(booking_time), request_key=request_key,
        )

    async def book_hotel_room(
        self, *, route_id: str, search_id: str, result_id: str,
        booking_type: str, guests: int, date: str,
        time: str | None = None, confirmation: str,
        request_key: str | None = None,
    ):
        return await self.book(
            route_id=route_id, search_id=search_id, result_id=result_id,
            booking_type=booking_type, guests=guests, confirmation=confirmation,
            booking_date=normalize_booking_date(date, self._today()), booking_time=normalize_booking_time(time), request_key=request_key,
        )

    async def book_restaurant_table(
        self, *, route_id: str, search_id: str, result_id: str,
        booking_type: str, guests: int, date: str,
        time: str | None = None, confirmation: str,
        request_key: str | None = None,
    ):
        normalized_date = normalize_booking_date(date, self._today())
        normalized_time = normalize_booking_time(time)
        if normalized_time is None and date.strip().casefold() == "tonight":
            normalized_time = "20:00"
        return await self.book(
            route_id=route_id, search_id=search_id, result_id=result_id,
            booking_type=booking_type, guests=guests, confirmation=confirmation,
            booking_date=normalized_date, booking_time=normalized_time, request_key=request_key,
        )

    def _require_active_route(self, route_id: str) -> None:
        if route_id != getattr(self._route_service, "active_route_id", None):
            raise APIError(409, "STALE_ROUTE", "The selected route is no longer current.")