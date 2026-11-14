# RoleMatch

Evidence-based resume and job description matching.

The backend CLI extracts document information, compares resume evidence against job requirements, calculates weighted scores, and saves reports. The React + TypeScript frontend is being rebuilt; API integration is pending.

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

## Run the frontend

Requires Node.js and npm. In a separate terminal, from the repository root:

```bash
cd frontend
npm install
npm run dev
```

Open the URL printed by Vite.
