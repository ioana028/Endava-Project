from backend.app.models.contracts import AssistantIntent, AssistantResponse


def test_day_one_response_has_no_route() -> None:
    response = AssistantResponse(
        transcript="Suzanne, take me to Budapest fast",
        intent=AssistantIntent(destination="Budapest", priority="FASTEST"),
        spoken_response="Calculating route based on your preferences, hold on",
    )

    assert response.route is None
    assert response.intent.destination == "Budapest"
    assert response.model_dump(by_alias=True)["spokenResponse"] == (
        "Calculating route based on your preferences, hold on"
    )
