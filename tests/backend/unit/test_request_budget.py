import pytest

from backend.app.core.errors import APIError
from backend.app.core.request_budget import RequestBudget


def test_request_budget_resets_and_reports_remaining_capacity() -> None:
    budget = RequestBudget(maximum=2)

    budget.consume(provider="routing", method="route", reason="base_route")
    assert budget.remaining == 1

    budget.consume(provider="places", method="search", reason="poi_attraction")
    assert budget.remaining == 0

    budget.reset()
    assert budget.used == 0
    assert budget.remaining == 2


def test_request_budget_rejects_calls_after_ceiling() -> None:
    budget = RequestBudget(maximum=1)
    budget.consume(provider="routing", method="route", reason="base_route")

    with pytest.raises(APIError) as error:
        budget.consume(provider="places", method="search", reason="poi_restaurant")

    assert error.value.status_code == 429
    assert error.value.code == "PROVIDER_BUDGET_EXHAUSTED"
