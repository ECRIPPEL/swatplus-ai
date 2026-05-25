import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Activity,
  ArrowRight,
  Droplets,
  Info,
  TrendingUp,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import PageHeader from "@/components/PageHeader";
import WorldMiniMap from "@/components/WorldMiniMap";
import LanduseDonut from "@/components/LanduseDonut";
import {
  getLanduse,
  getProject,
  getRecentActivity,
} from "@/lib/client";
import type {
  ActivityEntry,
  LanduseClass,
  ProjectMeta,
} from "@/lib/types";
import { formatNumber } from "@/lib/utils";

export default function Home() {
  const [project, setProject] = useState<ProjectMeta | null>(null);
  const [landuse, setLanduse] = useState<LanduseClass[] | null>(null);
  const [activity, setActivity] = useState<ActivityEntry[] | null>(null);

  useEffect(() => {
    getProject().then(setProject);
    getLanduse().then(setLanduse);
    getRecentActivity().then(setActivity);
  }, []);

  return (
    <div className="mx-auto max-w-[1280px] space-y-7">
      <PageHeader
        overline="Project overview"
        title={project?.name ?? <Skeleton className="h-8 w-48" />}
        desc={
          project ? (
            <>
              {project.climate} · {formatNumber(project.areaKm2, 1)} km² ·{" "}
              {project.hrus} HRUs · outfall{" "}
              <span className="font-mono text-[12px]">
                {project.outfallChannel}
              </span>
            </>
          ) : (
            <Skeleton className="h-4 w-80" />
          )
        }
        actions={
          <Button asChild size="sm" className="gap-1.5">
            <Link to="/setup">
              Start analysis
              <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </Button>
        }
      />

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
        <Card className="shadow-card lg:col-span-2">
          <CardContent className="p-5">
            <div className="mb-3 text-[10.5px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
              Basin location
            </div>
            {project ? (
              <WorldMiniMap
                lat={project.outletLat}
                lon={project.outletLon}
                label={`${project.outletLat.toFixed(2)}°, ${project.outletLon.toFixed(
                  2
                )}° · ${project.biome}`}
              />
            ) : (
              <Skeleton className="h-[260px] w-full" />
            )}
          </CardContent>
        </Card>

        <Card className="shadow-card">
          <CardContent className="p-5">
            <div className="mb-3 text-[10.5px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
              Land use composition
            </div>
            {landuse ? (
              <LanduseDonut data={landuse} />
            ) : (
              <Skeleton className="h-[200px] w-full" />
            )}
          </CardContent>
        </Card>
      </div>

      <Card className="shadow-card">
        <CardContent className="flex flex-wrap items-center gap-x-10 gap-y-4 p-5">
          <Stat label="Sub-basins" value={project?.subbasins} />
          <Stat label="HRUs" value={project?.hrus} />
          <Stat label="Channels" value={project?.channels} />
          <Stat label="Weather stations" value={project?.weatherStations} />
          <Stat label="Model version" value={project?.modelVersion} wide />
          <Stat
            label="Warmup"
            value={project ? `${project.warmupYears} yr` : undefined}
          />
        </CardContent>
      </Card>

      <div>
        <div className="mb-3 text-[10.5px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
          Recent activity
        </div>
        <Card className="shadow-card">
          <CardContent className="space-y-1 p-3">
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
    </div>
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
      <div className="text-[10.5px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
        {label}
      </div>
      <div className="mt-1 text-[15px] font-semibold tabular-nums">
        {value ?? <Skeleton className="h-5 w-16" />}
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
    <div className="flex items-start gap-3 rounded-md px-2 py-1.5 hover:bg-accent">
      <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-primary/10 text-primary">
        <Icon className="h-3.5 w-3.5" />
      </div>
      <div className="min-w-0 flex-1">
        <div className="text-[13px] leading-snug">{a.summary}</div>
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
