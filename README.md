# RoleMatch

Evidence-based resume and job description matching.

## Current status

Pydantic schemas are available for resumes, work experience, and job descriptions. Resume parsing, matching, and scoring are not implemented.

## Setup

Requires Python 3.14+ and uv.

Run from the project root:

```bash
uv sync
uv run rolematch
```

The command currently prints a starter greeting. Schema validation does not require an API key.

## Structure

- `src/rolematch/`: application package.
- `src/rolematch/schemas/resume.py`: `Resume` and nested `Experience` models.
- `src/rolematch/schemas/job_description.py`: `JobDescription` model.
- `pyproject.toml`: project metadata, dependencies, and the `rolematch` command.
- `uv.lock`: resolved dependency versions; commit this file.
- `.env.example`: configuration template, without secrets.
- `data/`: local resumes, job descriptions, and reports; contents are ignored by Git.

## Schemas

`Resume` captures contact information, total experience in years, skills, work experiences, projects, and certifications. Each `Experience` captures company, role, duration in months, description, and skills.

`JobDescription` captures title, company, location, employment type, description, minimum experience in years, responsibilities, and separate required and preferred skills and qualifications.



