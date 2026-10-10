import base64
import hashlib
import hmac
import json
import uuid
from datetime import timedelta

import pytest
from cryptography.hazmat.primitives.asymmetric import ec

from app.core.exceptions import ServiceUnavailableError
from app.core.security import JwksKeyResolver

PROTECTED = "/api/v1/profile"


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _unsigned_none_token(sub: uuid.UUID) -> str:
    header = _b64(json.dumps({"alg": "none", "typ": "JWT"}).encode())
    payload = _b64(json.dumps({"sub": str(sub), "aud": "authenticated", "role": "authenticated", "exp": 4102444800}).encode())
    return f"{header}.{payload}."


def _hs256_token_signed_with_public_key(sub: uuid.UUID, signing_key, issuer: str) -> str:
    """Classic algorithm-confusion attempt: HMAC-sign using the public key bytes."""
    from cryptography.hazmat.primitives import serialization

    secret = signing_key.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    header = _b64(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    payload = _b64(
        json.dumps(
            {"sub": str(sub), "aud": "authenticated", "iss": issuer, "role": "authenticated", "exp": 4102444800}
        ).encode()
    )
    signature = hmac.new(secret, f"{header}.{payload}".encode(), hashlib.sha256).digest()
    return f"{header}.{payload}.{_b64(signature)}"


async def test_missing_authorization_header_is_rejected(client):
    response = await client.get(PROTECTED)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "authentication_required"
    assert response.headers["www-authenticate"] == "Bearer"


async def test_non_bearer_scheme_is_rejected(client):
    response = await client.get(PROTECTED, headers={"Authorization": "Basic dXNlcjpwdw=="})
    assert response.status_code == 401


async def test_garbage_token_is_rejected(client):
    response = await client.get(PROTECTED, headers={"Authorization": "Bearer not-a-jwt"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_token"


async def test_expired_token_is_rejected(client, make_token):
    token = make_token(expires_in=timedelta(hours=-1))
    response = await client.get(PROTECTED, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "token_expired"


@pytest.mark.parametrize(
    "claims",
    [
        {"audience": "some-other-audience"},
        {"issuer": "https://attacker.example.com/auth/v1"},
        {"drop": ("exp",)},
        {"drop": ("sub",)},
        {"drop": ("aud",)},
        {"drop": ("iss",)},
        {"sub": "not-a-uuid"},
        {"role": "anon"},
    ],
)
async def test_tokens_with_bad_claims_are_rejected(client, make_token, claims):
    response = await client.get(PROTECTED, headers={"Authorization": f"Bearer {make_token(**claims)}"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_token"


async def test_token_signed_by_another_key_is_rejected(client, make_token):
    forged = make_token(key=ec.generate_private_key(ec.SECP256R1()))
    response = await client.get(PROTECTED, headers={"Authorization": f"Bearer {forged}"})
    assert response.status_code == 401


async def test_algorithm_none_token_is_rejected(client):
    response = await client.get(PROTECTED, headers={"Authorization": f"Bearer {_unsigned_none_token(uuid.uuid4())}"})
    assert response.status_code == 401


async def test_hs256_algorithm_confusion_is_rejected(client, signing_key, settings):
    token = _hs256_token_signed_with_public_key(uuid.uuid4(), signing_key, settings.supabase_issuer)
    response = await client.get(PROTECTED, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


def test_unreachable_jwks_endpoint_is_a_service_error_not_an_auth_failure():
    resolver = JwksKeyResolver("http://127.0.0.1:9/auth/v1/.well-known/jwks.json")
    with pytest.raises(ServiceUnavailableError):
        resolver("eyJhbGciOiJFUzI1NiIsImtpZCI6Im5vcGUifQ.e30.c2ln")
