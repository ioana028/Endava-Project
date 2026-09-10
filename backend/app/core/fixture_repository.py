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
                Partner.model_validate(item)
                for item in self._read_json(self._partners_path)
            )
        except (OSError, json.JSONDecodeError, ValidationError, TypeError) as exc:
            raise RuntimeError("Unable to load backend fixtures") from exc

        self._fixtures = Fixtures(telemetry=telemetry, partners=partners)
        return self._fixtures

    @property
    def fixtures(self) -> Fixtures:
        if self._fixtures is None:
            raise RuntimeError("Fixtures have not been loaded")
        return self._fixtures

    @staticmethod
    def _read_json(path: Path) -> object:
        with path.open(encoding="utf-8") as fixture_file:
            return json.load(fixture_file)