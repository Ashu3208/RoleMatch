from functools import lru_cache
from json import JSONDecodeError
import os
from typing import Annotated, Any

from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt

load_dotenv()


class TokenVerificationUnavailableError(RuntimeError):
    """Signing keys could not be retrieved or processed; verification cannot proceed."""

@lru_cache(maxsize=1)
def _get_jwks_client(issuer: str) -> jwt.PyJWKClient:
    return jwt.PyJWKClient(
        f"{issuer}/.well-known/jwks.json",
        cache_jwk_set=True,
        lifespan=300,
        timeout=5,
    )


def verify_access_token(token: str) -> dict[str, Any] | None:
    supabase_url = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
    if not supabase_url:
        raise ValueError("Missing SUPABASE_URL")

    issuer = f"{supabase_url}/auth/v1"
    try:
        header = jwt.get_unverified_header(token)
        if header.get("alg") != "ES256":
            return None
        if not isinstance(header.get("kid"), str) or not header["kid"].strip():
            return None

        signing_key = _get_jwks_client(issuer).get_signing_key_from_jwt(token)
        if signing_key.algorithm_name != "ES256":
            return None

        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256"],
            issuer=issuer,
            audience="authenticated",
            options={"require": ["exp", "iss", "aud", "sub"]},
        )
        if not payload["sub"].strip():
            return None
        return payload
    except (jwt.PyJWKClientConnectionError, jwt.PyJWKSetError, jwt.PyJWKError, JSONDecodeError) as error:
        raise TokenVerificationUnavailableError("Unable to load Supabase signing keys") from error
    except (jwt.InvalidTokenError, jwt.PyJWKClientError):
        return None

bearer = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> dict[str, Any]:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Missing or invalid bearer token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized

    try:
        payload = verify_access_token(credentials.credentials)
    except TokenVerificationUnavailableError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service temporarily unavailable",
        ) from error

    if payload is None:
        raise unauthorized
    return payload
    
