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

## Tests

```bash
uv run python -m unittest discover -s tests -v
```
