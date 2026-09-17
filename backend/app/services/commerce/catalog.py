import json
from pathlib import Path

from ...core.errors import APIError


CATALOG_PATH = Path(__file__).resolve().parents[4] / "data" / "commerce" / "catalog.json"


def vignette_amount_eur(requirement_id: str) -> float:
    try:
        with CATALOG_PATH.open(encoding="utf-8") as catalog_file:
            catalog = json.load(catalog_file)
        amount = catalog["vignettes"][requirement_id]["amountEur"]
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as error:
        raise APIError(422, "UNKNOWN_REQUIREMENT_PRICE", "The vignette price is unavailable.") from error
    if not isinstance(amount, (int, float)) or amount < 0:
        raise APIError(422, "INVALID_REQUIREMENT_PRICE", "The vignette price is invalid.")
    return float(amount)