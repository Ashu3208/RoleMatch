# RoleMatch

Evidence-based resume and job description matching.

## Current status

Extracts structured resume and job-description data using Groq and Pydantic validation. Uses PyMuPDF to extract PDF text in positional order; also supports DOCX documents and plain-text job descriptions. Matching and scoring are not implemented.

## Setup

Requires Python 3.14+ and uv.

Run from the project root:

```bash
uv sync
```

For LLM calls, copy `.env.example` to `.env` and set `GROQ_API_KEY`.

Place resumes in `data/Resume/` and job descriptions in `data/JD/`, then run:

```bash
uv run rolematch
```

Reads subdirectories and shows progress and per-directory summaries. Hidden, unsupported, and empty files are skipped. Extracted JSON is saved to disk rather than printed.

Extractions are saved as `<text_hash>.json` in `data/extraction/Resume/` and `data/extraction/JD/`. Unchanged text reuses valid saved data without an LLM call. Delete affected cache files after changing prompts or models to force re-extraction.

## Tests

```bash
uv run python -m unittest discover -s tests -v
```
