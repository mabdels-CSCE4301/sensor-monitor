"""Integration tests for `/api/calc` on both server implementations."""

import pytest
from fastapi.testclient import TestClient

import calculator
from app import app as flask_app

FLASK_CLIENT = flask_app.test_client()
FASTAPI_CLIENT = TestClient(calculator.app)

CLIENTS = [
    pytest.param(FLASK_CLIENT, id="flask"),
    pytest.param(FASTAPI_CLIENT, id="fastapi"),
]


def _json(response):
    getter = getattr(response, "get_json", None)
    return getter() if getter is not None else response.json()


def _get(client, params):
    """Flask's test client uses `query_string`; httpx uses `params`."""
    if client is FLASK_CLIENT:
        return client.get("/api/calc", query_string=params)
    return client.get("/api/calc", params=params)


@pytest.mark.parametrize("client", CLIENTS)
@pytest.mark.parametrize(
    "expression, display",
    [("2+3*4", "14"), ("(2+3)*4", "20"), ("-5+2", "-3")],
)
def test_expression_mode_returns_value_display_and_metadata(client, expression, display):
    response = _get(client,{"expression": expression})

    assert response.status_code == 200
    data = _json(response)
    assert data["success"] is True
    assert data["result"] == float(display)
    assert data["display"] == display
    assert data["expression"] == expression
    assert data["angle_mode"] == "DEG"
    assert data["is_trigonometric"] is False


@pytest.mark.parametrize("client", CLIENTS)
@pytest.mark.parametrize("operator", ["multiply", "x", "*"])
def test_abop_path_keeps_existing_aliases(client, operator):
    response = _get(client,{"a": 7, "b": 8, "op": operator})

    assert response.status_code == 200
    data = _json(response)
    assert data["result"] == 56
    assert data["display"] == "56"
    assert data["a"] == 7
    assert data["b"] == 8
    assert data["op"] == operator
    assert data["angle_mode"] == "DEG"
    assert data["is_trigonometric"] is False


@pytest.mark.parametrize("client", CLIENTS)
def test_operator_keyword_alias_is_accepted(client):
    response = _get(client,{"a": 7, "b": 8, "operator": "add"})

    assert response.status_code == 200
    assert _json(response)["display"] == "15"


@pytest.mark.parametrize("client", CLIENTS)
def test_post_json_body_is_supported(client):
    response = client.post("/api/calc", json={"expression": "sqrt(16)"})

    assert response.status_code == 200
    data = _json(response)
    assert data["display"] == "4"
    assert data["is_trigonometric"] is False


@pytest.mark.parametrize("client", CLIENTS)
def test_default_angle_mode_is_degrees(client):
    response = _get(client,{"expression": "sin(30)"})

    data = _json(response)
    assert data["display"] == "0.5"
    assert data["angle_mode"] == "DEG"
    assert data["is_trigonometric"] is True


@pytest.mark.parametrize("client", CLIENTS)
def test_angle_mode_is_honored_and_echoed(client):
    response = _get(
        client, {"expression": "sin(pi/2)", "angle_mode": "RAD"}
    )

    assert response.status_code == 200
    data = _json(response)
    assert data["display"] == "1"
    assert data["angle_mode"] == "RAD"
    assert data["is_trigonometric"] is True


@pytest.mark.parametrize("client", CLIENTS)
def test_non_trig_evaluation_is_flagged_false(client):
    response = _get(client,{"expression": "2+2"})

    assert _json(response)["is_trigonometric"] is False


@pytest.mark.parametrize("client", CLIENTS)
@pytest.mark.parametrize(
    "expression", ["5/0", "2+", "(2+3", "sqrt(-1)", "2pi", "2^100000"]
)
def test_errors_are_controlled_400s(client, expression):
    response = _get(client,{"expression": expression})

    assert response.status_code == 400
    data = _json(response)
    assert isinstance(data.get("detail"), str) and data["detail"]
    # Flask keeps its success field; FastAPI's HTTPException body does not.
    assert data.get("success") is not True


@pytest.mark.parametrize("client", CLIENTS)
def test_invalid_angle_mode_is_a_400(client):
    response = _get(
        client, {"expression": "sin(30)", "angle_mode": "grad"}
    )

    assert response.status_code == 400


@pytest.mark.parametrize("client", CLIENTS)
def test_missing_parameters_are_a_400(client):
    response = client.get("/api/calc")

    assert response.status_code == 400
    assert _json(response).get("detail")


@pytest.mark.parametrize("client", CLIENTS)
def test_invalid_numeric_value_is_a_400(client):
    response = _get(client,{"a": "abc", "b": 2, "op": "add"})

    assert response.status_code == 400


def test_both_servers_agree_on_display_strings():
    expressions = [
        "2+3*4",
        "1/3",
        "sqrt(2)",
        "ln(e)",
        "sin(30)",
        "cos(60)",
        "atan(1)",
        "pi",
    ]

    for expression in expressions:
        flask_data = _json(_get(FLASK_CLIENT, {"expression": expression}))
        fastapi_data = _json(_get(FASTAPI_CLIENT, {"expression": expression}))
        assert flask_data["display"] == fastapi_data["display"], expression
        assert flask_data["result"] == fastapi_data["result"], expression
