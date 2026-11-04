# RoleMatch

Evidence-based resume and job description matching.

## Current status

Project scaffold only. Resume parsing, matching, and scoring are not implemented yet.

## Setup

```bash
uv sync
cp .env.example .env
# Add your Groq API key to .env.
uv run --env-file .env rolematch
```

The command currently prints a starter greeting. Python 3.14 is used to match the existing learning environment.

## Structure

- `src/rolematch/`: application package.
- `pyproject.toml`: project metadata, dependencies, and the `rolematch` command.
- `uv.lock`: resolved dependency versions; commit this file.
- `.env.example`: configuration template, without secrets.
- `data/`: local resumes, job descriptions, and reports; contents are ignored by Git.

Add focused modules as each feature is implemented:

```text
src/rolematch/
    __init__.py
    cli.py          # Inputs and orchestration; move the entry point here
    schemas.py      # Pydantic extraction and assessment models
    parser.py       # PDF text extraction
    matcher.py      # LLM calls and response validation
    scoring.py      # Explicit scoring rubric calculated in Python
tests/             # Parsing, validation, and scoring tests
```

Start with the command line workflow. Add an API or UI once parsing, matching, and scoring work reliably. Keep only synthetic or explicitly shareable samples in version control.

## Personal Git identity

This repository uses local Git settings for `Ashutosh Agrawal <ashutoshagrawal822@gmail.com>`.
The remote points to `Ashu3208/RoleMatch`.

The repository credential helper requests only the GitHub CLI token for `Ashu3208`; it does not fall back to another account's saved token. The saved token was verified as belonging to `Ashu3208` during setup. If reauthentication is needed later:

```bash
gh auth login --hostname github.com --git-protocol https --web
```

Choose `Ashu3208` in the browser. The commit email should be added and verified on that GitHub account for attribution.
