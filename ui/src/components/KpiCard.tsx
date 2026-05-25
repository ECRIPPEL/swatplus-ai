import type { ReactNode } from "react";
import { ArrowDown, ArrowUp, Minus } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import Sparkline from "@/components/Sparkline";
import { cn } from "@/lib/utils";

interface KpiCardProps {
  label: string;
  value: ReactNode;
  delta?: number;
  deltaSuffix?: string;
  deltaInverted?: boolean;
  trend?: number[];
  trendColor?: string;
  tag?: ReactNode;
  sub?: ReactNode;
  className?: string;
}

export default function KpiCard({
  label,
  value,
  delta,
  deltaSuffix,
  deltaInverted = false,
  trend,
  trendColor,
  tag,
  sub,
  className,
}: KpiCardProps) {
  const deltaSign = delta === undefined ? 0 : delta > 0 ? 1 : delta < 0 ? -1 : 0;
  const DeltaIcon = deltaSign === 0 ? Minus : deltaSign > 0 ? ArrowUp : ArrowDown;
  const goodSign = deltaInverted ? -1 : 1;
  const isPositive = deltaSign === goodSign;
  const isNegative = deltaSign === -goodSign;

  return (
    <Card className={cn("shadow-card", className)}>
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="text-[10.5px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
              {label}
            </div>
            <div className="mt-1.5 text-[26px] font-semibold leading-none tracking-[-0.02em] tabular-nums">
              {value}
            </div>
            {sub && (
              <div className="mt-1.5 text-[11.5px] text-muted-foreground">
                {sub}
              </div>
            )}
          </div>
          {trend && trend.length > 1 && (
            <div className="shrink-0 opacity-80">
              <Sparkline data={trend} color={trendColor} height={28} width={72} />
            </div>
          )}
        </div>
        {(delta !== undefined || tag) && (
          <div className="mt-3 flex items-center gap-2">
            {delta !== undefined && (
              <span
                className={cn(
                  "inline-flex items-center gap-1 rounded-md border px-1.5 py-0.5 text-[10.5px] font-medium",
                  isPositive &&
                    "border-emerald-500/25 bg-emerald-500/12 text-emerald-700 dark:text-emerald-300",
                  isNegative &&
                    "border-red-500/25 bg-red-500/12 text-red-700 dark:text-red-300",
                  !isPositive &&
                    !isNegative &&
                    "border-border bg-muted text-muted-foreground"
                )}
              >
                <DeltaIcon className="h-3 w-3" />
                {delta > 0 ? "+" : ""}
                {delta}
                {deltaSuffix ?? ""}
              </span>
            )}
            {tag}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
