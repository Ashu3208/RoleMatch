# RoleMatch frontend

React + TypeScript + Vite, with ESLint. Supports Google sign-in, saved-session restoration, and sign-out through Supabase. Navigation links to the account page (`/`) and profile (`/profile`), which loads verified user information from FastAPI's `/me` endpoint. Document processing integration is pending. See the [project overview](../README.md) and [roadmap](../ROADMAP.md).

## Development

Requires Node.js and npm. Run from this `frontend` directory:

Before starting, copy `.env.example` to `.env` if it is not already configured, and set the project URL and publishable key. Configure Google's OAuth provider and allowed frontend redirect URL in Supabase. Restart the dev server after changing environment values.

Start the backend separately with `uv run server` from `backend/`. `VITE_API_URL` defaults to `http://127.0.0.1:8000`; set it in the frontend `.env` if the API is hosted elsewhere. The backend's `FRONTEND_ORIGINS` must include the frontend's origin if it differs from the default port 5173.

```bash
npm install
npm run dev
```

Open the URL printed by Vite.

## Checks and production preview

```bash
npm test
npm run lint
npm run build
npm run preview
```

The build checks TypeScript and writes production files to `dist/`. Preview serves that build locally.

Auth and profile tests use Vitest and React Testing Library with mocked Supabase and API responses; they do not sign in to Google or contact Supabase.
