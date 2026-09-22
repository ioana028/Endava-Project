from backend.app.core.route_country_rules import detect_border_crossings, derive_route_requirements, load_route_country_rules


def test_country_aliases_cover_european_vignette_corridors() -> None:
    rules = load_route_country_rules()

    assert "Czechia" in rules["country_aliases"]
    assert "Slovakia" in rules["country_aliases"]
    assert "Slovenia" in rules["country_aliases"]
    assert any(alias in rules["country_aliases"].get("Slovakia", []) for alias in ("SK", "Bratislava"))
    assert any(alias in rules["country_aliases"].get("Slovenia", []) for alias in ("SI", "Ljubljana"))


def test_detect_border_crossings_uses_aliases_not_broad_substring_matches() -> None:
    rules = load_route_country_rules()

    assert "Austria-Hungary" in detect_border_crossings("Vienna", "Budapest", rules)
    assert "Czechia-Slovakia" in detect_border_crossings("Prague", "Bratislava", rules)
    assert "Slovakia-Slovenia" in detect_border_crossings("Bratislava", "Ljubljana", rules)
    assert detect_border_crossings("Austrian route", "Budapest", rules) == []


def test_derive_route_requirements_returns_expected_vignette_facts() -> None:
    rules = load_route_country_rules()

    requirements = derive_route_requirements(["Austria-Hungary", "Czechia-Slovakia"], rules)
    assert "Hungarian motorway vignette" in requirements
    assert "Slovak motorway vignette" in requirements
