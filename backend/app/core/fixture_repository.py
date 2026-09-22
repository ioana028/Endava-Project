import json
from pathlib import Path

from pydantic import ValidationError

from ..models.fixtures import Fixtures, Partner, VehicleState


class FixtureRepository:
    def __init__(self, telemetry_path: Path, partners_path: Path) -> None:
        self._telemetry_path = telemetry_path
        self._partners_path = partners_path
        self._fixtures: Fixtures | None = None

    def load(self) -> Fixtures:
        try:
            telemetry = VehicleState.model_validate(self._read_json(self._telemetry_path))
            partners = tuple(
                Partner.model_validate(self._normalize_partner(item))
                for item in self._read_json(self._partners_path)
            )
        except (OSError, json.JSONDecodeError, ValidationError, TypeError) as exc:
            raise RuntimeError("Unable to load backend fixtures") from exc

        self._fixtures = Fixtures(telemetry=telemetry, partners=partners)
        return self._fixtures

    @staticmethod
    def _normalize_partner(item: object) -> object:
        if not isinstance(item, dict):
            return item

        normalized = dict(item)
        coordinates = normalized.get("coords")
        kind = normalized.get("kind")
        if kind is None:
            normalized["kind"] = "location" if coordinates is not None else "brand"
        elif kind == "network":
            # Preserve the legacy provider-facing name while treating it as a brand record.
            normalized["kind"] = "brand"

        brand = normalized.get("brand") or normalized.get("name") or ""
        provider_brands = tuple(normalized.get("providerBrands") or ())
        normalized["brandAliases"] = tuple(
            dict.fromkeys(
                (*tuple(normalized.get("brandAliases") or ()), brand, *provider_brands)
            )
        )
        normalized["providerBrands"] = provider_brands
        normalized.setdefault(
            "benefitScope",
            "brand-wide" if normalized["kind"] == "brand" else "location",
        )
        normalized.setdefault(
            "eligibleLocations",
            ("all-matched-locations",) if normalized["kind"] == "brand" else (),
        )
        normalized.setdefault("benefitSource", "fixture")
        normalized.setdefault("verified", True)
        return normalized

    @property
    def fixtures(self) -> Fixtures:
        if self._fixtures is None:
            raise RuntimeError("Fixtures have not been loaded")
        return self._fixtures

    @staticmethod
    def _read_json(path: Path) -> object:
        with path.open(encoding="utf-8") as fixture_file:
            return json.load(fixture_file)