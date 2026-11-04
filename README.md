# RoleMatch

Evidence-based resume and job description matching.

## Current status

Includes Pydantic schemas for resumes and job descriptions, plus a reusable Groq function that requests JSON output and returns a Python dictionary. Resume parsing, matching, and scoring are not implemented.

## Setup

Requires Python 3.14+ and uv.

Run from the project root:

```bash
uv sync
```

For LLM calls, copy `.env.example` to `.env` and set `GROQ_API_KEY`.

