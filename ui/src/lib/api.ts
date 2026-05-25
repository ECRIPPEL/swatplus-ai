// Real HTTP adapter — mirrors the surface of `./mockApi` so
// `./client` can pick one or the other transparently.
//
// Endpoints that the FastAPI `serve` subcommand does not implement yet
// throw `EndpointNotImplementedError`. The calling component renders a
// graceful placeholder; see the Etapa 3 roadmap for migration order:
// project / findings / landuse land in slice 3.4, the rest stay mock
// until Phase 2 (LLM) / Phase 3 (calibration pipeline) of the canonical
// roadmap.
//
// `streamAssistantReply` and `ctxForRoute` are re-exported from
// `./mockApi` because neither has a real backend yet — the LLM AskBar
// is wired up in Phase 2, not in this refactor.

import { ctxForRoute, streamAssistantReply, type ReplyMode, type RouteContext } from "./mockApi";
import type {
  ActivityEntry,
  CalParameter,
  ChatMessage,
  Finding,
  HydrographPoint,
  IterationResult,
  LanduseClass,
  ProjectMeta,
} from "./types";

export class EndpointNotImplementedError extends Error {
  constructor(endpoint: string) {
    super(
      `${endpoint} is not implemented by the current swatplus-ai serve. ` +
        `Re-run with VITE_USE_MOCK=1 for a local mock, or wait for a future migration slice.`
    );
    this.name = "EndpointNotImplementedError";
  }
}

async function fetchJson<T>(path: string): Promise<T> {
  const res = await fetch(path, { headers: { accept: "application/json" } });
  if (res.status === 501) {
    throw new EndpointNotImplementedError(path);
  }
  if (!res.ok) {
    throw new Error(`${path} failed: ${res.status} ${res.statusText}`);
  }
  return (await res.json()) as T;
}

export async function getProject(): Promise<ProjectMeta> {
  return fetchJson<ProjectMeta>("/api/project");
}

export async function getFindings(): Promise<Finding[]> {
  return fetchJson<Finding[]>("/api/findings");
}

export async function getLanduse(): Promise<LanduseClass[]> {
  return fetchJson<LanduseClass[]>("/api/landuse");
}

export async function getHydrograph(): Promise<HydrographPoint[]> {
  return fetchJson<HydrographPoint[]>("/api/hydrograph");
}

export async function getIterations(): Promise<IterationResult[]> {
  return fetchJson<IterationResult[]>("/api/iterations");
}

export async function getCalParameters(): Promise<CalParameter[]> {
  return fetchJson<CalParameter[]>("/api/cal-parameters");
}

export async function getRecentActivity(): Promise<ActivityEntry[]> {
  return fetchJson<ActivityEntry[]>("/api/activity");
}

export async function getChatHistory(): Promise<ChatMessage[]> {
  return fetchJson<ChatMessage[]>("/api/chat-history");
}

export { ctxForRoute, streamAssistantReply };
export type { ReplyMode, RouteContext };
