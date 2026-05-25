import { Badge } from "@/components/ui/badge";

export type MetricKind = "nse" | "kge" | "pbias" | "r2";
export type MoriasiClass = "good" | "satisfactory" | "unacceptable";

export function classify(value: number, kind: MetricKind): MoriasiClass {
  if (kind === "pbias") {
    const a = Math.abs(value);
    return a < 10 ? "good" : a < 15 ? "satisfactory" : "unacceptable";
  }
  return value > 0.75 ? "good" : value >= 0.5 ? "satisfactory" : "unacceptable";
}

export function classLabel(cls: MoriasiClass): string {
  if (cls === "good") return "Good";
  if (cls === "satisfactory") return "Satisfactory";
  return "Unacceptable";
}

export function classBadgeVariant(
  cls: MoriasiClass
): "success" | "warning" | "destructive" {
  if (cls === "good") return "success";
  if (cls === "satisfactory") return "warning";
  return "destructive";
}

export function moriasiThresholdsLabel(kind: MetricKind): string {
  if (kind === "pbias") return "|PBIAS| < 10 good · < 15 sat.";
  return "> 0.75 good · ≥ 0.5 sat.";
}

interface MoriasiBadgeProps {
  value: number;
  kind: MetricKind;
  prefix?: boolean;
  className?: string;
}

export function MoriasiBadge({
  value,
  kind,
  prefix = true,
  className,
}: MoriasiBadgeProps) {
  const cls = classify(value, kind);
  return (
    <Badge variant={classBadgeVariant(cls)} className={className}>
      {prefix ? "Moriasi · " : ""}
      {classLabel(cls)}
    </Badge>
  );
}
