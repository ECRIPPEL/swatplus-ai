import { useEffect, useState } from "react";
import { FileText, Sparkles } from "lucide-react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip as RTooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { ScrollArea } from "@/components/ui/scroll-area";
import { getHydrograph, getIterations } from "@/lib/mockApi";
import type { HydrographPoint, IterationResult } from "@/lib/types";
import { cn, formatNumber } from "@/lib/utils";

export default function Evaluation() {
  const [hydro, setHydro] = useState<HydrographPoint[] | null>(null);
  const [iters, setIters] = useState<IterationResult[] | null>(null);

  useEffect(() => {
    getHydrograph().then(setHydro);
    getIterations().then(setIters);
  }, []);

  const latest = iters?.[iters.length - 1];

  const metrics = latest
    ? [
        { label: "NSE", value: latest.nse, kind: "nse" as const, fmt: (n: number) => formatNumber(n, 3) },
        { label: "KGE", value: latest.kge, kind: "kge" as const, fmt: (n: number) => formatNumber(n, 3) },
        {
          label: "PBIAS",
          value: latest.pbias,
          kind: "pbias" as const,
          fmt: (n: number) => `${formatNumber(n, 1)}%`,
        },
        { label: "R²", value: latest.r2, kind: "r2" as const, fmt: (n: number) => formatNumber(n, 3) },
      ]
    : null;

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <div className="text-sm text-muted-foreground">Module 3</div>
          <h2 className="text-2xl font-semibold tracking-tight">Evaluation</h2>
          <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
            Metrics classified against Moriasi 2007 guidance for daily
            streamflow. Residuals grounded against literature for similar
            basins.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Dialog>
            <DialogTrigger asChild>
              <Button size="sm" variant="outline" className="gap-2">
                <FileText className="h-3.5 w-3.5" />
                Draft manuscript paragraph
              </Button>
            </DialogTrigger>
            <DraftDialog />
          </Dialog>
          <Button size="sm" className="gap-2">
            <Sparkles className="h-3.5 w-3.5" />
            Re-evaluate
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {metrics
          ? metrics.map((m) => <MetricCard key={m.label} {...m} />)
          : Array.from({ length: 4 }).map((_, i) => (
              <Card key={i}>
                <CardContent className="space-y-3 p-5">
                  <Skeleton className="h-3 w-14" />
                  <Skeleton className="h-8 w-20" />
                  <Skeleton className="h-5 w-24" />
                </CardContent>
              </Card>
            ))}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Observed vs simulated — outfall cha033</CardTitle>
          <div className="text-xs text-muted-foreground">
            Daily discharge (m³/s) · 2013 water year
          </div>
        </CardHeader>
        <CardContent>
          <div className="h-[380px]">
            {hydro ? (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={hydro}>
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
                    tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
                    minTickGap={48}
                  />
                  <YAxis
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
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Residual analysis</CardTitle>
          <div className="text-xs text-muted-foreground">
            Where the model is and isn't performing
          </div>
        </CardHeader>
        <CardContent className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <InsightCard
            title="Peak under-prediction"
            value="-19%"
            sub="Mean relative error on top 10 storm events"
            tone="destructive"
          />
          <InsightCard
            title="Baseflow over-prediction"
            value="+12%"
            sub="Recession-period bias (July–September)"
            tone="warning"
          />
          <InsightCard
            title="Timing error"
            value="+1.2 d"
            sub="Mean peak-arrival lag"
            tone="info"
          />
        </CardContent>
      </Card>
    </div>
  );
}

function MetricCard({
  label,
  value,
  kind,
  fmt,
}: {
  label: string;
  value: number;
  kind: "nse" | "kge" | "pbias" | "r2";
  fmt: (n: number) => string;
}) {
  const cls = classify(value, kind);
  const variant =
    cls === "good"
      ? "success"
      : cls === "satisfactory"
        ? "warning"
        : "destructive";
  const clsLabel =
    cls === "good"
      ? "Good"
      : cls === "satisfactory"
        ? "Satisfactory"
        : "Unacceptable";
  return (
    <Card>
      <CardContent className="p-5">
        <div className="text-xs uppercase tracking-wider text-muted-foreground">
          {label}
        </div>
        <div className="mt-1 text-3xl font-semibold tracking-tight">
          {fmt(value)}
        </div>
        <Badge variant={variant} className="mt-2 text-[10px]">
          Moriasi · {clsLabel}
        </Badge>
      </CardContent>
    </Card>
  );
}

function InsightCard({
  title,
  value,
  sub,
  tone,
}: {
  title: string;
  value: string;
  sub: string;
  tone: "destructive" | "warning" | "info";
}) {
  const toneMap = {
    destructive: "text-destructive",
    warning: "text-amber-600 dark:text-amber-400",
    info: "text-sky-600 dark:text-sky-400",
  } as const;
  return (
    <div className="rounded-xl border p-4">
      <div className="text-xs text-muted-foreground">{title}</div>
      <div className={cn("mt-2 text-2xl font-semibold", toneMap[tone])}>
        {value}
      </div>
      <div className="mt-1 text-xs text-muted-foreground">{sub}</div>
    </div>
  );
}

function classify(
  value: number,
  kind: "nse" | "kge" | "pbias" | "r2"
): "good" | "satisfactory" | "unacceptable" {
  if (kind === "pbias") {
    const a = Math.abs(value);
    return a < 10 ? "good" : a < 15 ? "satisfactory" : "unacceptable";
  }
  return value > 0.75
    ? "good"
    : value >= 0.5
      ? "satisfactory"
      : "unacceptable";
}

function DraftDialog() {
  return (
    <DialogContent className="max-w-2xl">
      <DialogHeader>
        <DialogTitle>Draft results-section paragraph</DialogTitle>
        <DialogDescription>
          Generated from the current evaluation metrics, grounded in the
          Literature DB.
        </DialogDescription>
      </DialogHeader>
      <ScrollArea className="max-h-[400px] pr-4">
        <div className="space-y-3 text-sm leading-relaxed">
          <p>
            The model was calibrated against daily discharge at the basin outlet
            (cha033) for the period 2011–2016 and validated over 2017–2019. The
            final calibration achieved NSE = 0.58, KGE = 0.54, and PBIAS = −8.3%
            (Moriasi et al. 2007 classification: <em>satisfactory</em> for NSE
            and <em>good</em> for PBIAS).
          </p>
          <p>
            Residual analysis indicates systematic under-prediction of storm
            peaks (mean peak residual: −19%), consistent with reports for humid
            subtropical clay-dominated basins when CN2 is tightly bounded
            (Arnold et al. 2012). Baseflow separation yields a simulated
            baseflow index of 0.71 versus an observed 0.58; further calibration
            iterations relaxing ALPHA_BF and GW_DELAY are expected to close this
            gap.
          </p>
          <div className="flex flex-wrap gap-2 pt-2">
            <Badge variant="outline">Moriasi 2007</Badge>
            <Badge variant="outline">Arnold 2012</Badge>
            <Badge variant="outline">White 2014</Badge>
          </div>
        </div>
      </ScrollArea>
      <div className="flex items-center justify-end gap-2 pt-2">
        <Button variant="outline" size="sm">
          Copy to clipboard
        </Button>
        <Button size="sm">Export .docx</Button>
      </div>
    </DialogContent>
  );
}
