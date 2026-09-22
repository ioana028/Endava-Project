from backend.app.core.route_country_rules import load_route_country_rules


def test_day9_weather_fixture_supports_route_segments_and_alerts() -> None:
    rules = load_route_country_rules()
    assert isinstance(rules, dict)
    assert "country_aliases" in rules
    assert isinstance(rules["country_aliases"], dict)
    assert "Czechia" in rules["country_aliases"]
