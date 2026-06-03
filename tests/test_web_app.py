from __future__ import annotations

from fastapi.testclient import TestClient

from sensex_noise.auth.kite_auth import KiteSession
from sensex_noise.auth.token_store import TokenStore
from sensex_noise.web import routes_kite
from sensex_noise.web.app import app


def _seed_web_env(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("KITE_API_KEY", "test-api-key")
    monkeypatch.setenv("KITE_API_SECRET", "test-api-secret")
    monkeypatch.setenv("ADMIN_TOKEN", "admin-secret")
    monkeypatch.setenv("APP_BASE_URL", "http://127.0.0.1:8000")
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("ENABLE_SENSEX_OPTION_TAPE_RECORDER", "false")
    monkeypatch.setenv("SENSEX_TAPE_WRITE_LEGACY_OPTIONS_LOG", "true")
    monkeypatch.setenv("BACKGROUND_TICK_QUEUE_MAXSIZE", "20000")
    monkeypatch.setenv("JOURNAL_QUEUE_MAXSIZE", "50000")


def test_health_is_public(monkeypatch, tmp_path) -> None:
    _seed_web_env(monkeypatch, tmp_path)

    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_admin_status_requires_admin_token(monkeypatch, tmp_path) -> None:
    _seed_web_env(monkeypatch, tmp_path)
    client = TestClient(app)

    unauthorized = client.get("/admin/status")
    authorized = client.get("/admin/status", headers={"Authorization": "Bearer admin-secret"})

    assert unauthorized.status_code == 401
    assert authorized.status_code == 200
    payload = authorized.json()
    assert payload["token_store"]["has_today_token"] is False
    assert payload["token_store"]["metadata"] is None
    assert payload["paths"]["data_dir"] == str(tmp_path)
    assert "test-api-secret" not in str(payload)
    assert "admin-secret" not in str(payload)


def test_admin_status_returns_503_when_admin_token_missing(monkeypatch, tmp_path) -> None:
    _seed_web_env(monkeypatch, tmp_path)
    monkeypatch.setenv("ADMIN_TOKEN", "")

    response = TestClient(app).get("/admin/status")

    assert response.status_code == 503


def test_kite_login_redirect_sets_signed_state(monkeypatch, tmp_path) -> None:
    _seed_web_env(monkeypatch, tmp_path)
    monkeypatch.setattr(routes_kite, "build_login_url", lambda api_key: "https://kite.test/login?api_key=abc")

    response = TestClient(app).get("/kite/login", follow_redirects=False)

    assert response.status_code == 307
    assert "https://kite.test/login?api_key=abc&state=" in response.headers["location"]
    assert "kite_auth_state=" in response.headers["set-cookie"]


def test_kite_callback_stores_token_without_returning_secret(monkeypatch, tmp_path) -> None:
    _seed_web_env(monkeypatch, tmp_path)
    monkeypatch.setattr(routes_kite, "build_login_url", lambda api_key: "https://kite.test/login?api_key=abc")

    def fake_exchange_request_token(*, api_key: str, api_secret: str, request_token: str) -> KiteSession:
        assert api_key == "test-api-key"
        assert api_secret == "test-api-secret"
        assert request_token == "request-token-1"
        return KiteSession(access_token="stored-secret-token", user_id="USER123")

    monkeypatch.setattr(routes_kite, "exchange_request_token", fake_exchange_request_token)
    client = TestClient(app)
    login_response = client.get("/kite/login", follow_redirects=False)
    state = login_response.cookies["kite_auth_state"]

    response = client.get(f"/kite/callback?request_token=request-token-1&state={state}")

    assert response.status_code == 200
    assert "stored-secret-token" not in response.text
    payload = response.json()
    assert payload["token_store"]["metadata"]["user_id"] == "USER123"
    assert payload["token_store"]["metadata"]["has_access_token"] is True
    assert TokenStore(tmp_path / "runtime" / "kite_access_token.json").read_today().access_token == "stored-secret-token"


def test_kite_callback_rejects_missing_state(monkeypatch, tmp_path) -> None:
    _seed_web_env(monkeypatch, tmp_path)

    response = TestClient(app).get("/kite/callback?request_token=request-token-1")

    assert response.status_code == 400
