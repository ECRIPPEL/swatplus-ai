import type { TooltipProps } from "recharts";
import type { NameType, ValueType } from "recharts/types/component/DefaultTooltipContent";

interface ChartTooltipProps
  extends Omit<TooltipProps<ValueType, NameType>, "formatter" | "labelFormatter"> {
  formatter?: (value: number, name?: string) => string;
  labelFormatter?: (label: string | number) => string;
}

export default function ChartTooltip({
  active,
  payload,
  label,
  formatter,
  labelFormatter,
}: ChartTooltipProps) {
  if (!active || !payload || payload.length === 0) return null;

  const rows = payload.filter((p) => p.value !== undefined && p.value !== null);
  if (rows.length === 0) return null;

  return (
    <div className="rounded-lg border bg-popover/97 px-3 py-2 text-xs shadow-pop backdrop-blur">
      {label !== undefined && (
        <div className="mb-1 font-mono text-[10px] uppercase tracking-[0.1em] text-muted-foreground">
          {labelFormatter ? labelFormatter(label as string | number) : label}
        </div>
      )}
      <div className="space-y-1">
        {rows.map((p, i) => (
          <div key={i} className="flex items-center gap-2.5">
            <span
              className="h-2 w-2 shrink-0 rounded-sm"
              style={{ background: (p.color as string) ?? "hsl(var(--primary))" }}
            />
            {p.name !== undefined && (
              <span className="text-muted-foreground">{p.name}</span>
            )}
            <span className="ml-auto font-mono tabular-nums text-foreground">
              {formatter
                ? formatter(Number(p.value), p.name as string | undefined)
                : String(p.value)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
