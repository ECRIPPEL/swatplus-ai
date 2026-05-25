// Shapes generated from `src/swatplus_ai/api/models.py` are the canonical
// wire contract for the three endpoints migrated in slice 3.4 (project,
// findings, landuse). We re-export them here under the names components
// have always imported so none of the consumers need to rename on migration.
// `FindingVM → Finding` and `LanduseSlice → LanduseClass` are purely
// back-compat aliases — the generated interfaces are authoritative.
import type { Citation } from "./schemas";

export type {
  Citation,
  FindingVM as Finding,
  LanduseSlice as LanduseClass,
  ProjectMeta,
} from "./schemas";

export type Severity = "error" | "warning" | "info";

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
