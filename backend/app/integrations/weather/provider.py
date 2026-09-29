from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import httpx

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


def summarize_route_weather(snapshot: WeatherSnapshot) -> RouteAlert | None:
    if not snapshot.points:
        return None

    temperatures = [
        point.temperature_c
        for point in snapshot.points
        if point.temperature_c is not None
    ]
    condition_counts: dict[str, int] = {}
    for point in snapshot.points:
        condition_counts[point.condition] = condition_counts.get(point.condition, 0) + 1
    condition = (
        next(iter(condition_counts))
        if len(condition_counts) == 1
        else "Mixed conditions"
    )
    temperature_text = (
        f"average temperature about {round(sum(temperatures) / len(temperatures))}°C"
        if temperatures
        else "average temperature unavailable"
    )
    return RouteAlert(
        type="WEATHER",
        location_name="Route average",
        severity="INFO",
        message=(
            f"Current route conditions: {condition}; {temperature_text} across "
            f"{len(snapshot.points)} sampled points."
        ),
    )


def summarize_route_weather_advisories(snapshot: WeatherSnapshot) -> RouteAlert | None:
    counts: dict[tuple[str, str], int] = {}
    for point in snapshot.points:
        if point.severity not in {"WARNING", "CRITICAL"}:
            continue
        key = (point.severity, point.condition)
        counts[key] = counts.get(key, 0) + 1
    if not counts:
        return None

    severity_order = {"CRITICAL": 0, "WARNING": 1}
    messages = []
    for (severity, condition), count in sorted(
        counts.items(), key=lambda item: (severity_order[item[0][0]], item[0][1])
    ):
        point_label = "sampled point" if count == 1 else "sampled points"
        messages.append(f"{severity.title()}: {condition} at {count} {point_label}")

    return RouteAlert(
        type="WEATHER",
        location_name="Weather advisories",
        severity="CRITICAL" if any(key[0] == "CRITICAL" for key in counts) else "WARNING",
        message="; ".join(messages) + ".",
    )


def sample_route_points(
    route_points: tuple[tuple[float, float], ...] | None,
    limit: int = 5,
) -> tuple[tuple[float, float], ...]:
    points = tuple(route_points or ())
    if not points or limit <= 0:
        return ()
    if len(points) <= limit:
        return points
    if limit == 1:
        return (points[0],)
    indices = tuple(
        round(index * (len(points) - 1) / (limit - 1))
        for index in range(limit)
    )
    return tuple(points[index] for index in indices)


class OfflineWeatherProvider:
    """Deterministic offline weather fixture for local route planning."""

    async def get_route_weather(
        self,
        *,
        route_points: tuple[tuple[float, float], ...] | None = None,
        location: str | None = None,
    ) -> WeatherSnapshot:
        # Never present fabricated offline conditions as live route weather.
        return WeatherSnapshot(points=())


class OpenMeteoWeatherProvider:
    """Live route weather from Open-Meteo; no API key is required."""

    def __init__(self, timeout_seconds: float = 10.0) -> None:
        self._timeout_seconds = timeout_seconds

    async def get_route_weather(
        self,
        *,
        route_points: tuple[tuple[float, float], ...] | None = None,
        location: str | None = None,
    ) -> WeatherSnapshot:
        points = sample_route_points(route_points)
        if not points:
            return WeatherSnapshot(points=())

        try:
            async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                response = await client.get(
                    "https://api.open-meteo.com/v1/forecast",
                    params={
                        "latitude": ",".join(str(latitude) for _, latitude in points),
                        "longitude": ",".join(str(longitude) for longitude, _ in points),
                        "current": "temperature_2m,weather_code",
                        "timezone": "auto",
                    },
                )
                response.raise_for_status()
                payload = response.json()
        except (httpx.HTTPError, ValueError, TypeError):
            return WeatherSnapshot(points=())

        responses = payload if isinstance(payload, list) else [payload]
        weather_points = tuple(
            self._to_point(item, index)
            for index, item in enumerate(responses)
            if isinstance(item, dict)
        )
        return WeatherSnapshot(
            points=weather_points,
            alerts=tuple(
                RouteAlert(
                    type="WEATHER",
                    location_name=point.location_name,
                    severity=point.severity,
                    message=point.alert_message or point.condition,
                )
                for point in weather_points
            ),
        )

    @staticmethod
    def _to_point(payload: dict[str, Any], index: int) -> WeatherPoint:
        current = payload.get("current") or {}
        code = int(current.get("weather_code", 0))
        condition, severity = _open_meteo_condition(code)
        temperature = current.get("temperature_2m")
        return WeatherPoint(
            location_name=f"Route section {index + 1}",
            condition=condition,
            temperature_c=float(temperature) if temperature is not None else None,
            severity=severity,
            timestamp=str(current.get("time")) if current.get("time") else None,
            alert_message=(
                f"{condition}, {float(temperature):g}°C."
                if temperature is not None
                else condition
            ),
        )


def _open_meteo_condition(code: int) -> tuple[str, str]:
    if code in {95, 96, 99}:
        return "Thunderstorms", "CRITICAL"
    if code in {65, 67, 82}:
        return "Heavy rain", "WARNING"
    if code in {51, 53, 55, 56, 57, 61, 63, 66, 71, 73, 75, 77, 80, 81, 85, 86}:
        return "Precipitation", "WARNING"
    if code in {45, 48}:
        return "Fog", "WARNING"
    if code in {1, 2, 3}:
        return "Cloudy", "INFO"
    return "Clear", "INFO"


def normalize_weather_result(payload: dict[str, Any] | None) -> WeatherSnapshot:
    if not isinstance(payload, dict):
        return WeatherSnapshot(points=())

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
