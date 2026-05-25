// Runtime selector between the mock adapter (`./mockApi`) and the real
// HTTP adapter (`./api`). Every component imports from `@/lib/client`
// so the wiring stays identical regardless of where the data comes from.
//
// `VITE_USE_MOCK=1` (set in `.env.development` during Etapa 3) forces
// the mock. Clearing the flag routes every call through the FastAPI
// `swatplus-ai serve` backend — see slice 3.3 of the UI refactor plan.
//
// The two adapters expose the same function names on purpose; the only
// extra symbol is `EndpointNotImplementedError`, which components can
// catch to render a graceful "not implemented yet" placeholder.

import * as mockApi from "./mockApi";
import * as realApi from "./api";

const impl = import.meta.env.VITE_USE_MOCK === "1" ? mockApi : realApi;

export const {
  getProject,
  getFindings,
  getHydrograph,
  getIterations,
  getChatHistory,
  getLanduse,
  getCalParameters,
  getRecentActivity,
  streamAssistantReply,
  ctxForRoute,
} = impl;

export { EndpointNotImplementedError } from "./api";
export type { ReplyMode, RouteContext } from "./mockApi";
