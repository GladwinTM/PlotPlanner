"""Supabase access-token verification and the authentication dependency.

Supabase signs access tokens with an asymmetric key and publishes the public
keys at ``<project>/auth/v1/.well-known/jwks.json``. No shared secret is needed
and none must be shipped to this service. Only asymmetric algorithms are
accepted, which rules out algorithm-confusion attacks (e.g. HS256 signed with a
public key).

The authenticated identity is the token's ``sub`` claim (the Supabase Auth
UUID). Nothing in a request body or query string can change it.
"""
import logging
from collections.abc import Callable
from typing import Any
from uuid import UUID

import jwt
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient
from jwt.exceptions import PyJWKClientConnectionError, PyJWKClientError, PyJWTError
from pydantic import BaseModel, ConfigDict

from app.core.exceptions import AuthenticationError, ServiceUnavailableError

logger = logging.getLogger(__name__)

ALLOWED_ALGORITHMS = ["ES256", "RS256"]
CLOCK_SKEW_SECONDS = 10

KeyResolver = Callable[[str], Any]


class AuthenticatedUser(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: UUID
    email: str | None = None
    # Taken from user-editable metadata. Only suitable as a default display name,
    # never for any authorization decision.
    display_name_hint: str | None = None


class JwksKeyResolver:
    """Resolve the signing key for a token from the project's JWKS (cached)."""

    def __init__(self, jwks_url: str) -> None:
        self._client = PyJWKClient(jwks_url, cache_keys=True, lifespan=600, timeout=5)

    def __call__(self, token: str) -> Any:
        try:
            return self._client.get_signing_key_from_jwt(token).key
        except PyJWKClientConnectionError as exc:
            logger.error("could not fetch the Supabase JWKS: %s", type(exc).__name__)
            raise ServiceUnavailableError("Authentication service is unavailable") from exc
        except PyJWTError as exc:  # unknown kid, malformed header, unsupported key
            logger.info("token key lookup failed: %s", type(exc).__name__)
            raise AuthenticationError("Invalid access token", code="invalid_token") from exc


class TokenVerifier:
    def __init__(self, *, issuer: str, audience: str, key_resolver: KeyResolver) -> None:
        self._issuer = issuer
        self._audience = audience
        self._key_resolver = key_resolver

    def verify(self, token: str) -> AuthenticatedUser:
        key = self._key_resolver(token)
        try:
            claims = jwt.decode(
                token,
                key,
                algorithms=ALLOWED_ALGORITHMS,
                audience=self._audience,
                issuer=self._issuer,
                leeway=CLOCK_SKEW_SECONDS,
                options={"require": ["exp", "sub", "aud", "iss"]},
            )
        except jwt.ExpiredSignatureError as exc:
            raise AuthenticationError("Access token has expired", code="token_expired") from exc
        except PyJWTError as exc:
            logger.info("token rejected: %s", type(exc).__name__)
            raise AuthenticationError("Invalid access token", code="invalid_token") from exc

        if claims.get("role") != "authenticated":
            raise AuthenticationError("Invalid access token", code="invalid_token")
        try:
            user_id = UUID(str(claims["sub"]))
        except ValueError as exc:
            raise AuthenticationError("Invalid access token", code="invalid_token") from exc

        metadata = claims.get("user_metadata") or {}
        hint = metadata.get("full_name") or metadata.get("name") if isinstance(metadata, dict) else None
        email = claims.get("email")
        return AuthenticatedUser(
            id=user_id,
            email=email if isinstance(email, str) else None,
            display_name_hint=hint if isinstance(hint, str) else None,
        )


_bearer = HTTPBearer(auto_error=False)


def get_token_verifier(request: Request) -> TokenVerifier:
    return request.app.state.token_verifier


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    verifier: TokenVerifier = Depends(get_token_verifier),
) -> AuthenticatedUser:
    """Authenticate the request. Declared sync so FastAPI runs it in a worker
    thread (JWKS retrieval is blocking I/O)."""
    if credentials is None or credentials.scheme.lower() != "bearer" or not credentials.credentials:
        raise AuthenticationError()
    return verifier.verify(credentials.credentials)
