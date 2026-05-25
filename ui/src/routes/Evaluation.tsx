import { useEffect, useMemo, useState } from "react";
import { Copy, FileText, Sparkles } from "lucide-react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip as RTooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import PageHeader from "@/components/PageHeader";
import ChartTooltip from "@/components/ChartTooltip";
import CitePop from "@/components/CitePop";
import {
  classify,
  classBadgeVariant,
  classLabel,
  MoriasiBadge,
  moriasiThresholdsLabel,
  type MetricKind,
  type MoriasiClass,
} from "@/lib/moriasi";
import { getHydrograph, getIterations } from "@/lib/client";
import type { Citation, HydrographPoint, IterationResult } from "@/lib/types";
import { cn, formatNumber } from "@/lib/utils";

const DRAFT_CITATIONS: Citation[] = [
  {
    id: "m07",
    label: "Moriasi 2007",
    source: "Moriasi et al., Trans. ASABE 50(3), 2007 — model evaluation guidelines.",
  },
  {
    id: "a12",
    label: "Arnold 2012",
    source: "Arnold et al., Trans. ASABE 55(4), 2012 — SWAT model development.",
  },
  {
    id: "d15",
    label: "Daggupati 2015",
    source: "Daggupati et al., JAWRA 51(6), 2015 — warmup and validation framework.",
  },
  {
    id: "w14",
    label: "White 2014",
    source: "White et al., JAWRA 50(5), 2014 — evapotranspiration budgets in humid basins.",
  },
];

