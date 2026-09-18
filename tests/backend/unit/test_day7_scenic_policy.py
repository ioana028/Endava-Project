from backend.app.models.contracts import StopPinpoint
from backend.app.services.trip.deterministic import rank_pois, rank_scenic_pois
from backend.app.services.trip.ports import POICandidate


def candidate(
    stop_id: str,
    tag: str,
    route_relevance: float,
    quality: float = 4.0,
) -> POICandidate:
    return POICandidate(
        stop=StopPinpoint(
            id=stop_id,
            name=stop_id,
            category="attraction",
            coords=(17.0, 48.0),
            tag=tag,
        ),
        route_relevance=route_relevance,
        quality=quality,
    )


def test_scenic_ranking_prefers_explicit_scenic_metadata() -> None:
    candidates = [
        candidate("fastest-view", "ordinary stop", 0.99, 5.0),
        candidate("scenic-lake", "lake viewpoint", 0.70, 3.5),
    ]

    assert [item.stop.id for item in rank_scenic_pois(candidates)] == [
        "scenic-lake",
        "fastest-view",
    ]


def test_scenic_ranking_is_distinct_from_fastest_ranking() -> None:
    candidates = [
        candidate("fastest-view", "ordinary stop", 0.99, 5.0),
        candidate("scenic-lake", "lake viewpoint", 0.70, 3.5),
    ]

    fastest = rank_pois(candidates)
    scenic = rank_scenic_pois(candidates)

    assert fastest[0].stop.id == "fastest-view"
    assert scenic[0].stop.id == "scenic-lake"


def test_scenic_route_stop_selection_uses_scenic_ranking() -> None:
    from backend.app.services.trip.deterministic import select_route_stops

    stops = [
        StopPinpoint(
            id="ordinary", name="ordinary", category="attraction",
            coords=(17.5, 47.90), tag="ordinary stop", rating=5,
        ),
        StopPinpoint(
            id="lake", name="lake", category="attraction",
            coords=(17.6, 47.87), tag="lake viewpoint", rating=3,
        ),
    ]

    results = select_route_stops(
        stops, ((16.37, 48.20), (19.04, 47.50)), location="route", scenic=True
    )

    assert results[0].id == "lake"
