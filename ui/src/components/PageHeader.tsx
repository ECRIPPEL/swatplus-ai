import type { ReactNode } from "react";

interface PageHeaderProps {
  overline?: string;
  title: ReactNode;
  desc?: ReactNode;
  status?: ReactNode;
  actions?: ReactNode;
}

export default function PageHeader({
  overline,
  title,
  desc,
  status,
  actions,
}: PageHeaderProps) {
  return (
    <div className="flex items-start justify-between gap-6">
      <div className="min-w-0">
        {overline && (
          <div className="mb-1.5 text-[10.5px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
            {overline}
          </div>
        )}
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-[26px] font-semibold leading-[1.15] tracking-[-0.02em]">
            {title}
          </h1>
          {status}
        </div>
        {desc && (
          <p className="mt-1.5 max-w-2xl text-[13px] leading-relaxed text-muted-foreground">
            {desc}
          </p>
        )}
      </div>
      {actions && (
        <div className="flex shrink-0 items-center gap-2">{actions}</div>
      )}
    </div>
  );
}