export default function Evaluation() {
  const [hydro, setHydro] = useState<HydrographPoint[] | null>(null);
  const [iters, setIters] = useState<IterationResult[] | null>(null);

  useEffect(() => {
    getHydrograph().then(setHydro);
    getIterations().then(setIters);
  }, []);

  const latest = iters?.[iters.length - 1] ?? null;

  const metrics = useMemo<
    { label: string; value: number; kind: MetricKind; fmt: (n: number) => string }[] | null
  >(() => {
    if (!latest) return null;
    return [
      { label: "NSE", value: latest.nse, kind: "nse", fmt: (n) => formatNumber(n, 3) },
      { label: "KGE", value: latest.kge, kind: "kge", fmt: (n) => formatNumber(n, 3) },
      {
        label: "PBIAS",
        value: latest.pbias,
        kind: "pbias",
        fmt: (n) => `${formatNumber(n, 1)}%`,
      },
      { label: "R²", value: latest.r2, kind: "r2", fmt: (n) => formatNumber(n, 3) },
    ];
  }, [latest]);

  const overall = useMemo<MoriasiClass | null>(() => {
    if (!metrics) return null;
    const classes = metrics.map((m) => classify(m.value, m.kind));
    if (classes.includes("unacceptable")) return "unacceptable";
    if (classes.every((c) => c === "good")) return "good";
    return "satisfactory";
  }, [metrics]);

  const hydroWindow = useMemo(() => {
    if (!hydro) return null;
    return hydro.slice(-365);
  }, [hydro]);

  return (
    <div className="mx-auto max-w-[1280px] space-y-6">
      <PageHeader
        overline="Module 3 · Evaluation"
        title="Evaluation"
        desc="Final metrics classified against Moriasi 2007 guidance for daily streamflow. Residuals grounded against literature for comparable basins."
        status={
          overall ? (
            <Badge variant={classBadgeVariant(overall)}>
              Overall · {classLabel(overall)}
            </Badge>
          ) : null
        }
        actions={
          <Button size="sm" variant="outline" className="gap-1.5">
            <Sparkles className="h-3.5 w-3.5" />
            Re-evaluate
          </Button>
        }
      />

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        {metrics
          ? metrics.map((m) => (
              <MoriasiMetricCard
                key={m.label}
                label={m.label}
                value={m.value}
                kind={m.kind}
                display={m.fmt(m.value)}
              />
            ))
          : Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-[130px] w-full rounded-xl" />
            ))}
      </div>

      <Card className="shadow-card">
        <CardHeader className="pb-2">
          <CardTitle className="text-[14px] font-semibold">
            Observed vs simulated — outfall cha033
          </CardTitle>
          <div className="text-[11.5px] text-muted-foreground">
            Daily discharge (m³/s) · last 365 days of simulation
          </div>
        </CardHeader>
        <CardContent>
          <div className="h-[340px]">
            {hydroWindow ? (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart
                  data={hydroWindow}
                  margin={{ top: 8, right: 12, bottom: 4, left: 0 }}
                >
                  <defs>
                    <linearGradient id="obsFill" x1="0" y1="0" x2="0" y2="1">
                      <stop
                        offset="0%"
                        stopColor="hsl(var(--chart-2))"
                        stopOpacity={0.24}
                      />
                      <stop
                        offset="100%"
                        stopColor="hsl(var(--chart-2))"
                        stopOpacity={0}
                      />
                    </linearGradient>
                    <linearGradient id="simFill" x1="0" y1="0" x2="0" y2="1">
                      <stop
                        offset="0%"
                        stopColor="hsl(var(--primary))"
                        stopOpacity={0.22}
                      />
                      <stop
                        offset="100%"
                        stopColor="hsl(var(--primary))"
                        stopOpacity={0}
                      />
                    </linearGradient>
                  </defs>
                  <CartesianGrid
                    strokeDasharray="3 3"
                    vertical={false}
                    stroke="hsl(var(--chart-grid))"
                  />
                  <XAxis
                    dataKey="date"
                    tickFormatter={(d) => (d as string).slice(5)}
                    tickLine={false}
                    axisLine={false}
                    tick={{
                      fontSize: 11,
                      fill: "hsl(var(--muted-foreground))",
                    }}
                    minTickGap={48}
                  />
                  <YAxis
                    tickLine={false}
                    axisLine={false}
                    tick={{
                      fontSize: 11,
                      fill: "hsl(var(--muted-foreground))",
                    }}
                    width={36}
                  />
                  <RTooltip
                    content={
                      <ChartTooltip
                        formatter={(v) => `${formatNumber(v, 2)} m³/s`}
                      />
                    }
                  />
                  <Area
                    type="monotone"
                    dataKey="observed"
                    stroke="hsl(var(--chart-2))"
                    strokeWidth={1.4}
                    fill="url(#obsFill)"
                    name="Observed"
                    isAnimationActive={false}
                  />
                  <Area
                    type="monotone"
                    dataKey="simulated"
                    stroke="hsl(var(--primary))"
                    strokeWidth={1.4}
                    fill="url(#simFill)"
                    name="Simulated"
                    isAnimationActive={false}
                  />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <Skeleton className="h-full w-full" />
            )}
          </div>
          <div className="mt-3 flex items-center gap-4 text-[11px] text-muted-foreground">
            <LegendSwatch color="hsl(var(--chart-2))" label="Observed" />
            <LegendSwatch color="hsl(var(--primary))" label="Simulated" />
          </div>
        </CardContent>
      </Card>

      <Card className="shadow-card">
        <CardHeader className="pb-2">
          <CardTitle className="text-[14px] font-semibold">
            Moriasi classification
          </CardTitle>
          <div className="text-[11.5px] text-muted-foreground">
            Current metric placed inside the Moriasi 2007 daily-streamflow bands
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {metrics
            ? metrics.map((m) => (
                <ClassificationBar
                  key={m.label}
                  label={m.label}
                  value={m.value}
                  kind={m.kind}
                  display={m.fmt(m.value)}
                />
              ))
            : Array.from({ length: 4 }).map((_, i) => (
                <Skeleton key={i} className="h-8 w-full" />
              ))}
        </CardContent>
      </Card>

      <Card className="shadow-card">
        <CardHeader className="flex flex-row items-start justify-between space-y-0 pb-2">
          <div>
            <CardTitle className="flex items-center gap-2 text-[14px] font-semibold">
              <FileText className="h-4 w-4 text-muted-foreground" />
              Draft paragraph
            </CardTitle>
            <div className="mt-1 text-[11.5px] text-muted-foreground">
              Generated from current metrics. Click any citation marker to
              inspect the source.
            </div>
          </div>
          <Button variant="outline" size="sm" className="gap-1.5">
            <Copy className="h-3.5 w-3.5" />
            Copy
          </Button>
        </CardHeader>
        <CardContent>
          <div className="space-y-3 text-[13.5px] leading-[1.7]">
            <p>
              The model was calibrated against daily discharge at the basin
              outlet (cha033) for the period 2011–2016 and validated over
              2017–2019. The final calibration achieved NSE = 0.58, KGE = 0.54,
              and PBIAS = −8.3%
              <CitePop n={1} citation={DRAFT_CITATIONS[0]} />
              {" "}(Moriasi et al. 2007 classification: <em>satisfactory</em>
              {" "}for NSE, KGE and <em>good</em> for PBIAS).
            </p>
            <p>
              Residual analysis indicates systematic under-prediction of storm
              peaks (mean peak residual −19%), consistent with reports for
              humid subtropical clay-dominated basins when CN2 is tightly
              bounded
              <CitePop n={2} citation={DRAFT_CITATIONS[1]} />. Baseflow
              separation yields a simulated baseflow index of 0.71 versus an
              observed 0.58; further iterations relaxing ALPHA_BF and GW_DELAY
              are expected to close this gap
              <CitePop n={3} citation={DRAFT_CITATIONS[3]} />.
            </p>
            <p>
              Warmup (3 years) meets the threshold recommended for
              shallow-aquifer basins
              <CitePop n={4} citation={DRAFT_CITATIONS[2]} />
              {" "}and was excluded from all reported metrics.
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function MoriasiMetricCard({
  label,
  value,
  kind,
  display,
}: {
  label: string;
  value: number;
  kind: MetricKind;
  display: string;
}) {
  return (
    <Card className="shadow-card">
      <CardContent className="p-4">
        <div className="text-[10.5px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
          {label}
        </div>
        <div className="mt-1.5 text-[28px] font-semibold leading-none tracking-[-0.02em] tabular-nums">
          {display}
        </div>
        <div className="mt-3">
          <MoriasiBadge value={value} kind={kind} />
        </div>
        <div className="mt-2 font-mono text-[10.5px] text-muted-foreground">
          {moriasiThresholdsLabel(kind)}
        </div>
      </CardContent>
    </Card>
  );
}

