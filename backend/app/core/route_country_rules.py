from __future__ import annotations

import json
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_ROUTE_COUNTRY_RULES_PATH = PROJECT_ROOT / "data" / "routes" / "route_country_rules.json"

DEFAULT_ROUTE_COUNTRY_RULES: dict[str, Any] = {
    "country_aliases": {
        "Austria": ["Austria", "Vienna"],
        "Hungary": ["Hungary", "Budapest"],
    },
    "border_crossings": [
        {
            "id": "Austria-Hungary",
            "from_country": "Austria",
            "to_country": "Hungary",
            "route_requirements": ["Hungarian motorway vignette"],
        }
    ],
}


def load_route_country_rules(
    path: Path = DEFAULT_ROUTE_COUNTRY_RULES_PATH,
) -> dict[str, Any]:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return DEFAULT_ROUTE_COUNTRY_RULES

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return DEFAULT_ROUTE_COUNTRY_RULES

    if not isinstance(parsed, dict) or not isinstance(parsed.get("border_crossings", []), list):
        return DEFAULT_ROUTE_COUNTRY_RULES

    merged = dict(DEFAULT_ROUTE_COUNTRY_RULES)
    merged.update(parsed)
    merged["country_aliases"] = {
        **DEFAULT_ROUTE_COUNTRY_RULES.get("country_aliases", {}),
        **parsed.get("country_aliases", {}),
    }
    return merged


def detect_border_crossings(
    origin_display_name: str,
    destination_display_name: str,
    rules: dict[str, Any] | None = None,
) -> list[str]:
    rules = rules or load_route_country_rules()
    origin_text = _normalize_country_text(origin_display_name)
    destination_text = _normalize_country_text(destination_display_name)
    aliases = rules.get("country_aliases", {}) if isinstance(rules, dict) else {}

    crossings: list[str] = []
    for crossing in rules.get("border_crossings", []):
        if not isinstance(crossing, dict):
            continue

        from_country = str(crossing.get("from_country", ""))
        to_country = str(crossing.get("to_country", ""))
        crossing_id = str(crossing.get("id", ""))

        if _contains_country(origin_text, from_country, aliases) and _contains_country(
            destination_text, to_country, aliases
        ):
            crossings.append(crossing_id)

    return crossings


def derive_route_requirements(
    border_crossings: list[str],
    rules: dict[str, Any] | None = None,
) -> list[str]:
    rules = rules or load_route_country_rules()

    requirements: list[str] = []
    seen: set[str] = set()

    for crossing in rules.get("border_crossings", []):
        if not isinstance(crossing, dict):
            continue

        crossing_id = str(crossing.get("id", ""))
        if crossing_id not in border_crossings:
            continue

        for requirement in crossing.get("route_requirements", []):
            requirement_text = str(requirement)
            if requirement_text not in seen:
                requirements.append(requirement_text)
                seen.add(requirement_text)

    return requirements


def _normalize_country_text(value: str) -> str:
    return value.casefold()


def _contains_country(text: str, country: str, aliases: dict[str, list[str]] | None = None) -> bool:
    aliases = aliases or {}
    possible_values = [country.casefold()]
    for alias in aliases.get(country, []):
        possible_values.append(alias.casefold())

    return any(value in text for value in possible_values)
