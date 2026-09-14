from fastapi import APIRouter, Request

from ..models.contracts import (
    AssistantIntent,
    RealtimeSessionResponse,
    RealtimeToolRouteRequest,
    RealtimeToolRouteResponse,
    RealtimeToolSearchRoutePoiRequest,
    RealtimeToolSearchRoutePoiResponse,
)


router = APIRouter(prefix="/api/assistant", tags=["assistant"])

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
    return RealtimeToolSearchRoutePoiResponse(results=results)