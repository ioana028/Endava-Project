from collections.abc import Iterable

from ...models.contracts import BorderCrossing, RouteRequirement


_COUNTRY_NAMES = {
    "AT": "Austria",
    "AUSTRIA": "Austria",
    "HU": "Hungary",
    "HUNGARY": "Hungary",
    "SK": "Slovakia",
    "SLOVAKIA": "Slovakia",
}


def country_code(country: str) -> str:
    return country.strip().upper()


def detect_border_crossings(countries: Iterable[str]) -> list[BorderCrossing]:
    normalized = [country_code(country) for country in countries]
    return [
        BorderCrossing(
            from_country=_COUNTRY_NAMES.get(source, source),
            to_country=_COUNTRY_NAMES.get(target, target),
        )
        for source, target in zip(normalized, normalized[1:])
        if source != target
    ]


def derive_requirements(countries: Iterable[str]) -> list[RouteRequirement]:
    normalized = {country_code(country) for country in countries}
    requirements: list[RouteRequirement] = []
    if "AT" in normalized:
        requirements.append(
            RouteRequirement(
                id="at-motorway-vignette",
                name="Austrian motorway vignette",
                country="AT",
                kind="vignette",
            )
        )
    if "HU" in normalized:
        requirements.append(
            RouteRequirement(
                id="hu-motorway-vignette",
                name="Hungarian motorway vignette",
                country="HU",
                kind="vignette",
            )
        )
    return requirements