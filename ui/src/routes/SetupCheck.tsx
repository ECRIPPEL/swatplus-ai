import * as React from "react";
import { useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  ExternalLink,
  Info,
  Sparkles,
  X,
  XCircle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { getFindings } from "@/lib/mockApi";
import type { Finding, Severity } from "@/lib/types";
import { cn } from "@/lib/utils";

const SEVERITY_META: Record<
  Severity,
  {
    label: string;
    badge: "destructive" | "warning" | "info";
    icon: React.ComponentType<{ className?: string }>;
    dotClass: string;
  }
> = {
  error: {
    label: "Error",
    badge: "destructive",
    icon: XCircle,
    dotClass: "bg-destructive",
  },
  warning: {
    label: "Warning",
    badge: "warning",
    icon: AlertTriangle,
    dotClass: "bg-amber-500",
  },
  info: {
    label: "Info",
    badge: "info",
    icon: Info,
    dotClass: "bg-sky-500",
  },
};

export default function SetupCheck() {
  const [findings, setFindings] = useState<Finding[] | null>(null);
  const [selected, setSelected] = useState<Finding | null>(null);
  const [filter, setFilter] = useState<"all" | Severity>("all");

  useEffect(() => {
    getFindings().then((f) => {
      setFindings(f);
      setSelected(f[0] ?? null);
    });
  }, []);

  const filtered = useMemo(() => {
    if (!findings) return null;
    return filter === "all" ? findings : findings.filter((f) => f.severity === filter);
  }, [findings, filter]);

  const counts = useMemo(() => {
    if (!findings) return { error: 0, warning: 0, info: 0 };
    return findings.reduce(
      (acc, f) => ({ ...acc, [f.severity]: acc[f.severity] + 1 }),
      { error: 0, warning: 0, info: 0 }
    );
  }, [findings]);

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <div className="text-sm text-muted-foreground">Module 1</div>
          <h2 className="text-2xl font-semibold tracking-tight">Setup Check</h2>
          <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
            Deterministic diagnostics over the TxtInOut project. Click any
            finding to open an LLM-grounded explanation with citations.
          </p>
        </div>
        <Button size="sm" className="gap-2">
          <Sparkles className="h-3.5 w-3.5" />
          Re-run check
        </Button>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <SummaryCard
          label="Errors"
          count={counts.error}
          icon={XCircle}
          tone="destructive"
        />
        <SummaryCard
          label="Warnings"
          count={counts.warning}
          icon={AlertTriangle}
          tone="warning"
        />
        <SummaryCard label="Info" count={counts.info} icon={Info} tone="info" />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-5">
        <Card className="lg:col-span-3">
          <div className="border-b px-6 pt-4">
            <Tabs value={filter} onValueChange={(v) => setFilter(v as typeof filter)}>
              <TabsList>
                <TabsTrigger value="all">All ({findings?.length ?? 0})</TabsTrigger>
                <TabsTrigger value="error">Errors ({counts.error})</TabsTrigger>
                <TabsTrigger value="warning">Warnings ({counts.warning})</TabsTrigger>
                <TabsTrigger value="info">Info ({counts.info})</TabsTrigger>
              </TabsList>
              <TabsContent value={filter} className="mt-0" />
            </Tabs>
          </div>
          <CardContent className="p-0">
            <ScrollArea className="h-[560px]">
              <div className="divide-y">
                {filtered
                  ? filtered.map((f) => (
                      <FindingRow
                        key={f.id}
                        f={f}
                        selected={selected?.id === f.id}
                        onClick={() => setSelected(f)}
                      />
                    ))
                  : Array.from({ length: 6 }).map((_, i) => (
                      <div key={i} className="p-4">
                        <Skeleton className="h-14 w-full" />
                      </div>
                    ))}
              </div>
            </ScrollArea>
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardContent className="p-0">
            {selected ? (
              <FindingDetail finding={selected} onClose={() => setSelected(null)} />
            ) : (
              <div className="flex h-[600px] items-center justify-center p-8 text-center text-sm text-muted-foreground">
                Select a finding to see the explanation.
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function SummaryCard({
  label,
  count,
  icon: Icon,
  tone,
}: {
  label: string;
  count: number;
  icon: React.ComponentType<{ className?: string }>;
  tone: "destructive" | "warning" | "info";
}) {
  const toneMap = {
    destructive: "bg-destructive/10 text-destructive",
    warning: "bg-amber-500/10 text-amber-600 dark:text-amber-400",
    info: "bg-sky-500/10 text-sky-600 dark:text-sky-400",
  } as const;
  return (
    <Card>
      <CardContent className="flex items-center gap-4 p-5">
        <div
          className={cn(
            "flex h-10 w-10 items-center justify-center rounded-lg",
            toneMap[tone]
          )}
        >
          <Icon className="h-5 w-5" />
        </div>
        <div>
          <div className="text-2xl font-semibold tracking-tight">{count}</div>
          <div className="text-xs text-muted-foreground">{label}</div>
        </div>
      </CardContent>
    </Card>
  );
}

function FindingRow({
  f,
  selected,
  onClick,
}: {
  f: Finding;
  selected: boolean;
  onClick: () => void;
}) {
  const meta = SEVERITY_META[f.severity];
  const Icon = meta.icon;
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "flex w-full items-start gap-3 px-5 py-4 text-left transition-colors hover:bg-accent/60",
        selected && "bg-primary/5"
      )}
    >
      <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center">
        <Icon
          className={cn(
            "h-4 w-4",
            f.severity === "error" && "text-destructive",
            f.severity === "warning" && "text-amber-500",
            f.severity === "info" && "text-sky-500"
          )}
        />
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="truncate text-sm font-medium">{f.title}</span>
        </div>
        <div className="mt-0.5 truncate text-xs text-muted-foreground">
          {f.location}
        </div>
        <div className="mt-2 flex items-center gap-2">
          <Badge variant={meta.badge}>{meta.label}</Badge>
          <span className="text-[11px] text-muted-foreground">
            rule · {f.ruleId}
          </span>
        </div>
      </div>
    </button>
  );
}

function FindingDetail({
  finding,
  onClose,
}: {
  finding: Finding;
  onClose: () => void;
}) {
  const meta = SEVERITY_META[finding.severity];
  const Icon = meta.icon;
  return (
    <div className="flex h-[600px] flex-col">
      <div className="flex items-start justify-between border-b p-5">
        <div className="flex items-start gap-3">
          <div
            className={cn(
              "flex h-9 w-9 shrink-0 items-center justify-center rounded-lg",
              finding.severity === "error" && "bg-destructive/10 text-destructive",
              finding.severity === "warning" &&
                "bg-amber-500/10 text-amber-600 dark:text-amber-400",
              finding.severity === "info" &&
                "bg-sky-500/10 text-sky-600 dark:text-sky-400"
            )}
          >
            <Icon className="h-4 w-4" />
          </div>
          <div>
            <Badge variant={meta.badge} className="mb-1">
              {meta.label}
            </Badge>
            <h3 className="text-sm font-semibold leading-snug">{finding.title}</h3>
            <div className="mt-1 text-xs text-muted-foreground">
              {finding.location}
            </div>
          </div>
        </div>
        <Button variant="ghost" size="icon" onClick={onClose} aria-label="Close">
          <X className="h-4 w-4" />
        </Button>
      </div>

      <ScrollArea className="flex-1">
        <div className="space-y-5 p-5 text-sm">
          <DetailBlock label="Evidence">
            <pre className="whitespace-pre-wrap rounded-md bg-muted p-3 text-xs">
              {finding.evidence}
            </pre>
          </DetailBlock>

          <DetailBlock label="Why it matters">
            <p className="text-sm leading-relaxed text-foreground">
              {finding.explanation}
            </p>
          </DetailBlock>

          <DetailBlock label="Suggested action">
            <p className="text-sm leading-relaxed text-foreground">
              {finding.suggestion}
            </p>
          </DetailBlock>

          {finding.citations.length > 0 && (
            <>
              <Separator />
              <DetailBlock label="Citations">
                <div className="flex flex-wrap gap-2">
                  {finding.citations.map((c) => (
                    <span
                      key={c.id}
                      className="inline-flex items-center gap-1 rounded-full border bg-background px-2.5 py-1 text-[11px]"
                      title={c.source}
                    >
                      <ExternalLink className="h-3 w-3 text-muted-foreground" />
                      {c.label}
                    </span>
                  ))}
                </div>
              </DetailBlock>
            </>
          )}

          <div className="flex items-center gap-2 rounded-lg border border-dashed bg-muted/30 p-3 text-xs text-muted-foreground">
            <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />
            Grounded in SWAT+ I/O spec and the Literature DB. Every claim is
            traceable to a citation above.
          </div>
        </div>
      </ScrollArea>
    </div>
  );
}

function DetailBlock({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <div className="mb-2 text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
        {label}
      </div>
      {children}
    </div>
  );
}
