import { Outlet } from "react-router-dom";
import { TooltipProvider } from "@/components/ui/tooltip";
import Sidebar from "@/components/Sidebar";
import TopBar from "@/components/TopBar";
import AskBar from "@/components/AskBar";

export default function Layout() {
  return (
    <TooltipProvider delayDuration={200}>
      <div className="flex h-screen w-screen overflow-hidden bg-background text-foreground">
        <Sidebar />
        <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
          <TopBar />
          <main className="min-w-0 flex-1 overflow-auto px-8 pb-24 pt-7">
            <Outlet />
          </main>
        </div>
      </div>
      <AskBar />
    </TooltipProvider>
  );
}
