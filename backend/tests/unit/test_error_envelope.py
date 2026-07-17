from fastapi.testclient import TestClient


def test_request_validation_uses_stable_error_envelope(client: TestClient) -> None:
    response = client.post("/api/v1/auth/register", json={})

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert body["error"]["message"] == "Request validation failed"
    assert body["error"]["details"]["errors"]
    assert body["error"]["correlation_id"]


def test_path_validation_uses_same_error_envelope(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "not-an-email", "password": "short"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_framework_404_uses_same_error_envelope(client: TestClient) -> None:
    response = client.get("/api/v1/does-not-exist")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_every_openapi_operation_documents_standard_error_envelope(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()

    for path_item in schema["paths"].values():
        for method, operation in path_item.items():
            if method not in {"get", "post", "put", "patch", "delete", "options", "head"}:
                continue
            for status_code in ("401", "403", "404", "409", "422", "429"):
                response = operation["responses"][status_code]
                assert response["content"]["application/json"]["schema"] == {
                    "$ref": "#/components/schemas/ErrorEnvelope"
                }
