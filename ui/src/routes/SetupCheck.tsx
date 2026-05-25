import * as React from "react";
import { useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  Info,
  ListFilter,
  Sparkles,
  X,
  XCircle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { ScrollArea } from "@/components/ui/scroll-area";
import PageHeader from "@/components/PageHeader";
import CitePop from "@/components/CitePop";
import { getFindings } from "@/lib/client";
import type { Finding, Severity } from "@/lib/types";
import { cn } from "@/lib/utils";

type FilterKey = "all" | Severity;

const SEVERITY_META: Record<
  Severity,
  {
    label: string;
    badgeVariant: "destructive" | "warning" | "info";
    icon: React.ComponentType<{ className?: string }>;
    railClass: string;
    iconClass: string;
    tintClass: string;
  }
> = {
  error: {
    label: "Error",
    badgeVariant: "destructive",
    icon: XCircle,
    railClass: "bg-red-500",
    iconClass: "text-red-500",
    tintClass: "bg-red-500/10 text-red-600 dark:text-red-300",
  },
  warning: {
    label: "Warning",
    badgeVariant: "warning",
    icon: AlertTriangle,
    railClass: "bg-amber-500",
    iconClass: "text-amber-500",
    tintClass: "bg-amber-500/10 text-amber-600 dark:text-amber-300",
  },
  info: {
    label: "Info",
    badgeVariant: "info",
    icon: Info,
    railClass: "bg-sky-500",
    iconClass: "text-sky-500",
    tintClass: "bg-sky-500/10 text-sky-600 dark:text-sky-300",
  },
};

export default function SetupCheck() {
  const [findings, setFindings] = useState<Finding[] | null>(null);
  const [selected, setSelected] = useState<Finding | null>(null);
  const [filter, setFilter] = useState<FilterKey>("all");

  useEffect(() => {
    getFindings().then((f) => {
      setFindings(f);
      setSelected(f[0] ?? null);
    });
  }, []);

  const counts = useMemo(() => {
    if (!findings) return { error: 0, warning: 0, info: 0 };
    return findings.reduce(
      (acc, f) => ({ ...acc, [f.severity]: acc[f.severity] + 1 }),
      { error: 0, warning: 0, info: 0 }
    );
  }, [findings]);

  const filtered = useMemo(() => {
    if (!findings) return null;
    return filter === "all"
      ? findings
      : findings.filter((f) => f.severity === filter);
  }, [findings, filter]);

  const ready = findings !== null && counts.error === 0;

  return (
    <div className="mx-auto max-w-[1280px] space-y-6">
      <PageHeader
        overline="Module 1 · Diagnostics"
        title="Setup Check"
        desc="Deterministic rule engine over the TxtInOut project. Every finding is grounded against the SWAT+ I/O spec and the Literature DB."
        status={
          findings ? (
            ready ? (
              <Badge variant="success" className="gap-1">
                <CheckCircle2 className="h-3 w-3" />
                Ready
              </Badge>
            ) : (
              <Badge variant="destructive" className="gap-1">
                <XCircle className="h-3 w-3" />
                Blocked · {counts.error} {counts.error === 1 ? "error" : "errors"}
              </Badge>
            )
          ) : null
        }
        actions={
          <Button size="sm" className="gap-1.5">
            <Sparkles className="h-3.5 w-3.5" />
            Re-run check
          </Button>
        }
      />

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <FilterKpi
          label="All"
          count={findings?.length ?? 0}
          icon={ListFilter}
          accent="primary"
          active={filter === "all"}
          loading={!findings}
          onClick={() => setFilter("all")}
        />
        <FilterKpi
          label="Errors"
          count={counts.error}
          icon={XCircle}
          accent="destructive"
          active={filter === "error"}
          loading={!findings}
          onClick={() => setFilter("error")}
        />
        <FilterKpi
          label="Warnings"
          count={counts.warning}
          icon={AlertTriangle}
          accent="warning"
          active={filter === "warning"}
          loading={!findings}
          onClick={() => setFilter("warning")}
        />
        <FilterKpi
          label="Info"
          count={counts.info}
          icon={Info}
          accent="info"
          active={filter === "info"}
          loading={!findings}
          onClick={() => setFilter("info")}
        />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
        <Card className="shadow-card lg:col-span-5">
          <CardContent className="p-0">
            <ScrollArea className="h-[620px]">
              {filtered ? (
                filtered.length === 0 ? (
                  <div className="flex h-40 items-center justify-center text-[12.5px] text-muted-foreground">
                    No findings match this filter.
                  </div>
                ) : (
                  <ul>
                    {filtered.map((f) => (
                      <FindingRow
                        key={f.id}
                        f={f}
                        selected={selected?.id === f.id}
                        onClick={() => setSelected(f)}
                      />
                    ))}
                  </ul>
                )
              ) : (
                <div className="space-y-3 p-4">
                  {Array.from({ length: 6 }).map((_, i) => (
                    <Skeleton key={i} className="h-16 w-full" />
                  ))}
                </div>
              )}
            </ScrollArea>
          </CardContent>
        </Card>

        <Card className="shadow-card lg:col-span-7">
          <CardContent className="p-0">
            {selected ? (
              <FindingDetail
                finding={selected}
                onClose={() => setSelected(null)}
              />
            ) : (
              <div className="flex h-[620px] items-center justify-center p-8 text-center text-[12.5px] text-muted-foreground">
                Select a finding to see the explanation.
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

const ACCENT_CLASSES = {
  primary: {
    ringActive: "ring-primary/35",
    rail: "bg-primary",
    tint: "bg-primary/10 text-primary",
  },
  destructive: {
    ringActive: "ring-red-500/35",
    rail: "bg-red-500",
    tint: "bg-red-500/10 text-red-600 dark:text-red-300",
  },
  warning: {
    ringActive: "ring-amber-500/40",
    rail: "bg-amber-500",
    tint: "bg-amber-500/10 text-amber-600 dark:text-amber-300",
  },
  info: {
    ringActive: "ring-sky-500/35",
    rail: "bg-sky-500",
    tint: "bg-sky-500/10 text-sky-600 dark:text-sky-300",
  },
} as const;

function FilterKpi({
  label,
  count,
  icon: Icon,
  accent,
  active,
  loading,
  onClick,
}: {
  label: string;
  count: number;
  icon: React.ComponentType<{ className?: string }>;
  accent: keyof typeof ACCENT_CLASSES;
  active: boolean;
  loading?: boolean;
  onClick: () => void;
}) {
  const a = ACCENT_CLASSES[accent];
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={cn(
        "group relative rounded-xl border bg-card p-4 text-left shadow-card transition-all hover:border-foreground/20",
        active && `border-transparent ring-2 ${a.ringActive}`
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="text-[10.5px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
            {label}
          </div>
          <div className="mt-1.5 text-[26px] font-semibold leading-none tracking-[-0.02em] tabular-nums">
            {loading ? <Skeleton className="h-7 w-9" /> : count}
          </div>
          {active && (
            <div className="mt-2 text-[10px] font-medium uppercase tracking-[0.1em] text-muted-foreground">
              · filtering
            </div>
          )}
        </div>
        <div
          className={cn(
            "flex h-8 w-8 shrink-0 items-center justify-center rounded-lg",
            a.tint
          )}
        >
          <Icon className="h-4 w-4" />
        </div>
      </div>
      {active && (
        <div
          className={cn(
            "absolute bottom-0 left-4 right-4 h-[2px] rounded-full",
            a.rail
          )}
        />
      )}
    </button>
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
    <li>
      <button
        type="button"
        onClick={onClick}
        className={cn(
          "relative flex w-full items-start gap-3 border-b px-5 py-3.5 text-left transition-colors hover:bg-accent/60",
          selected && "bg-primary/5"
        )}
      >
        <span
          className={cn(
            "absolute left-0 top-0 bottom-0 w-[3px]",
            meta.railClass
          )}
        />
        <Icon className={cn("mt-0.5 h-4 w-4 shrink-0", meta.iconClass)} />
        <div className="min-w-0 flex-1">
          <div className="truncate text-[13px] font-medium leading-snug">
            {f.title}
          </div>
          <div className="mt-0.5 truncate font-mono text-[10.5px] text-muted-foreground">
            {f.location}
          </div>
          <div className="mt-1.5 flex items-center gap-2">
            <Badge variant={meta.badgeVariant}>{meta.label}</Badge>
            <span className="font-mono text-[10.5px] text-muted-foreground">
              {f.ruleId}
            </span>
          </div>
        </div>
      </button>
    </li>
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
    <div className="flex h-[620px] flex-col">
      <div className="flex items-start justify-between border-b px-5 py-4">
        <div className="flex items-start gap-3">
          <div
            className={cn(
              "flex h-9 w-9 shrink-0 items-center justify-center rounded-lg",
              meta.tintClass
            )}
          >
            <Icon className="h-4 w-4" />
          </div>
          <div>
            <div className="mb-1 flex items-center gap-2">
              <Badge variant={meta.badgeVariant}>{meta.label}</Badge>
              <span className="font-mono text-[10.5px] text-muted-foreground">
                {finding.ruleId}
              </span>
            </div>
            <h3 className="text-[14px] font-semibold leading-snug">
              {finding.title}
            </h3>
            <div className="mt-0.5 font-mono text-[11px] text-muted-foreground">
              {finding.location}
            </div>
          </div>
        </div>
        <Button variant="ghost" size="icon" onClick={onClose} aria-label="Close">
          <X className="h-4 w-4" />
        </Button>
      </div>

      <ScrollArea className="flex-1">
        <div className="space-y-5 p-5 text-[13px]">
          <Section label="Evidence">
            <pre className="whitespace-pre-wrap rounded-md border bg-muted/40 p-3 font-mono text-[11.5px] leading-relaxed">
              {finding.evidence}
            </pre>
          </Section>

          <Section label="Why it matters">
            <p className="leading-relaxed">{finding.explanation}</p>
          </Section>

          <Section label="Suggested action">
            <p className="leading-relaxed">{finding.suggestion}</p>
          </Section>

          {finding.citations.length > 0 && (
            <Section label="Citations">
              <div className="flex flex-wrap items-center gap-1.5">
                {finding.citations.map((c, i) => (
                  <CitePop key={c.id} n={i + 1} citation={c} />
                ))}
                <span className="ml-2 text-[11.5px] text-muted-foreground">
                  click a marker to inspect the source
                </span>
              </div>
            </Section>
          )}

          <div className="flex items-center gap-2 rounded-lg border border-dashed bg-muted/30 p-3 text-[11.5px] text-muted-foreground">
            <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />
            Grounded in SWAT+ I/O spec and the Literature DB. Every claim is
            traceable to the citations above.
          </div>
        </div>
      </ScrollArea>
    </div>
  );
}

function Section({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <div className="mb-2 text-[10.5px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
        {label}
      </div>
      {children}
    </div>
  );
}