function ClassificationBar({
  label,
  value,
  kind,
  display,
}: {
  label: string;
  value: number;
  kind: MetricKind;
  display: string;
}) {
  const cls = classify(value, kind);
  let unacceptPct: number;
  let satPct: number;
  let goodPct: number;
  let markerPct: number;

  if (kind === "pbias") {
    unacceptPct = 100 / 3;
    satPct = 100 / 3;
    goodPct = 100 - unacceptPct - satPct;
    const abs = Math.min(30, Math.abs(value));
    markerPct = 100 - (abs / 30) * 100;
  } else {
    unacceptPct = 50;
    satPct = 25;
    goodPct = 25;
    const clamped = Math.max(0, Math.min(1, value));
    markerPct = clamped * 100;
  }

  return (
    <div>
      <div className="mb-1.5 flex items-baseline justify-between">
        <div className="flex items-baseline gap-2">
          <span className="text-[12.5px] font-medium">{label}</span>
          <span className="font-mono text-[12px] tabular-nums text-muted-foreground">
            {display}
          </span>
        </div>
        <span className="text-[10.5px] uppercase tracking-[0.12em] text-muted-foreground">
          {classLabel(cls)}
        </span>
      </div>
      <div className="relative h-2.5 w-full overflow-hidden rounded-full border">
        <div
          className="absolute inset-y-0 left-0 bg-red-500/22"
          style={{ width: `${unacceptPct}%` }}
        />
        <div
          className="absolute inset-y-0 bg-amber-500/22"
          style={{ left: `${unacceptPct}%`, width: `${satPct}%` }}
        />
        <div
          className="absolute inset-y-0 bg-emerald-500/22"
          style={{ left: `${unacceptPct + satPct}%`, width: `${goodPct}%` }}
        />
        <span
          className={cn(
            "absolute top-[-3px] bottom-[-3px] w-[2px] rounded-sm",
            cls === "good" && "bg-emerald-600",
            cls === "satisfactory" && "bg-amber-600",
            cls === "unacceptable" && "bg-red-600"
          )}
          style={{ left: `calc(${markerPct}% - 1px)` }}
        />
      </div>
    </div>
  );
}

function LegendSwatch({ color, label }: { color: string; label: string }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <span
        className="inline-block h-[2px] w-3 rounded-full"
        style={{ backgroundColor: color }}
      />
      {label}
    </span>
  );
}
