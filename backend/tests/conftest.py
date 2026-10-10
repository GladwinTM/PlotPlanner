"""Test harness.

Tests run against a disposable local PostgreSQL (see scripts/test_db.sh) that
imitates the parts of Supabase the app depends on: the ``auth`` schema, the
``anon``/``authenticated`` roles and ``auth.uid()``. The real migrations are
applied to it, so the schema and RLS policies under test are the shipped ones.

Safety: the database is dropped and rebuilt, so the harness refuses any target
that is not a local database whose name ends in ``_test``.
"""
import os
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse

import httpx
import jwt
import pytest
import pytest_asyncio
from alembic import command
from alembic.config import Config
from cryptography.hazmat.primitives.asymmetric import ec
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, text

from app.core.config import Settings
from app.core.security import TokenVerifier
from app.db.database import create_engine as create_app_engine
from app.factory import create_app
from app.integrations.jobs import JobSearchClient
from app.integrations.web import UrlVerifier
from app.integrations.youtube import YouTubeClient
from tests.fakes import FakeLLM, JobsMock, WebMock, YouTubeMock

BACKEND_DIR = Path(__file__).resolve().parents[1]
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+psycopg://plotplanner@127.0.0.1:54329/plotplanner_test"
)
SUPABASE_URL = "https://test-project.supabase.co"
ISSUER = f"{SUPABASE_URL}/auth/v1"

# Imitates what Supabase provides before any application migration runs.
SUPABASE_STUB_STATEMENTS = [
    "drop schema if exists public cascade",
    "drop schema if exists app_private cascade",
    "drop schema if exists auth cascade",
    "create schema public",
    "create schema auth",
    """do $$ begin
         if not exists (select from pg_roles where rolname = 'anon') then create role anon nologin; end if;
         if not exists (select from pg_roles where rolname = 'authenticated') then create role authenticated nologin; end if;
       end $$""",
    "grant usage on schema public, auth to anon, authenticated",
    "create table auth.users (id uuid primary key default gen_random_uuid(), email text)",
    """create function auth.uid() returns uuid language sql stable as $$
         select nullif(coalesce(
           current_setting('request.jwt.claim.sub', true),
           (nullif(current_setting('request.jwt.claims', true), '')::jsonb ->> 'sub')
         ), '')::uuid
       $$""",
    # Supabase grants new public tables to the API roles by default.
    "alter default privileges in schema public grant all on tables to anon, authenticated",
]


def _guard_test_database(url: str) -> None:
    parsed = urlparse(url.replace("+psycopg", ""))
    database = (parsed.path or "").lstrip("/")
    if parsed.hostname not in {"localhost", "127.0.0.1"} or not database.endswith("_test"):
        pytest.exit("Refusing to run tests: TEST_DATABASE_URL must be a local database named *_test", returncode=2)


def alembic_config(url: str = TEST_DATABASE_URL) -> Config:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    config.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    return config


@pytest.fixture(scope="session")
def db_engine():
    _guard_test_database(TEST_DATABASE_URL)
    engine = create_engine(TEST_DATABASE_URL, isolation_level="AUTOCOMMIT")
    try:
        with engine.connect() as connection:
            connection.execute(text("select 1"))
    except Exception:
        pytest.exit("Test database unreachable. Start it with: backend/scripts/test_db.sh start", returncode=2)
    with engine.connect() as connection:
        for statement in SUPABASE_STUB_STATEMENTS:
            connection.execute(text(statement))
    command.upgrade(alembic_config(), "head")
    yield engine
    engine.dispose()


@pytest.fixture
def clean_tables(db_engine):
    with db_engine.connect() as connection:
        connection.execute(text("truncate auth.users cascade"))
    yield


@pytest.fixture
def db(db_engine, clean_tables):
    with db_engine.connect() as connection:
        yield connection


@pytest.fixture(scope="session")
def signing_key():
    return ec.generate_private_key(ec.SECP256R1())


@pytest.fixture
def settings() -> Settings:
    return Settings(
        _env_file=None,
        app_env="test",
        database_url=TEST_DATABASE_URL,
        supabase_url=SUPABASE_URL,
        frontend_url="http://localhost:5173",
    )


@pytest.fixture
def token_verifier(settings, signing_key) -> TokenVerifier:
    public_key = signing_key.public_key()
    return TokenVerifier(
        issuer=settings.supabase_issuer,
        audience=settings.supabase_jwt_audience,
        key_resolver=lambda _token: public_key,
    )


@pytest.fixture
def fake_llm():
    return FakeLLM()


@pytest.fixture
def youtube_mock():
    return YouTubeMock()


@pytest.fixture
def jobs_mock():
    return JobsMock()


@pytest.fixture
def web_mock():
    return WebMock()


@pytest_asyncio.fixture
async def app(settings, token_verifier, db_engine, clean_tables, fake_llm, youtube_mock, jobs_mock, web_mock):
    engine = create_app_engine(settings, null_pool=True)
    application = create_app(
        settings,
        token_verifier=token_verifier,
        engine=engine,
        llm=fake_llm,
        youtube=YouTubeClient("test-youtube-key", transport=httpx.MockTransport(youtube_mock)),
        jobs=JobSearchClient(transport=httpx.MockTransport(jobs_mock)),
        url_verifier=UrlVerifier(transport=httpx.MockTransport(web_mock), resolve_hosts=False),
    )
    yield application
    await engine.dispose()


@pytest_asyncio.fixture
async def client(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http_client:
        yield http_client


@pytest.fixture
def make_token(signing_key):
    def build(
        sub: uuid.UUID | str | None = None,
        *,
        key=None,
        algorithm: str = "ES256",
        audience: str = "authenticated",
        issuer: str = ISSUER,
        expires_in: timedelta = timedelta(hours=1),
        drop: tuple[str, ...] = (),
        **claims,
    ) -> str:
        now = datetime.now(UTC)
        payload = {
            "sub": str(sub or uuid.uuid4()),
            "aud": audience,
            "iss": issuer,
            "role": "authenticated",
            "iat": now,
            "exp": now + expires_in,
            **claims,
        }
        for name in drop:
            payload.pop(name, None)
        return jwt.encode(payload, key or signing_key, algorithm=algorithm, headers={"kid": "test-key"})

    return build


@pytest.fixture
def create_user(db_engine, clean_tables):
    def build(email: str | None = None) -> uuid.UUID:
        user_id = uuid.uuid4()
        with db_engine.connect() as connection:
            connection.execute(
                text("insert into auth.users (id, email) values (:id, :email)"),
                {"id": user_id, "email": email},
            )
        return user_id

    return build


@pytest.fixture
def auth_headers(make_token):
    def build(user_id: uuid.UUID, **claims) -> dict[str, str]:
        return {"Authorization": f"Bearer {make_token(user_id, **claims)}"}

    return build


@pytest.fixture
def signed_in(create_user, auth_headers):
    """Create an auth user and return (user_id, headers)."""

    def build(email: str = "user@example.com"):
        user_id = create_user(email)
        return user_id, auth_headers(user_id, email=email)

    return build
