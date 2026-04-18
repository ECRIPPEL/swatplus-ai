export type Severity = "error" | "warning" | "info";

export interface Citation {
  id: string;
  label: string;
  source: string;
}

export interface Finding {
  id: string;
  severity: Severity;
  title: string;
  location: string;
  evidence: string;
  explanation: string;
  suggestion: string;
  citations: Citation[];
  ruleId: string;
}

export interface ProjectMeta {
  name: string;
  path: string;
  simulationStart: string;
  simulationEnd: string;
  warmupYears: number;
  subbasins: number;
  hrus: number;
  channels: number;
  weatherStations: number;
  modelVersion: string;
  outfallChannel: string;
  climate: string;
  area_km2: number;
  readyToRun: boolean;
}

export interface HydrographPoint {
  date: string;
  observed: number;
  simulated: number;
}

export interface IterationResult {
  iteration: number;
  nse: number;
  kge: number;
  pbias: number;
  r2: number;
}

export type ChatRole = "user" | "assistant";

export interface ChatMessage {
  id: string;
  role: ChatRole;
  content: string;
  citations?: Citation[];
  timestamp: string;
}

export type MoriasiClass = "good" | "satisfactory" | "unacceptable";

export interface CalParameter {
  name: string;
  description: string;
  change: "absval" | "pctchg" | "abschg";
  lowerBound: number;
  upperBound: number;
  initial: number;
  sensitivity: number;
}

export interface ActivityEntry {
  id: string;
  kind: "setup" | "calibration" | "evaluation" | "chat";
  summary: string;
  timestamp: string;
}
