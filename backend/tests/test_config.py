import pytest

from app.core.config import ConfigurationError, Settings, load_settings

VALID = {
    "database_url": "postgresql+psycopg://postgres:pw@db.example.com:5432/postgres",
    "supabase_url": "https://abcdefgh.supabase.co",
}


def test_valid_settings_derive_supabase_urls():
    settings = Settings(_env_file=None, **VALID)
    assert settings.supabase_issuer == "https://abcdefgh.supabase.co/auth/v1"
    assert settings.supabase_jwks_url == "https://abcdefgh.supabase.co/auth/v1/.well-known/jwks.json"
    assert settings.supabase_jwt_audience == "authenticated"


def test_missing_required_values_are_reported_by_variable_name():
    with pytest.raises(ConfigurationError) as error:
        load_settings(_env_file=None)
    assert "DATABASE_URL" in str(error.value)
    assert "SUPABASE_URL" in str(error.value)


@pytest.mark.parametrize(
    ("override", "expected"),
    [
        ({"database_url": "postgresql+psycopg://USER:PASSWORD@HOST:PORT/DATABASE"}, "DATABASE_URL"),
        ({"database_url": "mysql://postgres:pw@host/db"}, "postgresql://"),
        ({"supabase_url": "https://YOUR_PROJECT.supabase.co"}, "SUPABASE_URL"),
        ({"supabase_url": "http://example.com"}, "https://"),
        ({"supabase_url": "https://abcdefgh.supabase.co/"}, "must not end"),
        ({"api_prefix": "api/v1"}, "API_PREFIX"),
        ({"api_prefix": "/api/v1/"}, "API_PREFIX"),
        ({"frontend_url": "localhost:5173"}, "FRONTEND_URL"),
    ],
)
def test_invalid_values_are_rejected(override, expected):
    with pytest.raises(ConfigurationError) as error:
        load_settings(_env_file=None, **{**VALID, **override})
    assert expected in str(error.value)


def test_dashboard_uri_is_accepted_and_uses_the_psycopg_driver():
    settings = load_settings(
        _env_file=None,
        **{**VALID, "database_url": "postgresql://postgres.ref:pw@aws-0-region.pooler.supabase.com:5432/postgres"},
    )
    assert settings.database_url.startswith("postgresql+psycopg://")


def test_error_messages_never_contain_secret_values():
    secret = "s3cr3t-password-value"
    with pytest.raises(ConfigurationError) as error:
        load_settings(_env_file=None, **{**VALID, "database_url": f"mysql://postgres:{secret}@host/db"})
    assert secret not in str(error.value)
