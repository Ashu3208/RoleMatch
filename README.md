# RoleMatch

Evidence-based resume and job description matching.

The backend CLI extracts document information, compares resume evidence against job requirements, calculates weighted scores, and saves reports. The React + TypeScript frontend supports Google sign-in and a profile page connected to FastAPI. Document processing integration is pending.

- [Backend](backend/README.md): document processing, CLI, and tests.
- [Frontend](frontend/README.md): development, builds, and linting.
- [Roadmap](ROADMAP.md): completed work and planned features.

## Run the backend

Requires Python 3.14+ and uv. From the repository root:

```bash
cd backend
uv sync
```

Inside `backend/`, copy `.env.example` to `.env` and set `GROQ_API_KEY`. Place resumes in `data/Resume/` and job descriptions in `data/JD/` within that directory.

From the `backend` directory:

```bash
uv run rolematch
```

For the web app, configure Supabase as described in the [backend guide](backend/README.md) and start the API with `uv run server` from `backend/`.

## Run the frontend

Requires Node.js and npm. In a separate terminal, from the repository root:

```bash
cd frontend
npm install
npm run dev
```

Configure `frontend/.env` using the [frontend guide](frontend/README.md), then open the URL printed by Vite.
