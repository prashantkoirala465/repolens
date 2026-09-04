import structlog
from fastapi import FastAPI
from fastapi.testclient import TestClient
from structlog.testing import capture_logs

from repolens.core.middleware import RequestContextMiddleware


def _make_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(RequestContextMiddleware)

    @app.get("/ping")
    async def ping() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/boom")
    async def boom() -> None:
        raise RuntimeError("kaboom")

    return app


def test_successful_request_gets_a_correlated_access_log() -> None:
    client = TestClient(_make_app())
    # capture_logs disables configured processors by default — merge_contextvars
    # has to be passed explicitly or the bound request_id/method/path never
    # make it into the captured event dict.
    with capture_logs(processors=[structlog.contextvars.merge_contextvars]) as logs:
        response = client.get("/ping")

    assert response.status_code == 200
    assert "X-Request-ID" in response.headers

    (event,) = [e for e in logs if e["event"] == "http.request"]
    assert event["status_code"] == 200
    assert event["method"] == "GET"
    assert event["path"] == "/ping"
    assert event["request_id"] == response.headers["X-Request-ID"]
    assert "duration_ms" in event


def test_incoming_request_id_header_is_honored() -> None:
    client = TestClient(_make_app())

    response = client.get("/ping", headers={"X-Request-ID": "abc-123"})

    assert response.headers["X-Request-ID"] == "abc-123"


def test_a_fresh_request_id_is_generated_when_none_is_supplied() -> None:
    client = TestClient(_make_app())

    first = client.get("/ping").headers["X-Request-ID"]
    second = client.get("/ping").headers["X-Request-ID"]

    assert first != second


def test_unhandled_exception_still_logs_a_correlated_event() -> None:
    client = TestClient(_make_app(), raise_server_exceptions=False)
    with capture_logs(processors=[structlog.contextvars.merge_contextvars]) as logs:
        response = client.get("/boom")

    assert response.status_code == 500
    (event,) = [e for e in logs if e["event"] == "http.request"]
    assert event["status_code"] == 500
    assert event["path"] == "/boom"
    assert event["log_level"] == "error"
