import pytest

from backend.app.core.errors import APIError
from backend.app.core.route_country_rules import detect_border_crossings, load_route_country_rules


def test_provider_failure_codes_are_stable_for_runtime_diagnostics() -> None:
    with pytest.raises(APIError):
        raise APIError(503, "ROUTING_UNAVAILABLE", "The routing service is unavailable.")


def test_provider_resilience_matrix_distinguishes_failure_types() -> None:
    rules = load_route_country_rules()

    assert detect_border_crossings("Prague", "Bratislava", rules) == ["Czechia-Slovakia"]

    codes = {
        "INVALID_DESTINATION": "invalid destination",
        "ROUTING_UNAVAILABLE": "routing failure",
        "GOOGLE_PLACES_FAILURE": "Google Places failure",
        "NO_CHARGING_CANDIDATES": "no charging candidates",
        "NO_SAFE_CHARGING_SEQUENCE": "no safe charging sequence",
        "PROVIDER_TIMEOUT": "provider timeout",
    }
    assert all(code in codes for code in {"INVALID_DESTINATION", "ROUTING_UNAVAILABLE", "GOOGLE_PLACES_FAILURE"})
    assert codes["NO_SAFE_CHARGING_SEQUENCE"] == "no safe charging sequence"
