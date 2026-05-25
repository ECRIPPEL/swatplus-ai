import { Link, NavLink } from "react-router-dom";
import {
  BarChart3,
  Book,
  ChevronDown,
  Droplets,
  Folder,
  Settings,
  Sliders,
  Terminal,
} from "lucide-react";
import { cn } from "@/lib/utils";

type NavItem = {
  to: string;
  label: string;
  icon: typeof Droplets;
  badge?: string | number | null;
};

const NAV: NavItem[] = [
  { to: "/setup", label: "Setup Check", icon: Droplets, badge: 15 },
  { to: "/calibration", label: "Calibration", icon: Sliders, badge: "iter 30" },
  { to: "/evaluation", label: "Evaluation", icon: BarChart3, badge: null },
];

const RESOURCES = [
  { label: "Literature DB", icon: Book, hint: "6.2k" },
  { label: "Rule catalog", icon: Terminal, hint: "52" },
  { label: "Settings", icon: Settings, hint: undefined },
];

export default function Sidebar() {
  return (
    <aside className="flex h-full w-[232px] shrink-0 flex-col border-r border-border/70 bg-card/60">
      <Link
        to="/"
        className="flex h-14 items-center gap-2.5 border-b border-border/70 px-5 transition-colors hover:bg-accent/30"
      >
        <div className="relative grid h-8 w-8 grid-cols-2 gap-[2px] rounded-[8px] bg-foreground p-[5px]">
          <span className="rounded-[1.5px] bg-background" />
          <span className="rounded-[1.5px] bg-background/55" />
          <span className="rounded-[1.5px] bg-background/55" />
          <span className="rounded-[1.5px] bg-background" />
        </div>
        <div className="leading-tight">
          <div className="text-[13.5px] font-semibold tracking-tight">SWAT+ai</div>
          <div className="font-mono text-[9.5px] uppercase tracking-[0.14em] text-muted-foreground">
            v0.1.0-alpha
          </div>
        </div>
      </Link>

      <div className="px-3 py-3">
        <Link
          to="/"
          className="group flex w-full items-center gap-2 rounded-lg border border-border/70 bg-card px-2.5 py-2 text-left transition-colors hover:bg-accent/60"
        >
          <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-[6px] bg-gradient-to-br from-primary/80 to-primary/50 text-primary-foreground">
            <Folder className="h-3.5 w-3.5" strokeWidth={2} />
          </div>
          <div className="min-w-0 flex-1">
            <div className="truncate text-[12.5px] font-medium">URU Basin</div>
            <div className="truncate font-mono text-[10px] text-muted-foreground">
              TxtInOut · 312 HRUs
            </div>
          </div>
          <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />
        </Link>
      </div>

      <nav className="flex-1 space-y-0.5 px-2">
        <div className="px-2 pb-1.5 pt-1 text-[10px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
          Workspace
        </div>
        {NAV.map(({ to, label, icon: Icon, badge }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              cn(
                "group relative flex h-9 w-full items-center gap-2.5 rounded-lg px-2.5 text-[13px] font-medium transition-all",
                isActive
                  ? "bg-foreground text-background shadow-card"
                  : "text-muted-foreground hover:bg-accent/70 hover:text-foreground"
              )
            }
          >
            {({ isActive }) => (
              <>
                <Icon
                  className={cn(
                    "h-[15px] w-[15px]",
                    isActive
                      ? "text-background"
                      : "text-muted-foreground group-hover:text-foreground"
                  )}
                  strokeWidth={isActive ? 2 : 1.75}
                />
                <span className="flex-1 text-left">{label}</span>
                {badge != null && (
                  <span
                    className={cn(
                      "rounded-md px-1.5 py-0.5 font-mono text-[10px] tabular-nums",
                      isActive
                        ? "bg-background/20 text-background"
                        : "bg-muted text-muted-foreground"
                    )}
                  >
                    {badge}
                  </span>
                )}
              </>
            )}
          </NavLink>
        ))}

        <div className="px-2 pb-1.5 pt-5 text-[10px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
          Resources
        </div>
        {RESOURCES.map(({ label, icon: Icon, hint }) => (
          <button
            key={label}
            className="group flex h-9 w-full items-center gap-2.5 rounded-lg px-2.5 text-[13px] font-medium text-muted-foreground transition-colors hover:bg-accent/70 hover:text-foreground"
          >
            <Icon className="h-[15px] w-[15px]" />
            <span className="flex-1 text-left">{label}</span>
            {hint && (
              <span className="font-mono text-[10px] text-muted-foreground/60">
                {hint}
              </span>
            )}
          </button>
        ))}
      </nav>

      <div className="m-3 rounded-xl border border-border/70 bg-card p-3">
        <div className="mb-2 flex items-center justify-between">
          <span className="text-[9.5px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
            LLM provider
          </span>
          <button className="text-[10px] text-muted-foreground hover:text-foreground">
            change
          </button>
        </div>
        <div className="flex items-center gap-2.5">
          <div className="flex h-7 w-7 items-center justify-center rounded-md bg-foreground font-mono text-[10px] font-semibold text-background">
            Ai
          </div>
          <div className="min-w-0">
            <div className="truncate text-xs font-medium">Anthropic</div>
            <div className="truncate font-mono text-[10px] text-muted-foreground">
              claude-opus-4-7
            </div>
          </div>
        </div>
        <div className="mt-2.5 flex items-center justify-between border-t border-border/60 pt-2.5 text-[10px]">
          <span className="inline-flex items-center gap-1.5 text-muted-foreground">
            <span className="relative flex h-1.5 w-1.5">
              <span className="absolute inset-0 animate-ping rounded-full bg-emerald-500 opacity-60" />
              <span className="relative h-1.5 w-1.5 rounded-full bg-emerald-500" />
            </span>
            keychain
          </span>
          <span className="font-mono tabular-nums text-muted-foreground">
            $0.12 · 12.4k tok
          </span>
        </div>
      </div>
    </aside>
  );
}
