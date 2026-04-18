import * as React from "react";
import { useEffect, useMemo, useState } from "react";
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Droplets,
  Info,
  Sparkles,
  TrendingUp,
  XCircle,
} from "lucide-react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip as RTooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Skeleton } from "@/components/ui/skeleton";
import {
  getFindings,
  getHydrograph,
  getProject,
  getRecentActivity,
} from "@/lib/mockApi";
import type {
  ActivityEntry,
  Finding,
  HydrographPoint,
  ProjectMeta,
} from "@/lib/types";
import { cn, formatNumber } from "@/lib/utils";

const RANGES = [
  { id: "1M", days: 30 },
  { id: "3M", days: 90 },
  { id: "6M", days: 180 },
  { id: "1Y", days: 365 },
] as const;

export default function Dashboard() {
  const [project, setProject] = useState<ProjectMeta | null>(null);
  const [findings, setFindings] = useState<Finding[] | null>(null);
  const [hydro, setHydro] = useState<HydrographPoint[] | null>(null);
  const [activity, setActivity] = useState<ActivityEntry[] | null>(null);
  const [range, setRange] = useState<(typeof RANGES)[number]["id"]>("3M");

  useEffect(() => {
    getProject().then(setProject);
    getFindings().then(setFindings);
    getHydrograph().then(setHydro);
    getRecentActivity().then(setActivity);
  }, []);

  const counts = useMemo(() => {
    if (!findings) return { error: 0, warning: 0, info: 0 };
    return findings.reduce(
      (acc, f) => ({ ...acc, [f.severity]: acc[f.severity] + 1 }),
      { error: 0, warning: 0, info: 0 }
    );
  }, [findings]);

  const windowed = useMemo(() => {
    if (!hydro) return [];
    const days = RANGES.find((r) => r.id === range)!.days;
    return hydro.slice(-days);
  }, [hydro, range]);

  const waterBalance = useMemo(() => {
    // synthetic monthly water-balance totals derived from hydrograph
    if (!hydro) return [];
    const months: Record<string, { precip: number; et: number; runoff: number }> = {};
    hydro.forEach((p, i) => {
      const m = p.date.slice(0, 7);
      if (!months[m]) months[m] = { precip: 0, et: 0, runoff: 0 };
      const seasonal = 80 + 60 * Math.sin(i * 0.017);
      months[m].precip += seasonal / 30;
      months[m].et += (seasonal * 0.62) / 30;
      months[m].runoff += p.observed * 0.08;
    });
    return Object.entries(months).map(([month, v]) => ({
      month: month.slice(5),
      ...v,
    }));
  }, [hydro]);

  return (
    <div className="space-y-6">
      {/* header + CTA row */}
      <div className="flex items-start justify-between">
        <div>
          <div className="mb-1 text-sm text-muted-foreground">
            Project overview
          </div>
          <h2 className="text-2xl font-semibold tracking-tight">
            {project?.name ?? <Skeleton className="h-8 w-40" />}
          </h2>
          {project && (
            <div className="mt-1 text-sm text-muted-foreground">
              {project.climate} · {formatNumber(project.area_km2, 1)} km² ·{" "}
              {project.hrus} HRUs · outfall {project.outfallChannel}
            </div>
          )}
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm">
            Re-scan project
          </Button>
          <Button size="sm" className="gap-2">
            <Sparkles className="h-3.5 w-3.5" />
            Run setup check
          </Button>
        </div>
      </div>

      {/* Hero number + severity cards row */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-4">
        <Card className="lg:col-span-2">
          <CardHeader className="flex flex-row items-start justify-between space-y-0 pb-2">
            <div>
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Simulation period
              </CardTitle>
              <div className="mt-3 flex items-baseline gap-2">
                <span className="text-4xl font-semibold tracking-tight">
                  {project ? (
                    `${new Date(project.simulationStart).getFullYear()}–${new Date(
                      project.simulationEnd
                    ).getFullYear()}`
                  ) : (
                    <Skeleton className="h-10 w-36" />
                  )}
                </span>
                <span className="text-sm text-muted-foreground">
                  {project ? `${project.warmupYears}-yr warmup` : ""}
                </span>
              </div>
              <div className="mt-2 flex items-center gap-2">
                <Badge variant="success" className="gap-1">
                  <CheckCircle2 className="h-3 w-3" /> Model ready to run
                </Badge>
                <span className="text-xs text-muted-foreground">
                  12 years daily · outfall {project?.outfallChannel ?? "…"}
                </span>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="h-[170px]">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={waterBalance}>
                  <defs>
                    <linearGradient id="wbPrecip" x1="0" y1="0" x2="0" y2="1">
                      <stop
                        offset="0%"
                        stopColor="hsl(var(--primary))"
                        stopOpacity={0.35}
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
                    stroke="hsl(var(--border))"
                  />
                  <XAxis
                    dataKey="month"
                    tickLine={false}
                    axisLine={false}
                    tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
                  />
                  <YAxis hide />
                  <RTooltip
                    contentStyle={{
                      background: "hsl(var(--popover))",
                      border: "1px solid hsl(var(--border))",
                      borderRadius: 8,
                      fontSize: 12,
                    }}
                  />
                  <Area
                    type="monotone"
                    dataKey="precip"
                    stroke="hsl(var(--primary))"
                    strokeWidth={2}
                    fill="url(#wbPrecip)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
            <div className="mt-2 flex items-center justify-between text-xs text-muted-foreground">
              <span>Monthly precipitation (mm)</span>
              <span className="inline-flex items-center gap-1 text-emerald-600">
                <TrendingUp className="h-3 w-3" /> 1,427 mm/yr
              </span>
            </div>
          </CardContent>
        </Card>

        <SeverityCard
          title="Errors"
          count={counts.error}
          icon={XCircle}
          tone="destructive"
          sub="Block the setup"
          loading={!findings}
        />
        <SeverityCard
          title="Warnings"
          count={counts.warning}
          icon={AlertTriangle}
          tone="warning"
          sub="Worth reviewing"
          loading={!findings}
        />
      </div>

      {/* Hydrograph + activity */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader className="flex flex-row items-center justify-between space-y-0">
            <div>
              <CardTitle>Outfall hydrograph preview</CardTitle>
              <div className="mt-1 text-xs text-muted-foreground">
                Channel {project?.outfallChannel ?? "…"} · observed vs simulated
                (m³/s)
              </div>
            </div>
            <Tabs value={range} onValueChange={(v) => setRange(v as typeof range)}>
              <TabsList>
                {RANGES.map((r) => (
                  <TabsTrigger key={r.id} value={r.id}>
                    {r.id}
                  </TabsTrigger>
                ))}
              </TabsList>
            </Tabs>
          </CardHeader>
          <CardContent>
            <div className="h-[260px]">
              {hydro ? (
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={windowed}>
                    <CartesianGrid
                      strokeDasharray="3 3"
                      vertical={false}
                      stroke="hsl(var(--border))"
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
                      minTickGap={40}
                    />
                    <YAxis
                      tickLine={false}
                      axisLine={false}
                      tick={{
                        fontSize: 11,
                        fill: "hsl(var(--muted-foreground))",
                      }}
                      width={32}
                    />
                    <RTooltip
                      contentStyle={{
                        background: "hsl(var(--popover))",
                        border: "1px solid hsl(var(--border))",
                        borderRadius: 8,
                        fontSize: 12,
                      }}
                    />
                    <Line
                      type="monotone"
                      dataKey="observed"
                      stroke="hsl(var(--chart-2))"
                      strokeWidth={1.6}
                      dot={false}
                      name="Observed"
                    />
                    <Line
                      type="monotone"
                      dataKey="simulated"
                      stroke="hsl(var(--primary))"
                      strokeWidth={1.6}
                      dot={false}
                      name="Simulated"
                    />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <Skeleton className="h-full w-full" />
              )}
            </div>
            <div className="mt-3 flex items-center gap-4 text-xs text-muted-foreground">
              <LegendSwatch color="hsl(var(--chart-2))" label="Observed" />
              <LegendSwatch color="hsl(var(--primary))" label="Simulated" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Recent activity</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {activity ? (
              activity.map((a) => <ActivityRow key={a.id} a={a} />)
            ) : (
              <>
                <Skeleton className="h-12 w-full" />
                <Skeleton className="h-12 w-full" />
                <Skeleton className="h-12 w-full" />
              </>
            )}
          </CardContent>
        </Card>
      </div>

      {/* info bar */}
      <Card>
        <CardContent className="flex flex-wrap items-center gap-x-10 gap-y-4 p-6">
          <Stat label="Sub-basins" value={project?.subbasins} />
          <Stat label="HRUs" value={project?.hrus} />
          <Stat label="Channels" value={project?.channels} />
          <Stat label="Weather stations" value={project?.weatherStations} />
          <Stat label="Model version" value={project?.modelVersion} wide />
          <Stat label="Info findings" value={counts.info} />
        </CardContent>
      </Card>
    </div>
  );
}

function SeverityCard({
  title,
  count,
  icon: Icon,
  tone,
  sub,
  loading,
}: {
  title: string;
  count: number;
  icon: React.ComponentType<{ className?: string }>;
  tone: "destructive" | "warning" | "info";
  sub: string;
  loading?: boolean;
}) {
  const toneMap = {
    destructive: "bg-destructive/10 text-destructive",
    warning: "bg-amber-500/10 text-amber-600 dark:text-amber-400",
    info: "bg-sky-500/10 text-sky-600 dark:text-sky-400",
  } as const;
  return (
    <Card>
      <CardHeader className="flex flex-row items-start justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          {title}
        </CardTitle>
        <div
          className={cn(
            "flex h-8 w-8 items-center justify-center rounded-lg",
            toneMap[tone]
          )}
        >
          <Icon className="h-4 w-4" />
        </div>
      </CardHeader>
      <CardContent>
        <div className="text-3xl font-semibold tracking-tight">
          {loading ? <Skeleton className="h-9 w-10" /> : count}
        </div>
        <div className="mt-1 text-xs text-muted-foreground">{sub}</div>
      </CardContent>
    </Card>
  );
}

function LegendSwatch({ color, label }: { color: string; label: string }) {
  return (
    <span className="inline-flex items-center gap-2">
      <span
        className="inline-block h-2 w-4 rounded-full"
        style={{ backgroundColor: color }}
      />
      {label}
    </span>
  );
}

function Stat({
  label,
  value,
  wide,
}: {
  label: string;
  value: number | string | undefined;
  wide?: boolean;
}) {
  return (
    <div className={wide ? "min-w-[180px]" : ""}>
      <div className="text-xs uppercase tracking-wider text-muted-foreground">
        {label}
      </div>
      <div className="mt-1 text-lg font-semibold">
        {value ?? <Skeleton className="h-6 w-16" />}
      </div>
    </div>
  );
}

function ActivityRow({ a }: { a: ActivityEntry }) {
  const iconMap = {
    setup: Droplets,
    calibration: Activity,
    evaluation: TrendingUp,
    chat: Info,
  } as const;
  const Icon = iconMap[a.kind];
  return (
    <div className="flex items-start gap-3 rounded-lg px-2 py-1.5 hover:bg-accent">
      <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-primary/10 text-primary">
        <Icon className="h-3.5 w-3.5" />
      </div>
      <div className="min-w-0 flex-1">
        <div className="text-sm">{a.summary}</div>
        <div className="text-[11px] text-muted-foreground">
          {new Date(a.timestamp).toLocaleString("en-US", {
            month: "short",
            day: "numeric",
            hour: "numeric",
            minute: "2-digit",
          })}
        </div>
      </div>
    </div>
  );
}
