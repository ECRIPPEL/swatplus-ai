/// <reference types="vite/client" />

interface ImportMetaEnv {
  // Set to "1" in `.env.development` to force `@/lib/client` to use the
  // in-memory mock adapter instead of calling the FastAPI backend.
  readonly VITE_USE_MOCK?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
