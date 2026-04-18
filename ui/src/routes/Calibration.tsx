import * as React from "react";
import { useEffect, useState } from "react";
import { Check, ChevronDown, Play } from "lucide-react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip as RTooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { getCalParameters, getIterations } from "@/lib/mockApi";
import type { CalParameter, IterationResult } from "@/lib/types";
import { cn, formatNumber } from "@/lib/utils";

const TOOLS = [
  { id: "swatplus_toolbox", label: "SWAT+ Toolbox", note: "DDS / Morris" },
  { id: "swatrunr", label: "SWATrunR", note: "R package, FAST / DDS" },
  { id: "ipeat", label: "IPEAT+", note: "ParaSol / GLUE" },
];

export default function Calibration() {
  const [params, setParams] = useState<CalParameter[] | null>(null);
  const [iters, setIters] = useState<IterationResult[] | null>(null);
  const [tool, setTool] = useState(TOOLS[0]);

  useEffect(() => {
    getCalParameters().then(setParams);
    getIterations().then(setIters);
  }, []);

  const latest = iters?.[iters.length - 1];

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <div className="text-sm text-muted-foreground">Module 2</div>
          <h2 className="text-2xl font-semibold tracking-tight">Calibration</h2>
          <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
            Configure your parameter set, hand it to the tool of your choice,
            and let the assistant interpret iteration results as they land.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="sm" className="gap-2">
                Tool · {tool.label}
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
                    {tool.id === t.id && <Check className="ml-auto h-3.5 w-3.5" />}
                  </div>
                  <span className="text-[11px] text-muted-foreground">
                    {t.note}
                  </span>
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>
          <Button size="sm" className="gap-2">
            <Play className="h-3.5 w-3.5" />
            Run next iteration
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
        <MetricBadge label="Current iteration" value={latest?.iteration ?? "…"} />
        <MetricBadge
          label="NSE"
          value={latest ? formatNumber(latest.nse, 3) : "…"}
          hint={latest ? moriasiTag(latest.nse, "nse") : null}
        />
        <MetricBadge
          label="KGE"
          value={latest ? formatNumber(latest.kge, 3) : "…"}
          hint={latest ? moriasiTag(latest.kge, "kge") : null}
        />
        <MetricBadge
          label="PBIAS"
          value={latest ? `${formatNumber(latest.pbias, 1)}%` : "…"}
          hint={latest ? moriasiTag(latest.pbias, "pbias") : null}
        />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-5">
        <Card className="lg:col-span-3">
          <CardHeader>
            <CardTitle>Iteration history</CardTitle>
            <div className="text-xs text-muted-foreground">
              NSE · KGE · PBIAS over {iters?.length ?? 0} iterations
            </div>
          </CardHeader>
          <CardContent>
            <div className="h-[280px]">
              {iters ? (
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={iters}>
                    <CartesianGrid
                      strokeDasharray="3 3"
                      vertical={false}
                      stroke="hsl(var(--border))"
                    />
                    <XAxis
                      dataKey="iteration"
                      tickLine={false}
                      axisLine={false}
                      tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
                    />
                    <YAxis
                      yAxisId="left"
                      tickLine={false}
                      axisLine={false}
                      tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
                      domain={[0, 1]}
                      width={36}
                    />
                    <YAxis
                      yAxisId="right"
                      orientation="right"
                      tickLine={false}
                      axisLine={false}
                      tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
                      width={36}
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
                      yAxisId="left"
                      type="monotone"
                      dataKey="nse"
                      stroke="hsl(var(--primary))"
                      strokeWidth={2}
                      dot={false}
                      name="NSE"
                    />
                    <Line
                      yAxisId="left"
                      type="monotone"
                      dataKey="kge"
                      stroke="hsl(var(--chart-2))"
                      strokeWidth={2}
                      dot={false}
                      name="KGE"
                    />
                    <Line
                      yAxisId="right"
                      type="monotone"
                      dataKey="pbias"
                      stroke="hsl(var(--chart-4))"
                      strokeWidth={1.5}
                      strokeDasharray="4 3"
                      dot={false}
                      name="PBIAS"
                    />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <Skeleton className="h-full w-full" />
              )}
            </div>
            <div className="mt-3 flex items-center gap-4 text-xs text-muted-foreground">
              <LegendSwatch color="hsl(var(--primary))" label="NSE" />
              <LegendSwatch color="hsl(var(--chart-2))" label="KGE" />
              <LegendSwatch color="hsl(var(--chart-4))" label="PBIAS" />
            </div>
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Next-iteration suggestion</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 text-sm">
            <div className="rounded-lg border border-dashed bg-primary/5 p-4">
              <div className="text-[11px] font-medium uppercase tracking-wider text-primary">
                Assistant read
              </div>
              <p className="mt-1 text-sm leading-relaxed">
                Peaks under-predicted, baseflow over-predicted. ALPHA_BF pinned
                at bound.
              </p>
              <ul className="mt-3 space-y-1 text-xs">
                <li>
                  <strong>Widen</strong> CN2 to [-15%, +10%]
                </li>
                <li>
                  <strong>Widen</strong> ALPHA_BF to [0.01, 0.8]
                </li>
                <li>
                  <strong>Add</strong> GW_DELAY [0, 450] days
                </li>
              </ul>
            </div>
            <Button variant="outline" size="sm" className="w-full">
              Apply to next iteration
            </Button>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Parameter set</CardTitle>
          <div className="text-xs text-muted-foreground">
            8 parameters · sensitivity computed from iterations 1–18
          </div>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Parameter</TableHead>
                <TableHead>Change type</TableHead>
                <TableHead>Bounds</TableHead>
                <TableHead>Initial</TableHead>
                <TableHead>Sensitivity</TableHead>
                <TableHead className="text-right">Action</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {params
                ? params.map((p) => <ParamRow key={p.name} p={p} />)
                : Array.from({ length: 5 }).map((_, i) => (
                    <TableRow key={i}>
                      <TableCell colSpan={6}>
                        <Skeleton className="h-6 w-full" />
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

function ParamRow({ p }: { p: CalParameter }) {
  return (
    <TableRow>
      <TableCell>
        <div className="font-medium">{p.name}</div>
        <div className="text-[11px] text-muted-foreground">{p.description}</div>
      </TableCell>
      <TableCell>
        <Badge variant="outline" className="font-mono text-[10px]">
          {p.change}
        </Badge>
      </TableCell>
      <TableCell className="font-mono text-xs">
        [{p.lowerBound}, {p.upperBound}]
      </TableCell>
      <TableCell className="font-mono text-xs">{p.initial}</TableCell>
      <TableCell>
        <div className="flex items-center gap-2">
          <Progress value={p.sensitivity * 100} className="w-24" />
          <span className="w-10 text-right text-xs text-muted-foreground">
            {formatNumber(p.sensitivity, 2)}
          </span>
        </div>
      </TableCell>
      <TableCell className="text-right">
        <Button variant="ghost" size="sm">
          Edit
        </Button>
      </TableCell>
    </TableRow>
  );
}

function MetricBadge({
  label,
  value,
  hint,
}: {
  label: string;
  value: string | number;
  hint?: React.ReactNode;
}) {
  return (
    <Card>
      <CardContent className="p-5">
        <div className="text-xs uppercase tracking-wider text-muted-foreground">
          {label}
        </div>
        <div className="mt-1 text-2xl font-semibold tracking-tight">{value}</div>
        {hint && <div className="mt-2">{hint}</div>}
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

function moriasiTag(
  value: number,
  kind: "nse" | "kge" | "pbias"
): React.ReactElement {
  // Moriasi 2007 daily streamflow thresholds
  let cls: "good" | "satisfactory" | "unacceptable";
  if (kind === "pbias") {
    const a = Math.abs(value);
    cls = a < 10 ? "good" : a < 15 ? "satisfactory" : "unacceptable";
  } else {
    cls = value > 0.75 ? "good" : value >= 0.5 ? "satisfactory" : "unacceptable";
  }
  const variant =
    cls === "good" ? "success" : cls === "satisfactory" ? "warning" : "destructive";
  const label =
    cls === "good" ? "Good" : cls === "satisfactory" ? "Satisfactory" : "Unacceptable";
  return (
    <Badge variant={variant} className={cn("text-[10px]")}>
      Moriasi · {label}
    </Badge>
  );
}
