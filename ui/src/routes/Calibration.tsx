import { useEffect, useMemo, useState } from "react";
import { Check, ChevronDown, Play } from "lucide-react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ReferenceArea,
  ReferenceDot,
  ResponsiveContainer,
  Tooltip as RTooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import PageHeader from "@/components/PageHeader";
import KpiCard from "@/components/KpiCard";
import ChartTooltip from "@/components/ChartTooltip";
import { ProgressRing } from "@/components/ProgressRing";
import { MoriasiBadge } from "@/lib/moriasi";
import { getCalParameters, getIterations } from "@/lib/client";
import type { CalParameter, IterationResult } from "@/lib/types";
import { cn, formatNumber } from "@/lib/utils";

const TOOLS = [
  { id: "swatplus_toolbox", label: "SWAT+ Toolbox", note: "DDS / Morris" },
  { id: "swatrunr", label: "SWATrunR", note: "R package, FAST / DDS" },
  { id: "ipeat", label: "IPEAT+", note: "ParaSol / GLUE" },
];

const BUDGET_TOTAL = 50;

export default function Calibration() {
  const [params, setParams] = useState<CalParameter[] | null>(null);
  const [iters, setIters] = useState<IterationResult[] | null>(null);
  const [tool, setTool] = useState(TOOLS[0]);

  useEffect(() => {
    getCalParameters().then(setParams);
    getIterations().then(setIters);
  }, []);

  const latest = iters?.[iters.length - 1] ?? null;
  const baseline = iters && iters.length >= 5 ? iters[iters.length - 5] : null;

  const trends = useMemo(() => {
    if (!iters) return null;
    return {
      nse: iters.map((i) => i.nse),
      kge: iters.map((i) => i.kge),
      pbias: iters.map((i) => Math.abs(i.pbias)),
      r2: iters.map((i) => i.r2),
    };
  }, [iters]);

  const rings = useMemo(() => {
    if (!iters || !latest)
      return { budget: 0, convergence: 0, stability: 0 };
    const budget = Math.min(100, (iters.length / BUDGET_TOTAL) * 100);
    const last5 = iters.slice(-5).map((i) => i.nse);
    const mean = last5.reduce((a, b) => a + b, 0) / last5.length;
    const variance =
      last5.reduce((a, b) => a + (b - mean) * (b - mean), 0) / last5.length;
    const std = Math.sqrt(variance);
    const stability = Math.max(0, Math.min(100, 100 - std * 400));
    const convergence = Math.max(0, Math.min(100, latest.nse * 100 + 5));
    return { budget, convergence, stability };
  }, [iters, latest]);

  return (
    <div className="mx-auto max-w-[1280px] space-y-6">
      <PageHeader
        overline="Module 2 · Calibration"
        title="Calibration"
        desc="Configure the parameter set, hand it to the tool of choice, and let the assistant interpret iterations as they land."
        status={
          iters ? (
            <Badge variant="warning" className="gap-1.5">
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-amber-500" />
              running · iter {iters.length}
            </Badge>
          ) : null
        }
        actions={
          <div className="flex items-center gap-2">
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" size="sm" className="gap-2">
                  {tool.label}
                  <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-60">
                <DropdownMenuLabel>Calibration tool</DropdownMenuLabel>
                <DropdownMenuSeparator />
                {TOOLS.map((t) => (
                  <DropdownMenuItem
                    key={t.id}
                    onClick={() => setTool(t)}
                    className="flex flex-col items-start gap-0.5"
                  >
                    <div className="flex w-full items-center gap-2">
                      <span className="font-medium">{t.label}</span>
                      {tool.id === t.id && (
                        <Check className="ml-auto h-3.5 w-3.5" />
                      )}
                    </div>
                    <span className="text-[11px] text-muted-foreground">
                      {t.note}
                    </span>
                  </DropdownMenuItem>
                ))}
              </DropdownMenuContent>
            </DropdownMenu>
            <Button size="sm" className="gap-1.5">
              <Play className="h-3.5 w-3.5" />
              Run next iteration
            </Button>
          </div>
        }
      />

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        {latest && baseline && trends ? (
          <>
            <KpiCard
              label="NSE"
              value={formatNumber(latest.nse, 3)}
              delta={Number((latest.nse - baseline.nse).toFixed(3))}
              trend={trends.nse}
              trendColor="hsl(var(--primary))"
              tag={<MoriasiBadge value={latest.nse} kind="nse" />}
              sub={`vs iter ${baseline.iteration}`}
            />
            <KpiCard
              label="KGE"
              value={formatNumber(latest.kge, 3)}
              delta={Number((latest.kge - baseline.kge).toFixed(3))}
              trend={trends.kge}
              trendColor="hsl(var(--chart-2))"
              tag={<MoriasiBadge value={latest.kge} kind="kge" />}
              sub={`vs iter ${baseline.iteration}`}
            />
            <KpiCard
              label="PBIAS"
              value={`${formatNumber(latest.pbias, 1)}%`}
              delta={Number(
                (Math.abs(latest.pbias) - Math.abs(baseline.pbias)).toFixed(2)
              )}
              deltaSuffix="pp"
              deltaInverted
              trend={trends.pbias}
              trendColor="hsl(var(--chart-4))"
              tag={<MoriasiBadge value={latest.pbias} kind="pbias" />}
              sub={`vs iter ${baseline.iteration}`}
            />
            <KpiCard
              label="R²"
              value={formatNumber(latest.r2, 3)}
              delta={Number((latest.r2 - baseline.r2).toFixed(3))}
              trend={trends.r2}
              trendColor="hsl(var(--chart-3))"
              tag={<MoriasiBadge value={latest.r2} kind="r2" />}
              sub={`vs iter ${baseline.iteration}`}
            />
          </>
        ) : (
          Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-[130px] w-full rounded-xl" />
          ))
        )}
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-5">
        <Card className="shadow-card lg:col-span-3">
          <CardHeader className="pb-2">
            <CardTitle className="text-[14px] font-semibold">
              NSE convergence
            </CardTitle>
            <div className="text-[11.5px] text-muted-foreground">
              {iters?.length ?? 0} iterations · Moriasi bands shown as
              background
            </div>
          </CardHeader>
          <CardContent>
            <div className="h-[260px]">
              {iters && latest ? (
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart
                    data={iters}
                    margin={{ top: 8, right: 12, bottom: 4, left: 0 }}
                  >
                    <defs>
                      <linearGradient id="nseFill" x1="0" y1="0" x2="0" y2="1">
                        <stop
                          offset="0%"
                          stopColor="hsl(var(--primary))"
                          stopOpacity={0.28}
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
                      dataKey="iteration"
                      tickLine={false}
                      axisLine={false}
                      tick={{
                        fontSize: 11,
                        fill: "hsl(var(--muted-foreground))",
                      }}
                    />
                    <YAxis
                      domain={[0, 1]}
                      tickLine={false}
                      axisLine={false}
                      tick={{
                        fontSize: 11,
                        fill: "hsl(var(--muted-foreground))",
                      }}
                      width={32}
                    />
                    <ReferenceArea
                      y1={0.75}
                      y2={1}
                      fill="hsl(var(--success))"
                      fillOpacity={0.08}
                      stroke="none"
                    />
                    <ReferenceArea
                      y1={0.5}
                      y2={0.75}
                      fill="hsl(var(--warning))"
                      fillOpacity={0.08}
                      stroke="none"
                    />
                    <RTooltip
                      content={
                        <ChartTooltip
                          formatter={(v) => formatNumber(v, 3)}
                          labelFormatter={(l) => `iter ${l}`}
                        />
                      }
                    />
                    <Area
                      type="monotone"
                      dataKey="nse"
                      stroke="hsl(var(--primary))"
                      strokeWidth={1.6}
                      fill="url(#nseFill)"
                      name="NSE"
                      isAnimationActive={false}
                    />
                    <ReferenceDot
                      x={latest.iteration}
                      y={latest.nse}
                      r={4}
                      fill="hsl(var(--primary))"
                      stroke="hsl(var(--background))"
                      strokeWidth={2}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              ) : (
                <Skeleton className="h-full w-full" />
              )}
            </div>
            <div className="mt-3 flex flex-wrap items-center gap-4 text-[11px] text-muted-foreground">
              <span className="inline-flex items-center gap-1.5">
                <span className="h-2 w-3 rounded-sm bg-success/30" /> good (&gt;
                0.75)
              </span>
              <span className="inline-flex items-center gap-1.5">
                <span className="h-2 w-3 rounded-sm bg-warning/30" />{" "}
                satisfactory (≥ 0.5)
              </span>
              <span className="inline-flex items-center gap-1.5">
                <span className="h-[2px] w-3 rounded-full bg-primary" /> NSE
              </span>
            </div>
          </CardContent>
        </Card>

        <Card className="shadow-card lg:col-span-2">
          <CardHeader className="pb-2">
            <CardTitle className="text-[14px] font-semibold">
              Calibration budget
            </CardTitle>
            <div className="text-[11.5px] text-muted-foreground">
              Token + iteration budget against convergence & stability
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <BudgetRow
              label="Budget used"
              pct={rings.budget}
              sub={`${iters?.length ?? 0} / ${BUDGET_TOTAL} iterations`}
              color="hsl(var(--primary))"
            />
            <BudgetRow
              label="Convergence"
              pct={rings.convergence}
              sub="NSE-indexed progress"
              color="hsl(var(--chart-2))"
            />
            <BudgetRow
              label="Stability"
              pct={rings.stability}
              sub="σ of last 5 NSE values"
              color="hsl(var(--chart-4))"
            />
          </CardContent>
        </Card>
      </div>

      <Card className="shadow-card">
        <CardHeader className="pb-2">
          <CardTitle className="text-[14px] font-semibold">
            Parameter set
          </CardTitle>
          <div className="text-[11.5px] text-muted-foreground">
            {params?.length ?? 0} parameters · sensitivity from the last run
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow className="h-9">
                <TableHead className="text-[10.5px] uppercase tracking-[0.1em]">
                  Parameter
                </TableHead>
                <TableHead className="text-[10.5px] uppercase tracking-[0.1em]">
                  Change
                </TableHead>
                <TableHead className="text-[10.5px] uppercase tracking-[0.1em]">
                  Bounds
                </TableHead>
                <TableHead className="text-[10.5px] uppercase tracking-[0.1em]">
                  Initial
                </TableHead>
                <TableHead className="text-[10.5px] uppercase tracking-[0.1em]">
                  Sensitivity
                </TableHead>
                <TableHead className="text-right text-[10.5px] uppercase tracking-[0.1em]">
                  Action
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {params
                ? params.map((p) => <ParamRow key={p.name} p={p} />)
                : Array.from({ length: 5 }).map((_, i) => (
                    <TableRow key={i} className="h-11">
                      <TableCell colSpan={6}>
                        <Skeleton className="h-5 w-full" />
                      </TableCell>
                    </TableRow>
                  ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}

function BudgetRow({
  label,
  pct,
  sub,
  color,
}: {
  label: string;
  pct: number;
  sub: string;
  color: string;
}) {
  return (
    <div className="flex items-center gap-4">
      <ProgressRing value={pct} size={56} color={color} />
      <div className="min-w-0 flex-1">
        <div className="flex items-baseline justify-between gap-2">
          <span className="text-[13px] font-medium">{label}</span>
          <span className="font-mono text-[12px] tabular-nums text-muted-foreground">
            {Math.round(pct)}%
          </span>
        </div>
        <div className="mt-0.5 text-[11.5px] text-muted-foreground">{sub}</div>
      </div>
    </div>
  );
}

function ParamRow({ p }: { p: CalParameter }) {
  const sensPct = Math.max(0, Math.min(100, p.sensitivity * 100));
  return (
    <TableRow className="h-11">
      <TableCell>
        <div className="font-mono text-[12px] font-medium">{p.name}</div>
        <div className="text-[11px] text-muted-foreground">{p.description}</div>
      </TableCell>
      <TableCell>
        <Badge variant="outline" className="font-mono text-[10px]">
          {p.change}
        </Badge>
      </TableCell>
      <TableCell className="font-mono text-[11.5px] tabular-nums">
        [{p.lowerBound}, {p.upperBound}]
      </TableCell>
      <TableCell className="font-mono text-[11.5px] tabular-nums">
        {p.initial}
      </TableCell>
      <TableCell>
        <div className="flex items-center gap-2">
          <div className="relative h-1.5 w-24 overflow-hidden rounded-full bg-muted">
            <div
              className={cn(
                "absolute inset-y-0 left-0 rounded-full",
                sensPct > 75
                  ? "bg-primary"
                  : sensPct > 50
                    ? "bg-primary/70"
                    : "bg-primary/40"
              )}
              style={{ width: `${sensPct}%` }}
            />
            <span className="absolute left-[50%] top-0 h-full w-px bg-border" />
            <span className="absolute left-[75%] top-0 h-full w-px bg-border" />
          </div>
          <span className="w-10 font-mono text-[11px] tabular-nums text-muted-foreground">
            {formatNumber(p.sensitivity, 2)}
          </span>
        </div>
      </TableCell>
      <TableCell className="text-right">
        <Button variant="ghost" size="sm" className="h-7 text-[12px]">
          Edit
        </Button>
      </TableCell>
    </TableRow>
  );
}
