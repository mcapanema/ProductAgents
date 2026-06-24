from productagents.core.models.strategy import KeyResult, Objective


def test_objective_and_key_result_link():
    obj = Objective(title="Grow enterprise", period="2026-H2")
    kr = KeyResult(
        description="Close 10 enterprise deals",
        objective_id=obj.id,
        target=10.0,
        current=3.0,
        unit="deals",
    )
    assert kr.objective_id == obj.id
    assert kr.target == 10.0
    assert KeyResult.model_validate_json(kr.model_dump_json()) == kr
