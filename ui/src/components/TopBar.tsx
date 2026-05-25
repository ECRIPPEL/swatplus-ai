import { useLocation } from "react-router-dom";
import { Bell, ChevronDown, Search, Settings } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/ThemeToggle";

const TITLES: Record<string, string> = {
  "/": "URU Basin",
  "/setup": "Setup Check",
  "/calibration": "Calibration",
  "/evaluation": "Evaluation",
};

const CRUMBS: Record<string, string> = {
  "/": "Project overview",
  "/setup": "Module 1 · Diagnostics",
  "/calibration": "Module 2 · Calibration",
  "/evaluation": "Module 3 · Evaluation",
};

export default function TopBar() {
  const { pathname } = useLocation();
  const title = TITLES[pathname] ?? "SWAT+ai";
  const crumb = CRUMBS[pathname] ?? "";

  return (
    <header className="flex h-14 shrink-0 items-center justify-between gap-3 border-b border-border/70 bg-background/80 px-5 backdrop-blur-xl">
      <div className="flex min-w-0 items-center gap-3">
        <div className="flex min-w-0 flex-col">
          <span className="text-[10px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
            {crumb}
          </span>
          <span className="truncate text-[14px] font-semibold leading-tight tracking-tight">
            {title}
          </span>
        </div>
      </div>

      <div className="flex shrink-0 items-center gap-1.5">
        <div className="relative hidden xl:block">
          <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search findings, parameters…"
            className="h-8 w-[240px] rounded-lg border border-border/70 bg-card pl-8 pr-14 text-[12px] transition-colors placeholder:text-muted-foreground/70 focus:border-primary/40 focus:outline-none focus:ring-2 focus:ring-primary/25"
          />
          <kbd className="pointer-events-none absolute right-2 top-1/2 inline-flex -translate-y-1/2 items-center gap-0.5 rounded border border-border/70 bg-muted px-1.5 py-0.5 font-mono text-[9px] text-muted-foreground">
            ⌘K
          </kbd>
        </div>
        <Button variant="ghost" size="icon" className="xl:hidden" title="Search (⌘K)">
          <Search className="h-4 w-4" />
        </Button>

        <div className="mx-1 hidden h-5 w-px bg-border md:block" />

        <Button variant="ghost" size="icon" title="Notifications" className="relative">
          <Bell className="h-4 w-4" />
          <span className="absolute right-1 top-1 h-1.5 w-1.5 rounded-full bg-primary ring-2 ring-background" />
        </Button>
        <ThemeToggle />
        <Button variant="ghost" size="icon" title="Settings">
          <Settings className="h-4 w-4" />
        </Button>

        <div className="mx-1 h-5 w-px bg-border" />

        <button
          type="button"
          className="flex h-8 shrink-0 items-center gap-2 rounded-lg pl-1 pr-2 transition-colors hover:bg-accent/70"
        >
          <div className="flex h-6 w-6 items-center justify-center rounded-md bg-gradient-to-br from-primary/70 to-primary/40 text-[9.5px] font-semibold text-primary-foreground">
            ER
          </div>
          <ChevronDown className="h-3 w-3 text-muted-foreground" />
        </button>
      </div>
    </header>
  );
}
