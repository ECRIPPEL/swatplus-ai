import { ExternalLink } from "lucide-react";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import type { Citation } from "@/lib/types";

interface CitePopProps {
  n: number;
  citation: Citation;
}

export default function CitePop({ n, citation }: CitePopProps) {
  return (
    <Popover>
      <PopoverTrigger asChild>
        <button
          type="button"
          className="mx-[1px] inline-flex h-[15px] min-w-[16px] items-center justify-center rounded-[3px] border border-primary/25 bg-primary/10 px-1 align-super text-[9.5px] font-semibold leading-none text-primary transition-colors hover:bg-primary/18"
          aria-label={`Citation ${n}: ${citation.label}`}
        >
          {n}
        </button>
      </PopoverTrigger>
      <PopoverContent className="w-80 p-3">
        <div className="flex items-start gap-2">
          <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-primary/10 text-primary">
            <ExternalLink className="h-3.5 w-3.5" />
          </div>
          <div className="min-w-0 flex-1">
            <div className="text-[10px] font-medium uppercase tracking-[0.12em] text-muted-foreground">
              Citation · {citation.label}
            </div>
            <div className="mt-1 text-[12.5px] leading-snug text-foreground">
              {citation.source}
            </div>
          </div>
        </div>
      </PopoverContent>
    </Popover>
  );
}
