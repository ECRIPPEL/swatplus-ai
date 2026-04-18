# SWAT+ai · UI prototype

Standalone Vite + React + TypeScript prototype of the SWAT+ai desktop GUI. Every data source is mocked — nothing here imports from `src/swatplus_ai`. This subproject exists so the UI/UX can be iterated independently of the Python core; a later integration slice will wrap this SPA in a pywebview shell.

## How to run

```bash
cd ui
npm install
npm run dev
```

Open http://localhost:5173. Five routes are wired up: `/dashboard`, `/setup`, `/calibration`, `/evaluation`, `/chat`. The light/dark theme toggle persists to localStorage.

## Stack

- React 18 + TypeScript · Vite
- Tailwind CSS v3
- shadcn/ui (New York style, zinc base, violet primary) — components live in `src/components/ui/`
- lucide-react (icons), recharts (charts), react-router-dom (routing)

## Layout

```
ui/
├── src/
│   ├── components/
│   │   ├── Layout.tsx · Sidebar.tsx · TopBar.tsx
│   │   ├── ThemeProvider.tsx · ThemeToggle.tsx
│   │   └── ui/                     # shadcn primitives
│   ├── routes/                     # Dashboard / SetupCheck / Calibration / Evaluation / Chat
│   ├── mock/                       # JSON fixtures
│   └── lib/                        # types, mockApi, utils
├── tailwind.config.ts · postcss.config.js · components.json
└── package.json · tsconfig*.json · vite.config.ts
```

All fetches go through `src/lib/mockApi.ts`, which wraps the JSON files in `setTimeout` so the UI exercises loading skeletons. The chat route uses a chunk-by-chunk streaming simulation to match how the real LLM Gateway will stream.
