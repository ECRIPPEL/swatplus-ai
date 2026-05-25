interface ProgressRingProps {
  value: number;
  size?: number;
  stroke?: number;
  color?: string;
  track?: string;
  className?: string;
}

export function ProgressRing({
  value,
  size = 56,
  stroke = 4.5,
  color = "hsl(var(--primary))",
  track = "hsl(var(--muted))",
  className,
}: ProgressRingProps) {
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  return (
    <svg
      width={size}
      height={size}
      className={`block -rotate-90 ${className ?? ""}`}
    >
      <circle
        cx={size / 2}
        cy={size / 2}
        r={r}
        fill="none"
        stroke={track}
        strokeWidth={stroke}
      />
      <circle
        cx={size / 2}
        cy={size / 2}
        r={r}
        fill="none"
        stroke={color}
        strokeWidth={stroke}
        strokeDasharray={c}
        strokeDashoffset={c * (1 - value / 100)}
        strokeLinecap="round"
        style={{ transition: "stroke-dashoffset 600ms ease-out" }}
      />
    </svg>
  );
}
