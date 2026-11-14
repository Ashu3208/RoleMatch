# RoleMatch frontend

React + TypeScript + Vite, with ESLint. Supports Google sign-in, saved-session restoration, and sign-out for the current browser session through Supabase. Backend API integration is pending. See the [project overview](../README.md) and [roadmap](../ROADMAP.md).

## Development

Requires Node.js and npm. Run from this `frontend` directory:

Before starting, copy `.env.example` to `.env` if it is not already configured, and set the project URL and publishable key. Configure Google's OAuth provider and allowed frontend redirect URL in Supabase. Restart the dev server after changing environment values.

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

Auth tests use Vitest and React Testing Library with mocked Supabase responses; they do not sign in to Google or contact Supabase.
