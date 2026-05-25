import { Cell, Pie, PieChart, ResponsiveContainer } from "recharts";
import type { LanduseClass } from "@/lib/types";

const COLORS = [
  "hsl(var(--chart-1))",
  "hsl(var(--chart-2))",
  "hsl(var(--chart-3))",
  "hsl(var(--chart-4))",
  "hsl(var(--chart-5))",
  "hsl(var(--muted-foreground))",
  "hsl(var(--border))",
];

interface LanduseDonutProps {
  data: LanduseClass[];
}

export default function LanduseDonut({ data }: LanduseDonutProps) {
  return (
    <div className="flex items-center gap-5">
      <div className="h-[200px] w-[200px] shrink-0">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              dataKey="pct"
              nameKey="className"
              cx="50%"
              cy="50%"
              innerRadius={52}
              outerRadius={82}
              paddingAngle={1.5}
              stroke="hsl(var(--background))"
              strokeWidth={2}
              isAnimationActive={false}
            >
              {data.map((_, i) => (
                <Cell key={i} fill={COLORS[i % COLORS.length]} />
              ))}
            </Pie>
          </PieChart>
        </ResponsiveContainer>
      </div>
      <ul className="min-w-0 flex-1 space-y-1.5">
        {data.map((d, i) => (
          <li
            key={d.className}
            className="flex items-center gap-2.5 text-[12px] leading-tight"
          >
            <span
              className="h-2 w-2 shrink-0 rounded-[2px]"
              style={{ background: COLORS[i % COLORS.length] }}
            />
            <span className="w-12 shrink-0 font-mono text-[11px] text-muted-foreground">
              {d.className}
            </span>
            <span className="min-w-0 flex-1 truncate">{d.name}</span>
            <span className="shrink-0 font-mono tabular-nums text-muted-foreground">
              {d.pct.toFixed(1)}%
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
