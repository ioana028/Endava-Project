from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from ...models.contracts import RouteAlert


@dataclass(frozen=True, slots=True)
class WeatherPoint:
    location_name: str
    condition: str
    temperature_c: float | None = None
    severity: str = "INFO"
    timestamp: str | None = None
    alert_message: str | None = None


@dataclass(frozen=True, slots=True)
class WeatherSnapshot:
    points: tuple[WeatherPoint, ...]
    alerts: tuple[RouteAlert, ...] = ()


class OfflineWeatherProvider:
    """Deterministic offline weather fixture for local route planning."""

    async def get_route_weather(self, *, route_points: tuple[tuple[float, float], ...] | None = None, location: str | None = None) -> WeatherSnapshot:
        points: list[WeatherPoint] = []
        if route_points:
            for index, _ in enumerate(route_points[:5], start=1):
                points.append(
                    WeatherPoint(
                        location_name=(location or f"Route segment {index}"),
                        condition="Partly cloudy" if index % 2 else "Rain showers",
                        temperature_c=16.0 + index,
                        severity="INFO" if index % 2 else "WARNING",
                        timestamp=datetime.now(UTC).isoformat(timespec="minutes"),
                    )
                )
        else:
            points = [
                WeatherPoint(
                    location_name=location or "Route corridor",
                    condition="Clear",
                    temperature_c=18.0,
                    severity="INFO",
                    timestamp=datetime.now(UTC).isoformat(timespec="minutes"),
                )
            ]

        alerts: list[RouteAlert] = []
        for point in points:
            if point.severity in {"WARNING", "CRITICAL"}:
                alerts.append(
                    RouteAlert(
                        type="WEATHER",
                        location_name=point.location_name,
                        severity=point.severity,
                        message=(point.alert_message or f"Weather advisory: {point.condition} at {point.location_name}."),
                    )
                )
        return WeatherSnapshot(points=tuple(points), alerts=tuple(alerts))


def normalize_weather_result(payload: dict[str, Any] | None) -> WeatherSnapshot:
    if not isinstance(payload, dict):
        return OfflineWeatherProvider().get_route_weather()

    points = payload.get("points") or []
    normalized_points = []
    for point in points:
        if not isinstance(point, dict):
            continue
        normalized_points.append(
            WeatherPoint(
                location_name=str(point.get("locationName") or point.get("location_name") or "Route corridor"),
                condition=str(point.get("condition") or "Clear"),
                temperature_c=float(point["temperatureC"]) if point.get("temperatureC") is not None else None,
                severity=str(point.get("severity") or "INFO").upper(),
                timestamp=str(point.get("timestamp") or datetime.now(UTC).isoformat(timespec="minutes")),
                alert_message=str(point.get("alertMessage") or point.get("alert_message")) if point.get("alertMessage") or point.get("alert_message") else None,
            )
        )
    if not normalized_points:
        normalized_points = [
            WeatherPoint(
                location_name=str(payload.get("locationName") or payload.get("location_name") or "Route corridor"),
                condition=str(payload.get("condition") or "Clear"),
                temperature_c=float(payload["temperatureC"]) if payload.get("temperatureC") is not None else None,
                severity=str(payload.get("severity") or "INFO").upper(),
                timestamp=str(payload.get("timestamp") or datetime.now(UTC).isoformat(timespec="minutes")),
                alert_message=str(payload.get("alertMessage") or payload.get("alert_message")) if payload.get("alertMessage") or payload.get("alert_message") else None,
            )
        ]

    alerts = tuple(
        RouteAlert(
            type="WEATHER",
            location_name=point.location_name,
            severity=point.severity,
            message=(point.alert_message or f"Weather advisory: {point.condition} at {point.location_name}."),
        )
        for point in normalized_points
        if point.severity in {"WARNING", "CRITICAL"}
    )
    return WeatherSnapshot(points=tuple(normalized_points), alerts=alerts)
