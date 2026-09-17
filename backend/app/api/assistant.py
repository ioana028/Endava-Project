from collections.abc import Awaitable
from dataclasses import asdict, is_dataclass
from typing import Any

from fastapi import APIRouter, Request

from ..core.errors import APIError
from ..models.contracts import (
    AssistantIntent,
    RealtimeSessionResponse,
    RealtimeToolRouteRequest,
    RealtimeToolRouteResponse,
    RealtimeToolBookingRequest,
    RealtimeToolBookingResponse,
    RealtimeToolPurchaseVignetteRequest,
    RealtimeToolPurchaseVignetteResponse,
    RealtimeToolReturnToMainRouteRequest,
    RealtimeToolReturnToMainRouteResponse,
    RealtimeToolRerouteRequest,
    RealtimeToolRerouteResponse,
    RealtimeToolSearchRoutePoiRequest,
    RealtimeToolSearchRoutePoiResponse,
    RealtimeToolSearchStopAmenitiesRequest,
    RealtimeToolSearchStopAmenitiesResponse,
    RealtimeToolStartDrivingRequest,
    RealtimeToolStartDrivingResponse,
)


router = APIRouter(prefix="/api/assistant", tags=["assistant"])


def _active_context_id(route_service: object, name: str) -> str | None:
    public_value = getattr(route_service, name, None)
    if public_value is not None:
        return public_value
    return getattr(route_service, f"_{name}", None)


async def _call_service(
    request: Request,
    service_names: tuple[str, ...],
    method_name: str,
    **payload: Any,
) -> Any:
    for service_name in service_names:
        service = getattr(request.app.state, service_name, None)
        method = getattr(service, method_name, None)
        if method is not None:
            result = method(**payload)
            if isinstance(result, Awaitable):
                return await result
            return result

    raise APIError(
        503,
        f"{method_name.upper()}_UNAVAILABLE",
        f"The {method_name.replace('_', ' ')} service is not available yet.",
    )


def _validate_response(model: type[Any], result: Any) -> Any:
    if is_dataclass(result):
        result = asdict(result)
    if isinstance(result, dict) and "booking_id" in result and "status" not in result:
        result["status"] = "completed"
    if isinstance(result, dict):
        result = {
            field_name: result[field_name]
            for field_name in model.model_fields
            if field_name in result
        }
    return model.model_validate(result)


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
    return RealtimeToolRouteResponse(
        route=route,
        route_id=_active_context_id(request.app.state.route_service, "active_route_id"),
        search_id=_active_context_id(request.app.state.route_service, "active_search_id"),
    )


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


@router.post(
    "/realtime/tools/purchase-vignette",
    response_model=RealtimeToolPurchaseVignetteResponse,
)
async def realtime_purchase_vignette(
    payload: RealtimeToolPurchaseVignetteRequest,
    request: Request,
) -> RealtimeToolPurchaseVignetteResponse:
    result = await _call_service(
        request,
        ("commerce_service", "wallet_service", "route_service"),
        "purchase_vignette",
        **payload.model_dump(),
    )
    return _validate_response(RealtimeToolPurchaseVignetteResponse, result)


@router.post(
    "/realtime/tools/book-hotel-room",
    response_model=RealtimeToolBookingResponse,
)
async def realtime_book_hotel_room(
    payload: RealtimeToolBookingRequest,
    request: Request,
) -> RealtimeToolBookingResponse:
    if payload.booking_type != "hotel_room":
        raise APIError(422, "VALIDATION_ERROR", "The booking type must be hotel_room.")
    result = await _call_service(
        request,
        ("booking_service", "commerce_service", "route_service"),
        "book_hotel_room",
        **payload.model_dump(),
    )
    return _validate_response(RealtimeToolBookingResponse, result)


@router.post(
    "/realtime/tools/book-restaurant-table",
    response_model=RealtimeToolBookingResponse,
)
async def realtime_book_restaurant_table(
    payload: RealtimeToolBookingRequest,
    request: Request,
) -> RealtimeToolBookingResponse:
    if payload.booking_type != "restaurant_table":
        raise APIError(
            422,
            "VALIDATION_ERROR",
            "The booking type must be restaurant_table.",
        )
    result = await _call_service(
        request,
        ("booking_service", "commerce_service", "route_service"),
        "book_restaurant_table",
        **payload.model_dump(),
    )
    return _validate_response(RealtimeToolBookingResponse, result)


@router.post(
    "/realtime/tools/start-driving",
    response_model=RealtimeToolStartDrivingResponse,
)
async def realtime_start_driving(
    payload: RealtimeToolStartDrivingRequest,
    request: Request,
) -> RealtimeToolStartDrivingResponse:
    result = await _call_service(
        request,
        ("route_service", "navigation_service"),
        "start_driving",
        **payload.model_dump(),
    )
    return _validate_response(RealtimeToolStartDrivingResponse, result)


@router.post(
    "/realtime/tools/return-to-main-route",
    response_model=RealtimeToolReturnToMainRouteResponse,
)
async def realtime_return_to_main_route(
    payload: RealtimeToolReturnToMainRouteRequest,
    request: Request,
) -> RealtimeToolReturnToMainRouteResponse:
    result = await _call_service(
        request,
        ("route_service", "navigation_service"),
        "return_to_main_route",
        **payload.model_dump(),
    )
    return _validate_response(RealtimeToolReturnToMainRouteResponse, result)