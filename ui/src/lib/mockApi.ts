import projectData from "@/mock/project.json";
import findingsData from "@/mock/findings.json";
import hydrographData from "@/mock/hydrograph.json";
import iterationsData from "@/mock/iterations.json";
import chatData from "@/mock/chat.json";
import type {
  ActivityEntry,
  CalParameter,
  ChatMessage,
  Finding,
  HydrographPoint,
  IterationResult,
  ProjectMeta,
} from "./types";

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

export async function getProject(): Promise<ProjectMeta> {
  await sleep(200);
  return projectData as ProjectMeta;
}

export async function getFindings(): Promise<Finding[]> {
  await sleep(300);
  return findingsData as Finding[];
}

export async function getHydrograph(): Promise<HydrographPoint[]> {
  await sleep(400);
  return hydrographData as HydrographPoint[];
}

export async function getIterations(): Promise<IterationResult[]> {
  await sleep(300);
  return iterationsData as IterationResult[];
}

export async function getChatHistory(): Promise<ChatMessage[]> {
  await sleep(200);
  return chatData as ChatMessage[];
}

export async function getCalParameters(): Promise<CalParameter[]> {
  await sleep(250);
  return [
    {
      name: "CN2",
      description: "SCS curve number (moisture condition II)",
      change: "pctchg",
      lowerBound: -15,
      upperBound: 10,
      initial: 0,
      sensitivity: 0.91,
    },
    {
      name: "ALPHA_BF",
      description: "Baseflow recession constant",
      change: "absval",
      lowerBound: 0.01,
      upperBound: 0.8,
      initial: 0.048,
      sensitivity: 0.74,
    },
    {
      name: "GW_DELAY",
      description: "Groundwater delay time (days)",
      change: "absval",
      lowerBound: 0,
      upperBound: 450,
      initial: 31,
      sensitivity: 0.52,
    },
    {
      name: "SURLAG",
      description: "Surface runoff lag coefficient",
      change: "absval",
      lowerBound: 0.5,
      upperBound: 12,
      initial: 4,
      sensitivity: 0.48,
    },
    {
      name: "GWQMN",
      description: "Threshold depth of water for return flow (mm)",
      change: "absval",
      lowerBound: 0,
      upperBound: 5000,
      initial: 1000,
      sensitivity: 0.41,
    },
    {
      name: "ESCO",
      description: "Soil evaporation compensation factor",
      change: "absval",
      lowerBound: 0.3,
      upperBound: 0.95,
      initial: 0.95,
      sensitivity: 0.12,
    },
    {
      name: "EPCO",
      description: "Plant uptake compensation factor",
      change: "absval",
      lowerBound: 0.3,
      upperBound: 1.0,
      initial: 1.0,
      sensitivity: 0.11,
    },
    {
      name: "SOL_AWC",
      description: "Soil available water capacity (mm H₂O / mm soil)",
      change: "pctchg",
      lowerBound: -20,
      upperBound: 20,
      initial: 0,
      sensitivity: 0.38,
    },
  ];
}

export async function getRecentActivity(): Promise<ActivityEntry[]> {
  await sleep(200);
  return [
    {
      id: "a1",
      kind: "setup",
      summary: "Setup check completed — 15 findings (2 error, 8 warning, 5 info)",
      timestamp: "2026-04-17T09:02:11Z",
    },
    {
      id: "a2",
      kind: "calibration",
      summary: "Calibration iteration 18 finished · NSE 0.58 · KGE 0.54",
      timestamp: "2026-04-17T08:47:03Z",
    },
    {
      id: "a3",
      kind: "evaluation",
      summary: "Evaluation draft paragraph generated",
      timestamp: "2026-04-16T17:22:44Z",
    },
    {
      id: "a4",
      kind: "chat",
      summary: "8-turn chat on CN2 sensitivity and peak under-prediction",
      timestamp: "2026-04-16T16:05:19Z",
    },
    {
      id: "a5",
      kind: "setup",
      summary: "pcp04 precipitation gap infilled from neighbour station",
      timestamp: "2026-04-16T11:33:01Z",
    },
  ];
}

const MOCK_REPLIES: string[] = [
  "Looking at your current state — the peak under-prediction pattern and the high baseflow index (0.71) are pointing at the same thing: CN2 is running too low. I'd widen CN2 to [-15%, +10%] and add GW_DELAY to the parameter set before the next iteration.",
  "For basins the size of URU (412 km²) with clay-loam dominant soils, daily NSE above 0.65 is achievable but rarely above 0.80. Moriasi 2007 puts your current 0.58 at the satisfactory/unsatisfactory boundary — the next round should comfortably push you into satisfactory.",
  "That symptom usually comes from one of three causes: a narrow CN2 range, a pinned ALPHA_BF, or an overzealous PET method. Your diagnostic flagged the first two; if you want, I can draft a parameter set for iteration 19.",
  "The warmup is fine. Your 3-year warmup is adequate per Daggupati 2015 for shallow-aquifer basins — don't extend it just because the first years of simulation look odd; those are part of the warmup and are already being skipped from the metrics.",
];

export async function streamAssistantReply(
  userText: string,
  onChunk: (chunk: string) => void,
  signal?: AbortSignal
): Promise<void> {
  await sleep(400);
  const idx = Math.abs(hashString(userText)) % MOCK_REPLIES.length;
  const reply = MOCK_REPLIES[idx];
  const words = reply.split(" ");
  for (const word of words) {
    if (signal?.aborted) return;
    await sleep(35);
    onChunk(word + " ");
  }
}

function hashString(s: string): number {
  let h = 0;
  for (let i = 0; i < s.length; i++) {
    h = (h << 5) - h + s.charCodeAt(i);
    h |= 0;
  }
  return h;
}
