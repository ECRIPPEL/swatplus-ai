import projectData from "@/mock/project.json";
import findingsData from "@/mock/findings.json";
import hydrographData from "@/mock/hydrograph.json";
import iterationsData from "@/mock/iterations.json";
import chatData from "@/mock/chat.json";
import landuseData from "@/mock/landuse.json";
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

export async function getLanduse(): Promise<LanduseClass[]> {
  await sleep(200);
  return landuseData as LanduseClass[];
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

export type ReplyMode = "concise" | "free";

const MOCK_CONCISE: string[] = [
  "Widen CN2 to [-15%, +10%] and add GW_DELAY — peaks should climb.",
  "ALPHA_BF is pinned at the upper bound; freeing it fixes the baseflow drift.",
  "Daily NSE = 0.58 sits right at Moriasi's satisfactory threshold.",
  "A 3-year warmup is adequate for shallow-aquifer basins per Daggupati 2015.",
  "PBIAS of −8.3% is 'good' by Moriasi — the sign means slight over-prediction.",
  "Peak under-prediction is textbook CN2-too-low for clay-loam basins.",
  "NSE plateaued because the parameter set lost sensitivity around iteration 12.",
  "Yes — the pcp04 gap was infilled yesterday; a re-run will pick it up.",
];

const MOCK_FREE: string[] = [
  `Looking at your current state, two symptoms point at the same root cause:

- **Peak under-prediction** on the top 10 storm events (mean error −19%)
- **Baseflow over-prediction** during July–September recession (+12%)

Both are consistent with **CN2 bound too tight** for a clay-loam basin. Recommended adjustments for iteration 19:

1. Widen \`CN2\` to \`[-15%, +10%]\` (currently \`[-5%, +5%]\`)
2. Free \`ALPHA_BF\` by widening to \`[0.01, 0.8]\` — it's pinned at the upper bound
3. Add \`GW_DELAY\` to the set with range \`[0, 450]\` days

This follows Arnold et al. 2012 and the broader Moriasi 2015 guidance for humid subtropical basins.`,

  `Daily NSE of **0.58** sits right at the Moriasi 2007 boundary between *satisfactory* (≥ 0.50) and *good* (> 0.75). For a 412 km² basin on clay-loam dominant soils, expect to land in the 0.65–0.75 band with a well-calibrated parameter set — above 0.80 on daily streamflow is rare.

Progression over the last 10 iterations (0.51 → 0.58) shows the sensitivity surface flattening. If the next widened run adds less than +0.02, consider pivoting to a different structural assumption (e.g. plant uptake or soil AWC) rather than squeezing more out of CN2.`,

  `A 3-year warmup is **adequate** for shallow-aquifer basins. Daggupati et al. 2015 found no further reduction in output bias beyond 2 years when groundwater contributes under 50% to total flow. Your baseflow index is 0.71, so groundwater is significant but not dominant — 3 years is conservative and safe.

Don't extend just because the early years look odd — **those are already excluded from the calibration metrics**. The warmup buffer is doing what it's designed to do.`,

  `Draft paragraph for the results section:

> The model was calibrated against daily discharge at the outlet (cha033) over 2011–2016 and validated on 2017–2019. The final calibration achieved NSE = 0.58, KGE = 0.54, and PBIAS = −8.3% — *satisfactory* for NSE and *good* for PBIAS per Moriasi et al. 2007. Residual analysis indicates systematic under-prediction of storm peaks (mean peak residual −19%), consistent with reports for humid subtropical clay-dominated basins (Arnold et al. 2012).

Citations carried: \`Moriasi 2007\`, \`Arnold 2012\`, \`Daggupati 2015\`, \`White 2014\`.`,
];

export async function streamAssistantReply(
  userText: string,
  mode: ReplyMode,
  onChunk: (chunk: string) => void,
  signal?: AbortSignal
): Promise<void> {
  await sleep(160);
  const pool = mode === "concise" ? MOCK_CONCISE : MOCK_FREE;
  const idx = Math.abs(hashString(userText)) % pool.length;
  const reply = pool[idx];
  const words = reply.split(" ");
  for (const word of words) {
    if (signal?.aborted) return;
    await sleep(22);
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

export interface RouteContext {
  route: "home" | "setup" | "calibration" | "evaluation";
  title: string;
  placeholder: string;
  items: string[];
  suggestions: string[];
}

export function ctxForRoute(pathname: string): RouteContext {
  if (pathname.startsWith("/setup")) {
    return {
      route: "setup",
      title: "Setup context",
      placeholder: "Ask about a finding, a rule, or a fix…",
      items: ["15 findings", "2 errors", "URU basin"],
      suggestions: [
        "Why is pcp04 flagged with gaps?",
        "Explain the warmup-period rule.",
        "Can I ignore the info findings?",
      ],
    };
  }
  if (pathname.startsWith("/calibration")) {
    return {
      route: "calibration",
      title: "Calibration context",
      placeholder: "Ask about NSE, a parameter, or the next iteration…",
      items: ["iter 30", "NSE 0.58", "8 params"],
      suggestions: [
        "Why is NSE stuck at 0.58?",
        "What does ALPHA_BF do physically?",
        "Draft a widened CN2 proposal.",
      ],
    };
  }
  if (pathname.startsWith("/evaluation")) {
    return {
      route: "evaluation",
      title: "Evaluation context",
      placeholder: "Ask about residuals, Moriasi, or the draft paragraph…",
      items: ["NSE 0.58", "PBIAS −8.3%", "cha033"],
      suggestions: [
        "How does my NSE compare for similar basins?",
        "Is PBIAS of −8.3% good or satisfactory?",
        "Draft a paragraph for the results section.",
      ],
    };
  }
  return {
    route: "home",
    title: "Project context",
    placeholder: "Ask about URU Basin, the model, or where to start…",
    items: ["URU basin", "subtropical", "ready"],
    suggestions: [
      "Summarize URU basin for me.",
      "What should I do next?",
      "Is the warmup long enough for this biome?",
    ],
  };
}
