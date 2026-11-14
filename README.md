# RoleMatch

Evidence-based resume and job description matching.

## Current status

Extracts resume and job-description information, matches requirements to resume evidence, and calculates weighted scores. The CLI processes PDF/DOCX resumes and PDF/DOCX/plain-text JDs, then saves a report for each current resume–JD pair.

See [ROADMAP.md](ROADMAP.md) for completed work, the current task, and upcoming milestones, including the personal knowledge hub and RAG-assisted resume suggestions.

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

Comparison reports are saved in `data/reports/`, identified by both documents' text hashes. Each assessment includes evidence, reasoning, and earned/possible points, alongside overall and required/preferred totals. Comparisons are recomputed on each run and replace the previous report for the same pair; historical extraction files are not automatically included.

## Tests

```bash
uv run python -m unittest discover -s tests -v
```
