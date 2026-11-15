from io import BytesIO
import json
import os
from time import monotonic, time
import unittest
from unittest.mock import patch
from urllib.error import URLError

from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient
import jwt

from rolematch.auth import (
    TokenVerificationUnavailableError,
    _get_jwks_client,
    verify_access_token,
)
from rolematch.main import app


class AuthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.private_key = ec.generate_private_key(ec.SECP256R1())
        cls.next_private_key = ec.generate_private_key(ec.SECP256R1())

    def setUp(self):
        self.issuer = "https://example.supabase.co/auth/v1"
        self.claims = {
            "sub": "example-user-id",
            "email": "applicant@example.com",
            "iss": self.issuer,
            "aud": "authenticated",
            "iat": int(time()),
            "exp": int(time()) + 300,
        }
        self.jwks = {"keys": [self.public_jwk(self.private_key, "key-1")]}
        environment = patch.dict(os.environ, {"SUPABASE_URL": "https://example.supabase.co/"})
        environment.start()
        self.addCleanup(environment.stop)
        _get_jwks_client.cache_clear()
        self.addCleanup(_get_jwks_client.cache_clear)

        # Exercise real key selection, signature checking, and caching. Only
        # HTTP is mocked: no user credentials or Supabase requests are needed.
        opener = patch("jwt.jwks_client.urllib.request.build_opener")
        self.fetch = opener.start().return_value.open
        self.addCleanup(opener.stop)
        self.fetch.side_effect = lambda *args, **kwargs: BytesIO(json.dumps(self.jwks).encode())

    @staticmethod
    def public_jwk(private_key, kid):
        key = json.loads(jwt.algorithms.ECAlgorithm.to_jwk(private_key.public_key()))
        return {**key, "kid": kid, "alg": "ES256", "use": "sig"}

    def token(self, claims=None, *, key=None, kid="key-1", headers=None):
        return jwt.encode(
            self.claims if claims is None else claims,
            self.private_key if key is None else key,
            algorithm="ES256",
            headers={"kid": kid, **(headers or {})},
        )

    def test_accepts_valid_signed_token(self):
        self.assertEqual(verify_access_token(self.token()), self.claims)
        self.fetch.assert_called_once()
        self.assertEqual(self.fetch.call_args.args[0].full_url, f"{self.issuer}/.well-known/jwks.json")
        self.assertEqual(self.fetch.call_args.kwargs["timeout"], 5)

    def test_rejects_expired_token(self):
        claims = {**self.claims, "exp": int(time()) - 10}
        self.assertIsNone(verify_access_token(self.token(claims)))

    def test_rejects_forged_signature(self):
        forged = self.token(key=self.next_private_key)
        self.assertIsNone(verify_access_token(forged))

    def test_rejects_wrong_issuer_audience_or_subject(self):
        for field, value in [
            ("iss", "https://another-project.supabase.co/auth/v1"),
            ("aud", "another-service"),
            ("sub", 123),
            ("sub", ""),
            ("sub", "   "),
        ]:
            with self.subTest(field=field, value=value):
                self.assertIsNone(verify_access_token(self.token({**self.claims, field: value})))

    def test_rejects_missing_required_claims(self):
        for field in ["exp", "iss", "aud", "sub"]:
            with self.subTest(field=field):
                claims = {key: value for key, value in self.claims.items() if key != field}
                self.assertIsNone(verify_access_token(self.token(claims)))

    def test_rejects_future_issue_and_not_before_times(self):
        for field in ["iat", "nbf"]:
            with self.subTest(field=field):
                self.assertIsNone(verify_access_token(self.token({
                    **self.claims, field: int(time()) + 60,
                })))

    def test_rejects_malformed_and_unsupported_tokens_without_fetching_keys(self):
        unsigned = jwt.encode(self.claims, key=None, algorithm="none", headers={"kid": "key-1"})
        symmetric = jwt.encode(self.claims, key="x" * 64, algorithm="HS256", headers={"kid": "key-1"})
        for token in ["", "not-a-jwt", unsigned, symmetric, self.token(kid="")]:
            with self.subTest(token_type=token.split('.')[0]):
                self.assertIsNone(verify_access_token(token))
        self.fetch.assert_not_called()

    def test_rejects_unknown_key_id(self):
        self.assertIsNone(verify_access_token(self.token(kid="unknown-key")))

    def test_reuses_cached_keys(self):
        token = self.token()
        self.assertIsNotNone(verify_access_token(token))
        self.assertIsNotNone(verify_access_token(token))
        self.fetch.assert_called_once()

    def test_refreshes_for_a_rotated_key_after_the_refresh_cooldown(self):
        self.assertIsNotNone(verify_access_token(self.token()))
        self.jwks["keys"].append(self.public_jwk(self.next_private_key, "key-2"))
        rotated_token = self.token(key=self.next_private_key, kid="key-2")

        with patch("jwt.jwks_client.time.monotonic", return_value=monotonic() + 31):
            self.assertIsNotNone(verify_access_token(rotated_token))
        self.assertEqual(self.fetch.call_count, 2)

    def test_refreshes_expired_cache_and_rejects_a_removed_key(self):
        old_token = self.token()
        self.assertIsNotNone(verify_access_token(old_token))
        self.jwks = {"keys": [self.public_jwk(self.next_private_key, "key-2")]}

        with patch("jwt.jwks_client.time.monotonic", return_value=monotonic() + 301):
            self.assertIsNone(verify_access_token(old_token))
        self.assertEqual(self.fetch.call_count, 2)

    def test_key_service_outage_is_distinct_from_invalid_credentials(self):
        self.fetch.side_effect = URLError("service unavailable")
        with self.assertRaises(TokenVerificationUnavailableError):
            verify_access_token(self.token())

    def test_malformed_key_service_response_cannot_authenticate(self):
        self.fetch.side_effect = lambda *args, **kwargs: BytesIO(b"not JSON")
        with self.assertRaises(TokenVerificationUnavailableError):
            verify_access_token(self.token())

    def test_missing_configuration_is_reported_without_fetching_keys(self):
        with patch.dict(os.environ, {"SUPABASE_URL": ""}):
            with self.assertRaisesRegex(ValueError, "SUPABASE_URL"):
                verify_access_token(self.token())
        self.fetch.assert_not_called()

    def test_key_lookup_always_uses_our_configured_issuer(self):
        token = self.token(headers={"jku": "https://untrusted.example/keys"})
        self.assertIsNotNone(verify_access_token(token))
        self.assertEqual(self.fetch.call_args.args[0].full_url, f"{self.issuer}/.well-known/jwks.json")

    def test_health_endpoint_remains_public(self):
        with TestClient(app) as client:
            response = client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})
        self.fetch.assert_not_called()

    def test_me_rejects_missing_malformed_and_wrong_scheme_credentials(self):
        with TestClient(app) as client:
            for headers in [
                {},
                {"Authorization": "Bearer"},
                {"Authorization": "Basic invalid"},
                {"Authorization": "Bearer not-a-jwt"},
            ]:
                with self.subTest(headers=headers):
                    response = client.get("/me", headers=headers)
                    self.assertEqual(response.status_code, 401)
                    self.assertEqual(response.headers["WWW-Authenticate"], "Bearer")
                    self.assertEqual(response.json(), {"detail": "Missing or invalid bearer token"})
        self.fetch.assert_not_called()

    def test_me_returns_only_verified_user_id_and_email(self):
        with TestClient(app) as client:
            response = client.get("/me", headers={"Authorization": f"Bearer {self.token()}"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            "id": self.claims["sub"], "email": self.claims["email"],
        })

    def test_me_rejects_expired_and_forged_tokens(self):
        tokens = [
            self.token({**self.claims, "exp": int(time()) - 10}),
            self.token(key=self.next_private_key),
        ]
        with TestClient(app) as client:
            for token in tokens:
                response = client.get("/me", headers={"Authorization": f"Bearer {token}"})
                self.assertEqual(response.status_code, 401)
                self.assertEqual(response.headers["WWW-Authenticate"], "Bearer")

    def test_me_returns_service_unavailable_for_key_service_outages(self):
        self.fetch.side_effect = URLError("service unavailable")
        with TestClient(app) as client:
            response = client.get("/me", headers={"Authorization": f"Bearer {self.token()}"})
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"detail": "Authentication service temporarily unavailable"})

    def test_openapi_documents_bearer_authentication_for_me(self):
        schema = app.openapi()
        self.assertEqual(schema["components"]["securitySchemes"]["HTTPBearer"], {
            "type": "http", "scheme": "bearer",
        })
        self.assertEqual(schema["paths"]["/me"]["get"]["security"], [{"HTTPBearer": []}])
        self.assertNotIn("security", schema["paths"]["/health"]["get"])

    def test_browser_can_preflight_authorization_from_the_frontend(self):
        with TestClient(app) as client:
            response = client.options("/me", headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "authorization",
            })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Access-Control-Allow-Origin"], "http://localhost:5173")
        self.assertIn("authorization", response.headers["Access-Control-Allow-Headers"].lower())
        self.fetch.assert_not_called()

    def test_cors_does_not_allow_unconfigured_origins(self):
        with TestClient(app) as client:
            response = client.options("/me", headers={
                "Origin": "https://untrusted.example",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "authorization",
            })
        self.assertEqual(response.status_code, 400)
        self.assertNotIn("Access-Control-Allow-Origin", response.headers)

    def test_frontend_can_read_authentication_failures(self):
        with TestClient(app) as client:
            response = client.get("/me", headers={"Origin": "http://localhost:5173"})
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.headers["Access-Control-Allow-Origin"], "http://localhost:5173")


if __name__ == "__main__":
    unittest.main()
