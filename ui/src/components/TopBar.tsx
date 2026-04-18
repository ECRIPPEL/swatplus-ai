import { useLocation } from "react-router-dom";
import { Bell, ChevronDown, FolderOpen, Settings } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { ThemeToggle } from "@/components/ThemeToggle";

const TITLES: Record<string, string> = {
  "/dashboard": "Dashboard",
  "/setup": "Setup Check",
  "/calibration": "Calibration",
  "/evaluation": "Evaluation",
  "/chat": "Chat",
};

export default function TopBar() {
  const { pathname } = useLocation();
  const title = TITLES[pathname] ?? "SWAT+ai";

  return (
    <header className="flex h-14 items-center justify-between border-b bg-card px-6">
      <div className="flex items-center gap-3">
        <h1 className="text-lg font-semibold tracking-tight">{title}</h1>
      </div>

      <div className="flex items-center gap-2">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="outline" size="sm" className="gap-2">
              <FolderOpen className="h-3.5 w-3.5" />
              URU Basin
              <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-56">
            <DropdownMenuLabel>Recent projects</DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem>URU Basin (current)</DropdownMenuItem>
            <DropdownMenuItem>Little River Experimental</DropdownMenuItem>
            <DropdownMenuItem>Upper Iguazu Demo</DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem>Open TxtInOut folder…</DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>

        <Separator orientation="vertical" className="mx-1 h-6" />

        <Button variant="ghost" size="icon" aria-label="Notifications">
          <Bell className="h-4 w-4" />
        </Button>
        <ThemeToggle />
        <Button variant="ghost" size="icon" aria-label="Settings">
          <Settings className="h-4 w-4" />
        </Button>

        <div className="ml-2 flex items-center gap-2 rounded-full border py-1 pl-1 pr-3">
          <div className="flex h-6 w-6 items-center justify-center rounded-full bg-primary text-[10px] font-semibold text-primary-foreground">
            ER
          </div>
          <div className="text-xs leading-tight">
            <div className="font-medium">E. Rippel</div>
            <div className="text-[10px] text-muted-foreground">Modeler</div>
          </div>
        </div>
      </div>
    </header>
  );
}
