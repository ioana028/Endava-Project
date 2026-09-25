from dataclasses import dataclass
from hashlib import sha256
import logging

from .errors import APIError


LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class RequestBudget:
    maximum: int = 20
    used: int = 0

    def reset(self) -> None:
        self.used = 0

    def consume(self, *, provider: str, method: str, reason: str) -> None:
        if self.used >= self.maximum:
            raise APIError(
                429,
                "PROVIDER_BUDGET_EXHAUSTED",
                "The request budget for this route session has been reached.",
            )
        self.used += 1
        fingerprint = sha256(
            f"{provider}|{method}|{reason}".encode("utf-8")
        ).hexdigest()[:16]
        LOGGER.info(
            "provider_request_budget provider=%s method=%s reason=%s fingerprint=%s used=%d remaining=%d",
            provider,
            method,
            reason,
            fingerprint,
            self.used,
            self.remaining,
        )

    @property
    def remaining(self) -> int:
        return max(0, self.maximum - self.used)
