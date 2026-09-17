from dataclasses import dataclass
from enum import StrEnum


class WalletStatus(StrEnum):
    READY = "ready"
    PROCESSING = "processing"
    COMPLETED = "completed"
    DECLINED = "declined"
    DUPLICATE = "duplicate"


class PhoneConfirmationStatus(StrEnum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class WalletTransaction:
    transaction_id: str
    request_key: str
    action: str
    route_id: str
    status: WalletStatus = WalletStatus.COMPLETED
    wallet_status: WalletStatus = WalletStatus.COMPLETED
    phone_confirmation_status: PhoneConfirmationStatus = PhoneConfirmationStatus.SENT
    amount_eur: float = 0.0
    currency: str = "EUR"
    requirement_id: str | None = None


@dataclass(frozen=True, slots=True)
class BookingConfirmation:
    booking_id: str
    confirmation_code: str
    request_key: str
    route_id: str
    search_id: str
    result_id: str
    booking_type: str
    guests: int
    date: str
    time: str | None = None
    wallet_status: WalletStatus = WalletStatus.COMPLETED
    phone_confirmation_status: PhoneConfirmationStatus = PhoneConfirmationStatus.SENT