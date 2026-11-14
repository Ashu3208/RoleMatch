# RoleMatch frontend

React + TypeScript + Vite, with ESLint. The interface is being rebuilt; backend API integration is pending. See the [project overview](../README.md) and [roadmap](../ROADMAP.md).

## Development

Requires Node.js and npm. Run from this `frontend` directory:

```bash
npm install
npm run dev
```

Open the URL printed by Vite.

For Supabase, copy `.env.example` to `.env` and set the project URL and publishable key. Restart the dev server after changing environment values.

## Checks and production preview

```bash
npm run lint
npm run build
npm run preview
```

The build checks TypeScript and writes production files to `dist/`. Preview serves that build locally.
