# RoleMatch backend

Python CLI for document extraction, evidence-based matching, and weighted scoring. See the [project overview](../README.md) and [roadmap](../ROADMAP.md).

## Setup

Requires Python 3.14+ and uv.

Run these commands from this `backend` directory:

```bash
uv sync
```

For LLM calls, copy `.env.example` to `.env` and set `GROQ_API_KEY`.

Place resumes in `data/Resume/` and job descriptions in `data/JD/`, then run:

```bash
uv run rolematch
```

Supports PDF/DOCX resumes and PDF/DOCX/plain-text JDs. Reads subdirectories and shows progress and scores without printing JSON. Hidden, unsupported, and empty files are skipped.

Extractions are saved in `data/extraction/Resume/` and `data/extraction/JD/`. Unchanged text reuses valid saved data without an extraction LLM call. Delete affected cache files after changing extraction prompts or models to force re-extraction.

Comparison reports are saved in `data/reports/`, with evidence, reasoning, points per assessment, and overall and required/preferred totals. Every current resume–JD pair is compared on each run, replacing its previous report.

## API development server

From this `backend` directory:

```bash
uv run server
```

Starts Uvicorn with automatic reloading. Health check: <http://127.0.0.1:8000/health>. API docs: <http://127.0.0.1:8000/docs>.

For token verification, set `SUPABASE_URL` in the backend `.env`. The verifier accepts ES256 tokens, checks their signature, issuer, audience, expiry, and user ID, and retrieves public signing keys through a cached JWKS client.

`GET /health` is public. `GET /me` requires a Supabase bearer access token and returns the verified user ID and email. Missing or invalid credentials return `401`; signing-key service failures return `503`. To test in `/docs`, click **Authorize** and paste the access token without the `Bearer` prefix.

CORS allows GET requests with Authorization headers from `http://localhost:5173` and `http://127.0.0.1:5173`. Set the comma-separated `FRONTEND_ORIGINS` environment variable to change the allowed frontend origins, then restart the server.

## Tests

```bash
uv run python -m unittest discover -s tests -v
```
