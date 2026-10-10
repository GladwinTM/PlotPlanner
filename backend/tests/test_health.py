from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.db.database import create_engine
from app.factory import create_app


async def test_health_does_not_need_auth_or_database(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_ready_reports_database_ok(client):
    response = await client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready", "checks": {"database": "ok"}}


async def test_ready_fails_with_503_and_leaks_nothing_when_database_is_down(token_verifier):
    unreachable = Settings(
        _env_file=None,
        database_url="postgresql+psycopg://leakme_user:leakme_pw@127.0.0.1:9/leakme_db",
        supabase_url="https://test-project.supabase.co",
    )
    engine = create_engine(unreachable, null_pool=True)
    application = create_app(unreachable, token_verifier=token_verifier, engine=engine)
    async with AsyncClient(transport=ASGITransport(app=application), base_url="http://test") as client:
        response = await client.get("/ready")
    await engine.dispose()

    assert response.status_code == 503
    assert response.json() == {"status": "unavailable", "checks": {"database": "failed"}}
    for leaked in ("leakme", "127.0.0.1", "psycopg"):
        assert leaked not in response.text


async def test_database_outage_on_a_protected_route_is_a_503_not_a_500(token_verifier, make_token):
    unreachable = Settings(
        _env_file=None,
        database_url="postgresql+psycopg://leakme_user:leakme_pw@127.0.0.1:9/leakme_db",
        supabase_url="https://test-project.supabase.co",
    )
    engine = create_engine(unreachable, null_pool=True)
    application = create_app(unreachable, token_verifier=token_verifier, engine=engine)
    async with AsyncClient(transport=ASGITransport(app=application), base_url="http://test") as client:
        response = await client.get("/api/v1/profile", headers={"Authorization": f"Bearer {make_token()}"})
    await engine.dispose()

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "database_unavailable"
    assert "leakme" not in response.text


async def test_unknown_route_uses_the_error_envelope(client):
    response = await client.get("/nope")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "http_error"


async def test_cors_allows_only_the_configured_frontend_origin(client):
    allowed = await client.options(
        "/api/v1/profile",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization",
        },
    )
    denied = await client.options(
        "/api/v1/profile",
        headers={"Origin": "https://evil.example.com", "Access-Control-Request-Method": "GET"},
    )
    assert allowed.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert "access-control-allow-origin" not in denied.headers
