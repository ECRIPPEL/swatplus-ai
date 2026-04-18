import { NavLink } from "react-router-dom";
import {
  BarChart3,
  Droplets,
  LayoutDashboard,
  MessageSquare,
  Sliders,
  Sparkles,
} from "lucide-react";
import { cn } from "@/lib/utils";

const NAV = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/setup", label: "Setup Check", icon: Droplets },
  { to: "/calibration", label: "Calibration", icon: Sliders },
  { to: "/evaluation", label: "Evaluation", icon: BarChart3 },
  { to: "/chat", label: "Chat", icon: MessageSquare },
];

export default function Sidebar() {
  return (
    <aside className="flex h-full w-60 flex-col border-r bg-card">
      <div className="flex h-14 items-center gap-2 border-b px-5">
        <div className="flex h-7 w-7 items-center justify-center rounded-md bg-primary text-primary-foreground">
          <Sparkles className="h-4 w-4" />
        </div>
        <div className="leading-tight">
          <div className="text-sm font-semibold">SWAT+ai</div>
          <div className="text-[10px] uppercase tracking-wider text-muted-foreground">
            v0.1.0-alpha
          </div>
        </div>
      </div>

      <nav className="flex-1 space-y-1 px-3 py-4">
        {NAV.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                isActive
                  ? "bg-primary/10 text-primary"
                  : "text-muted-foreground hover:bg-accent hover:text-foreground"
              )
            }
          >
            <Icon className="h-4 w-4" />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="m-3 rounded-xl border bg-gradient-to-br from-primary/10 via-primary/5 to-transparent p-4">
        <div className="mb-1 flex items-center gap-2 text-xs font-semibold">
          <Sparkles className="h-3 w-3 text-primary" />
          LLM provider
        </div>
        <div className="text-xs text-muted-foreground">
          Anthropic · claude-opus-4-7
        </div>
        <div className="mt-2 flex items-center gap-1 text-[11px] text-muted-foreground">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
          Key configured via keychain
        </div>
      </div>
    </aside>
  );
}
