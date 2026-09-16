from fastapi import APIRouter, Request

from ..core.errors import APIError
from ..models.contracts import (
    AssistantIntent,
    RealtimeSessionResponse,
    RealtimeToolRouteRequest,
    RealtimeToolRouteResponse,
    RealtimeToolRerouteRequest,
    RealtimeToolRerouteResponse,
    RealtimeToolSearchRoutePoiRequest,
    RealtimeToolSearchRoutePoiResponse,
    RealtimeToolSearchStopAmenitiesRequest,
    RealtimeToolSearchStopAmenitiesResponse,
)


router = APIRouter(prefix="/api/assistant", tags=["assistant"])


def _active_context_id(route_service: object, name: str) -> str | None:
    public_value = getattr(route_service, name, None)
    if public_value is not None:
        return public_value
    return getattr(route_service, f"_{name}", None)


@router.post(
    "/realtime/session",
    response_model=RealtimeSessionResponse,
)
async def realtime_session(request: Request) -> RealtimeSessionResponse:
    client_secret = await request.app.state.realtime_provider.create_client_secret()
    return RealtimeSessionResponse(
        client_secret=client_secret,
        model=request.app.state.settings.realtime_model,
    )


@router.post(
    "/realtime/tools/plan-route",
    response_model=RealtimeToolRouteResponse,
)
async def realtime_plan_route(
    payload: RealtimeToolRouteRequest,
    request: Request,
) -> RealtimeToolRouteResponse:
    route = await request.app.state.route_service.plan(
        AssistantIntent(destination=payload.destination, priority=payload.priority)
    )
    return RealtimeToolRouteResponse(route=route)


@router.post(
    "/realtime/tools/search-route-poi",
    response_model=RealtimeToolSearchRoutePoiResponse,
)
async def realtime_search_route_poi(
    payload: RealtimeToolSearchRoutePoiRequest,
    request: Request,
) -> RealtimeToolSearchRoutePoiResponse:
    results = await request.app.state.route_service.search_route_poi(
        category=payload.category,
        location=payload.location,
        preference=payload.preference,
    )
    return RealtimeToolSearchRoutePoiResponse(
        results=results,
        route_id=_active_context_id(request.app.state.route_service, "active_route_id"),
        search_id=_active_context_id(request.app.state.route_service, "active_search_id"),
    )


@router.post(
    "/realtime/tools/search-stop-amenities",
    response_model=RealtimeToolSearchStopAmenitiesResponse,
)
async def realtime_search_stop_amenities(
    payload: RealtimeToolSearchStopAmenitiesRequest,
    request: Request,
) -> RealtimeToolSearchStopAmenitiesResponse:
    search = getattr(request.app.state.route_service, "search_stop_amenities", None)
    if search is None:
        raise APIError(
            503,
            "AMENITIES_UNAVAILABLE",
            "Nearby amenity search is not available yet.",
        )

    result = await search(
        stop_id=payload.stop_id,
        route_id=payload.route_id,
        search_id=payload.search_id,
        categories=payload.categories,
    )
    return RealtimeToolSearchStopAmenitiesResponse(
        selected_stop_name=result["selected_stop_name"],
        results=result.get("results", []),
        radius_meters=result.get("radius_meters", 500),
        route_id=payload.route_id,
        search_id=payload.search_id,
    )


@router.post(
    "/realtime/tools/reroute-through-poi",
    response_model=RealtimeToolRerouteResponse,
)
async def realtime_reroute_through_poi(
    payload: RealtimeToolRerouteRequest,
    request: Request,
) -> RealtimeToolRerouteResponse:
    reroute = getattr(request.app.state.route_service, "reroute_through_poi", None)
    if reroute is None:
        raise APIError(
            503,
            "REROUTE_UNAVAILABLE",
            "Rerouting through a selected place is not available yet.",
        )

    route = await reroute(
        poi_id=payload.poi_id,
        route_id=payload.route_id,
        search_id=payload.search_id,
        coords=payload.coords,
        priority=payload.priority,
    )
    return RealtimeToolRerouteResponse(route=route)