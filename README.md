# RoleMatch

Evidence-based resume and job description matching.

## Current status

Includes PDF and DOCX text extraction, Pydantic schemas for resumes and job descriptions, and a reusable Groq JSON client. Structured extraction, matching, and scoring are not implemented.

## Setup

Requires Python 3.14+ and uv.

Run from the project root:

```bash
uv sync
```

For LLM calls, copy `.env.example` to `.env` and set `GROQ_API_KEY`.

## Tests

```bash
uv run python -m unittest discover -s tests -v
```
