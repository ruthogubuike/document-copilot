# Frontend setup

This project uses a Vite + React SPA because the frontend is an internal tool that mainly needs fast iteration, authenticated app flows, and a clean connection to the FastAPI backend. We do not need the extra server-rendering, SEO, or full-stack routing features that Next.js is optimized for.

## Init (from empty `frontend/`)

```bash
cd frontend
pnpm create vite . --template react-ts
pnpm install
pnpm add react-router-dom @supabase/supabase-js
pnpm add -D tailwindcss @tailwindcss/vite @types/node
```

Add `@import "tailwindcss";` to the top of `src/index.css`, then configure the `@/*` import alias in `tsconfig.json`, `tsconfig.app.json`, and `vite.config.ts` (see [shadcn Vite install](https://ui.shadcn.com/docs/installation/vite)).

```bash
pnpm dlx shadcn@latest init
```

## Run

```bash
cd frontend
pnpm install
pnpm dev
```

## Check

```bash
pnpm tsc --noEmit
pnpm lint
```
