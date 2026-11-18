from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "schemas"


def _validator(name: str) -> Draft202012Validator:
    observation = json.loads((SCHEMAS / "observation.v1.schema.json").read_text())
    action = json.loads((SCHEMAS / "action.v1.schema.json").read_text())
    registry = Registry().with_resource(
        "urn:royalebench:observation:v1", Resource.from_contents(observation)
    ).with_resource("urn:royalebench:action:v1", Resource.from_contents(action))
    schema = json.loads((SCHEMAS / name).read_text())
    return Draft202012Validator(schema, registry=registry)


def _observation() -> dict:
    return {
        "schema": "royalebench.observation.v1",
        "match_id": "forecast-test",
        "decision_id": 3,
        "seat": 0,
        "game": {},
        "own": {},
        "opponent": {},
        "entities": [],
        "legal_actions": {},
        "engine": {},
    }


def test_forecast_request_and_response_schemas_validate():
    observation = _observation()
    action = {"schema": "royalebench.action.v1", "type": "wait"}
    request = {
        "schema": "royalebench.forecast-request.v1",
        "request_id": "forecast-1",
        "observation_hash": "a" * 64,
        "horizon_ticks": 5,
        "observation": observation,
        "actions": [action],
    }
    response = {
        "schema": "royalebench.forecast-response.v1",
        "request_id": "forecast-1",
        "observation_hash": "a" * 64,
        "horizon_ticks": 5,
        "predicted_observation": observation,
    }
    _validator("forecast-request.v1.schema.json").validate(request)
    _validator("forecast-response.v1.schema.json").validate(response)


def test_forecast_schemas_reject_mismatched_or_missing_contract_fields():
    request = {
        "schema": "royalebench.forecast-request.v1",
        "request_id": "forecast-1",
        "observation_hash": "not-a-hash",
        "horizon_ticks": 0,
        "observation": _observation(),
        "actions": [{"schema": "royalebench.action.v1", "type": "wait"}],
    }
    errors = list(_validator("forecast-request.v1.schema.json").iter_errors(request))
    assert len(errors) >= 2

    response = {
        "schema": "royalebench.forecast-response.v1",
        "request_id": "forecast-1",
        "observation_hash": "a" * 64,
        "horizon_ticks": 5,
        "predicted_observation": _observation(),
        "unversioned_extra_field": True,
    }
    assert list(_validator("forecast-response.v1.schema.json").iter_errors(response))
