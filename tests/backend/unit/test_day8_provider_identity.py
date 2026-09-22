import asyncio

from backend.app.integrations.places.google import GooglePlacesProvider
from backend.app.models.contracts import AssistantIntent, Coordinates, RoutePriority
from backend.app.services.trip.ports import GeocodedPlace, ProviderRoute
from backend.app.services.trip.service import RouteService


class FakeResponse:
    def __init__(self, payload: object) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> object:
        return self._payload


class FakePlacesClient:
    responses: list[FakeResponse] = []

    def __init__(self, **kwargs: object) -> None:
        self.timeout = kwargs["timeout"]

    async def __aenter__(self) -> "FakePlacesClient":
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def post(self, url: str, **kwargs: object) -> FakeResponse:
        del url, kwargs
        return self.responses.pop(0)


def test_google_places_accepts_string_display_names_for_stable_provider_identity(
    monkeypatch,
) -> None:
    FakePlacesClient.responses = [
        FakeResponse(
            {
                "places": [
                    {
                        "id": "places/shell-recharge",
                        "displayName": "Shell Recharge",
                        "location": {"longitude": 16.06, "latitude": 48.0},
                        "types": ["electric_vehicle_charging_station"],
                        "rating": 4.6,
                        "formattedAddress": "Vienna",
                    }
                ]
            }
        ),
        FakeResponse({"places": []}),
    ]
    monkeypatch.setattr(
        "backend.app.integrations.places.google.httpx.AsyncClient",
        FakePlacesClient,
    )

    results = asyncio.run(
        GooglePlacesProvider("test-key").search(
            "charging",
            route=(
                (16.0, 48.0),
                (16.1, 48.0),
                (16.2, 48.0),
            ),
        )
    )

    assert len(results) == 1
    assert results[0].id == "places/shell-recharge"
    assert results[0].name == "Shell Recharge"


def test_confirming_multi_stop_charging_keeps_provider_waypoints_in_order() -> None:
    class RecordingRoutingProvider:
        def __init__(self) -> None:
            self.waypoints = None

        async def geocode(self, place: str) -> GeocodedPlace:
            return GeocodedPlace(
                display_name=place,
                coordinates=Coordinates(lng=16.0, lat=48.0),
            )

        async def route(
            self,
            origin: GeocodedPlace,
            destination: GeocodedPlace,
            priority: RoutePriority,
            waypoints: tuple[GeocodedPlace, ...] | None = None,
        ) -> ProviderRoute:
            del origin, destination, priority
            self.waypoints = waypoints
            return ProviderRoute(
                distance_meters=120_000,
                duration_seconds=7_200,
                geometry=((16.0, 48.0), (16.5, 48.1), (17.0, 48.2), (19.0, 47.5)),
            )

    class EmptyPlacesProvider:
        async def search(self, *args, **kwargs):
            del args, kwargs
            return []

    provider = RecordingRoutingProvider()
    route_service = RouteService(
        provider,
        __import__("backend.app.core.fixture_repository", fromlist=["FixtureRepository"]).FixtureRepository(
            __import__("pathlib").Path("data/vehicles/telemetry.json"),
            __import__("pathlib").Path("data/partners/partners.json"),
        ),
        places_provider=EmptyPlacesProvider(),
    )
    route_service._active_provider_route = ProviderRoute(
        distance_meters=120_000,
        duration_seconds=7_200,
        geometry=((16.0, 48.0), (17.0, 48.0), (19.0, 47.5)),
    )
    route_service._active_route_id = "route-1"
    route_service._active_origin = GeocodedPlace("Vienna", Coordinates(lng=16.0, lat=48.0))
    route_service._active_destination = GeocodedPlace("Budapest", Coordinates(lng=19.0, lat=47.5))
    route_service._active_priority = RoutePriority.FASTEST
    route_service._pending_charging_stops = [
        __import__("backend.app.models.contracts", fromlist=["StopPinpoint"]).StopPinpoint(
            id="charger-b",
            name="Second Charger",
            category="charging",
            coords=(17.4, 48.1),
            mandatory=True,
            charging_duration_minutes=20,
        ),
        __import__("backend.app.models.contracts", fromlist=["StopPinpoint"]).StopPinpoint(
            id="charger-a",
            name="First Charger",
            category="charging",
            coords=(16.6, 48.2),
            mandatory=True,
            charging_duration_minutes=15,
        ),
    ]

    result = asyncio.run(route_service.confirm_charging_stop("route-1"))

    assert provider.waypoints is not None
    assert [point.display_name for point in provider.waypoints] == [
        "Second Charger",
        "First Charger",
    ]
    assert result["route"].stops[0].name == "Second Charger"
    assert result["route"].stops[1].name == "First Charger"
