from dataclasses import replace
from datetime import date
from hashlib import sha256
import re
from typing import Any

from ...core.errors import APIError
from .models import (
    BookingConfirmation,
    PhoneConfirmationStatus,
    WalletStatus,
    WalletTransaction,
)


class WalletService:
    """In-memory wallet simulation; a browser refresh starts a new instance."""

    def __init__(self) -> None:
        self._transactions: dict[str, WalletTransaction] = {}
        self._bookings: dict[str, BookingConfirmation] = {}

    async def prepare_purchase(
        self, *, route_id: str, requirement_id: str, request_key: str | None = None
    ) -> WalletTransaction:
        key = request_key or self._key("purchase", route_id, requirement_id)
        existing = self._transactions.get(key)
        if existing is not None:
            return replace(existing, status=WalletStatus.DUPLICATE)
        transaction = WalletTransaction(
            transaction_id=f"txn-{self._stable_id(key)}",
            request_key=key,
            action="vignette_purchase",
            route_id=route_id,
            status=WalletStatus.READY,
            wallet_status=WalletStatus.READY,
            phone_confirmation_status=PhoneConfirmationStatus.PENDING,
            requirement_id=requirement_id,
        )
        self._transactions[key] = transaction
        return transaction

    async def initiate_purchase(
        self, *, route_id: str, requirement_id: str, request_key: str | None = None
    ) -> WalletTransaction:
        key = request_key or self._key("purchase", route_id, requirement_id)
        transaction = self._transactions.get(key)
        if transaction is not None:
            return replace(transaction, status=WalletStatus.DUPLICATE)
        transaction = WalletTransaction(
            transaction_id=f"txn-{self._stable_id(key)}",
            request_key=key,
            action="vignette_purchase",
            route_id=route_id,
            status=WalletStatus.PROCESSING,
            wallet_status=WalletStatus.PROCESSING,
            phone_confirmation_status=PhoneConfirmationStatus.PENDING,
            requirement_id=requirement_id,
        )
        self._transactions[key] = transaction
        return transaction

    async def complete_purchase(self, transaction_id: str) -> WalletTransaction:
        for key, transaction in self._transactions.items():
            if transaction.transaction_id == transaction_id:
                updated = replace(
                    transaction,
                    status=WalletStatus.COMPLETED,
                    wallet_status=WalletStatus.COMPLETED,
                    phone_confirmation_status=PhoneConfirmationStatus.SENT,
                )
                self._transactions[key] = updated
                return updated
        raise APIError(404, "TRANSACTION_NOT_FOUND", "The wallet transaction was not found.")

    async def process_purchase(
        self,
        *,
        route_id: str,
        requirement_id: str,
        request_key: str | None = None,
        amount_eur: float = 0.0,
    ) -> WalletTransaction:
        key = request_key or self._key("purchase", route_id, requirement_id)
        existing = self._transactions.get(key)
        if existing is not None:
            return replace(existing, status=WalletStatus.DUPLICATE)
        transaction = WalletTransaction(
            transaction_id=f"txn-{self._stable_id(key)}",
            request_key=key,
            action="vignette_purchase",
            route_id=route_id,
            amount_eur=amount_eur,
            requirement_id=requirement_id,
        )
        self._transactions[key] = transaction
        return transaction

    async def decline_purchase(
        self, *, route_id: str, requirement_id: str, request_key: str | None = None
    ) -> WalletTransaction:
        key = request_key or self._key("purchase", route_id, requirement_id)
        existing = self._transactions.get(key)
        if existing is not None:
            return replace(existing, status=WalletStatus.DUPLICATE)
        transaction = WalletTransaction(
            transaction_id=f"txn-{self._stable_id(key)}",
            request_key=key,
            action="vignette_purchase",
            route_id=route_id,
            status=WalletStatus.DECLINED,
            wallet_status=WalletStatus.DECLINED,
            phone_confirmation_status=PhoneConfirmationStatus.FAILED,
            requirement_id=requirement_id,
        )
        self._transactions[key] = transaction
        return transaction

    async def process_booking(
        self,
        *,
        route_id: str,
        search_id: str,
        result_id: str,
        booking_type: str,
        guests: int,
        booking_date: str | None = None,
        booking_time: str | None = None,
        request_key: str | None = None,
    ) -> BookingConfirmation:
        booking_date = booking_date or date.today().isoformat()
        self._validate_booking(booking_type, guests, booking_date, booking_time)
        key = request_key or self._key(
            "booking", route_id, search_id, result_id, booking_type,
            guests, booking_date, booking_time or "",
        )
        existing = self._bookings.get(key)
        if existing is not None:
            return existing
        suffix = self._stable_id(key)
        booking = BookingConfirmation(
            booking_id=f"booking-{suffix}",
            confirmation_code=f"CONF-{suffix[:8].upper()}",
            request_key=key,
            route_id=route_id,
            search_id=search_id,
            result_id=result_id,
            booking_type=booking_type,
            guests=guests,
            date=booking_date,
            time=booking_time,
        )
        self._bookings[key] = booking
        return booking

    async def send_phone_confirmation(self, transaction_id: str) -> WalletTransaction:
        for key, transaction in self._transactions.items():
            if transaction.transaction_id == transaction_id:
                updated = replace(
                    transaction,
                    phone_confirmation_status=PhoneConfirmationStatus.SENT,
                )
                self._transactions[key] = updated
                return updated
        raise APIError(404, "TRANSACTION_NOT_FOUND", "The wallet transaction was not found.")

    async def fail_phone_confirmation(self, transaction_id: str) -> WalletTransaction:
        for key, transaction in self._transactions.items():
            if transaction.transaction_id == transaction_id:
                updated = replace(
                    transaction,
                    phone_confirmation_status=PhoneConfirmationStatus.FAILED,
                )
                self._transactions[key] = updated
                return updated
        raise APIError(404, "TRANSACTION_NOT_FOUND", "The wallet transaction was not found.")

    @staticmethod
    def _validate_booking(
        booking_type: str, guests: int, booking_date: str, booking_time: str | None
    ) -> None:
        if booking_type not in {"hotel_room", "restaurant_table"}:
            raise APIError(422, "INVALID_BOOKING_TYPE", "The booking type is invalid.")
        if guests < 1:
            raise APIError(422, "INVALID_GUEST_COUNT", "Guest count must be at least one.")
        try:
            date.fromisoformat(booking_date)
        except ValueError as error:
            raise APIError(422, "INVALID_BOOKING_DATE", "Date must use YYYY-MM-DD format.") from error
        if booking_type == "restaurant_table" and not booking_time:
            raise APIError(422, "MISSING_BOOKING_TIME", "Restaurant bookings require a time.")
        if booking_time is not None and not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", booking_time):
            raise APIError(422, "INVALID_BOOKING_TIME", "Time must use HH:MM format.")

    @staticmethod
    def _key(*parts: Any) -> str:
        return "|".join(str(part) for part in parts)

    @staticmethod
    def _stable_id(value: str) -> str:
        return sha256(value.encode("utf-8")).hexdigest()[:12]