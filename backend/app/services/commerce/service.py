from ...core.errors import APIError
from ..wallet.service import WalletService


class CommerceService:
    def __init__(self, route_service: object, wallet_service: WalletService) -> None:
        self._route_service = route_service
        self._wallet = wallet_service

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
        return await self._wallet.process_purchase(
            route_id=route_id,
            requirement_id=requirement_id,
            request_key=request_key,
        )

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
            booking_time=booking_time, request_key=request_key,
        )

    def _require_active_route(self, route_id: str) -> None:
        if route_id != getattr(self._route_service, "active_route_id", None):
            raise APIError(409, "STALE_ROUTE", "The selected route is no longer current.")