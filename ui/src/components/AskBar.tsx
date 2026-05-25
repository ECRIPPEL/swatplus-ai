import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type FormEvent,
  type KeyboardEvent,
} from "react";
import { useLocation } from "react-router-dom";
import { ArrowUp, Loader2, Maximize2, Sparkles, X } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  ctxForRoute,
  streamAssistantReply,
  type ReplyMode,
} from "@/lib/client";
import { cn } from "@/lib/utils";

interface AskMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  mode: ReplyMode;
  timestamp: string;
}

export default function AskBar() {
  const location = useLocation();
  const ctx = useMemo(
    () => ctxForRoute(location.pathname),
    [location.pathname]
  );

  const [expanded, setExpanded] = useState(false);
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<AskMessage[]>([]);
  const [streaming, setStreaming] = useState(false);

  const wrapperRef = useRef<HTMLDivElement>(null);
  const pillInputRef = useRef<HTMLInputElement>(null);
  const panelInputRef = useRef<HTMLInputElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setExpanded(false);
  }, [location.pathname]);

  useEffect(() => {
    const onKey = (e: globalThis.KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "j") {
        e.preventDefault();
        setExpanded((v) => !v);
      } else if (e.key === "Escape") {
        setExpanded(false);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  useEffect(() => {
    if (!expanded) return;
    const onMouseDown = (e: MouseEvent) => {
      if (
        wrapperRef.current &&
        !wrapperRef.current.contains(e.target as Node)
      ) {
        setExpanded(false);
      }
    };
    document.addEventListener("mousedown", onMouseDown);
    return () => document.removeEventListener("mousedown", onMouseDown);
  }, [expanded]);

  useEffect(() => {
    if (expanded) {
      const t = setTimeout(() => panelInputRef.current?.focus(), 40);
      return () => clearTimeout(t);
    }
  }, [expanded]);

  useEffect(() => {
    if (expanded) {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, streaming, expanded]);

  const lastConcise = useMemo(() => {
    for (let i = messages.length - 1; i >= 0; i--) {
      const m = messages[i];
      if (m.role === "assistant" && m.mode === "concise") return m;
    }
    return null;
  }, [messages]);

  const send = useCallback(
    async (text: string, mode: ReplyMode) => {
      const trimmed = text.trim();
      if (!trimmed || streaming) return;
      const userMsg: AskMessage = {
        id: `u-${Date.now()}`,
        role: "user",
        content: trimmed,
        mode,
        timestamp: new Date().toISOString(),
      };
      const botId = `a-${Date.now()}`;
      const botMsg: AskMessage = {
        id: botId,
        role: "assistant",
        content: "",
        mode,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, userMsg, botMsg]);
      setInput("");
      setStreaming(true);
      const controller = new AbortController();
      abortRef.current = controller;
      try {
        await streamAssistantReply(
          trimmed,
          mode,
          (chunk) => {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === botId ? { ...m, content: m.content + chunk } : m
              )
            );
          },
          controller.signal
        );
      } finally {
        if (abortRef.current === controller) {
          abortRef.current = null;
        }
        setStreaming(false);
      }
    },
    [streaming]
  );

  const onPillSubmit = (e: FormEvent) => {
    e.preventDefault();
    send(input, "concise");
  };

  const onPanelSubmit = (e: FormEvent) => {
    e.preventDefault();
    send(input, "free");
  };

  const onPillKey = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "ArrowUp" && !input) {
      e.preventDefault();
      setExpanded(true);
    }
  };

  return (
    <div
      ref={wrapperRef}
      className="pointer-events-none fixed inset-x-0 bottom-5 z-40 flex flex-col items-center gap-2"
    >
      {!expanded && lastConcise && (
        <div className="pointer-events-auto w-[560px] rounded-xl border bg-card/95 px-3.5 py-2 shadow-pop backdrop-blur">
          <div className="flex items-start gap-2">
            <Sparkles className="mt-0.5 h-3.5 w-3.5 shrink-0 text-primary" />
            <div className="min-w-0 flex-1">
              <div className="text-[12.5px] leading-snug text-foreground">
                {lastConcise.content}
                {streaming && lastConcise.content.length === 0 && (
                  <span className="inline-block h-1 w-1 animate-pulse rounded-full bg-primary align-middle" />
                )}
              </div>
              <button
                type="button"
                onClick={() => setExpanded(true)}
                className="mt-1 inline-flex items-center gap-1 text-[10.5px] font-medium text-muted-foreground transition-colors hover:text-foreground"
              >
                <Maximize2 className="h-3 w-3" />
                Expand for detailed answer
              </button>
            </div>
          </div>
        </div>
      )}

      {expanded && (
        <div className="pointer-events-auto flex w-[620px] max-w-[calc(100vw-2rem)] flex-col overflow-hidden rounded-2xl border bg-card shadow-pop">
          <div className="flex items-center justify-between border-b px-4 py-2.5">
            <div className="flex items-center gap-2">
              <Sparkles className="h-3.5 w-3.5 text-primary" />
              <span className="text-[12px] font-medium">{ctx.title}</span>
            </div>
            <button
              type="button"
              onClick={() => setExpanded(false)}
              className="rounded-md p-1 text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
              aria-label="Close panel"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </div>

          <ScrollArea className="max-h-[360px] min-h-[200px]">
            <div className="space-y-4 px-5 py-4">
              {messages.length === 0 ? (
                <EmptyState
                  suggestions={ctx.suggestions}
                  onPick={(s) => send(s, "free")}
                />
              ) : (
                messages.map((m) => <MessageBubble key={m.id} m={m} />)
              )}
              {streaming && (
                <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
                  <Loader2 className="h-3 w-3 animate-spin" />
                  streaming…
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          </ScrollArea>

          <div className="border-t bg-muted/30 px-4 py-3">
            <div className="mb-2 flex flex-wrap gap-1.5">
              {ctx.items.map((it) => (
                <span
                  key={it}
                  className="inline-flex items-center rounded-full border bg-background px-2 py-0.5 font-mono text-[10px] text-muted-foreground"
                >
                  {it}
                </span>
              ))}
            </div>
            <form
              onSubmit={onPanelSubmit}
              className="flex items-center gap-2 rounded-full border bg-background pl-3.5 pr-1"
            >
              <input
                ref={panelInputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder={ctx.placeholder}
                className="h-10 min-w-0 flex-1 bg-transparent text-[13px] outline-none placeholder:text-muted-foreground"
                disabled={streaming}
              />
              <button
                type="submit"
                disabled={!input.trim() || streaming}
                className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground transition-colors hover:bg-primary/90 disabled:opacity-40"
                aria-label="Send"
              >
                <ArrowUp className="h-4 w-4" />
              </button>
            </form>
            <div className="mt-2 flex items-center justify-between text-[10.5px] text-muted-foreground">
              <span>markdown · grounded retrieval ON</span>
              <span className="font-mono">⌘J toggle · Esc close</span>
            </div>
          </div>
        </div>
      )}

      {!expanded && (
        <form
          onSubmit={onPillSubmit}
          className="pointer-events-auto flex h-12 w-[560px] max-w-[calc(100vw-2rem)] items-center rounded-full border bg-card pl-4 pr-1.5 shadow-pop"
        >
          <Sparkles className="mr-2.5 h-4 w-4 shrink-0 text-primary" />
          <input
            ref={pillInputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={onPillKey}
            placeholder={ctx.placeholder}
            className="h-full min-w-0 flex-1 bg-transparent text-[13px] outline-none placeholder:text-muted-foreground"
            disabled={streaming}
          />
          <kbd className="ml-2 hidden select-none items-center rounded-md border bg-muted px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground md:inline-flex">
            ⌘J
          </kbd>
          <button
            type="submit"
            disabled={!input.trim() || streaming}
            className={cn(
              "ml-1.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground transition-colors hover:bg-primary/90 disabled:opacity-40"
            )}
            aria-label="Ask"
          >
            <ArrowUp className="h-4 w-4" />
          </button>
        </form>
      )}
    </div>
  );
}

function EmptyState({
  suggestions,
  onPick,
}: {
  suggestions: string[];
  onPick: (s: string) => void;
}) {
  return (
    <div className="space-y-2">
      <div className="text-[11px] font-medium uppercase tracking-[0.12em] text-muted-foreground">
        Try
      </div>
      <div className="flex flex-col gap-1.5">
        {suggestions.map((s) => (
          <button
            key={s}
            type="button"
            onClick={() => onPick(s)}
            className="rounded-lg border bg-background px-3 py-2 text-left text-[12.5px] transition-colors hover:border-foreground/20 hover:bg-accent"
          >
            {s}
          </button>
        ))}
      </div>
    </div>
  );
}

function MessageBubble({ m }: { m: AskMessage }) {
  const isUser = m.role === "user";
  if (isUser) {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] rounded-2xl bg-primary px-3.5 py-2 text-[13px] leading-snug text-primary-foreground">
          {m.content}
        </div>
      </div>
    );
  }
  return (
    <div className="flex gap-2.5">
      <div className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary">
        <Sparkles className="h-3 w-3" />
      </div>
      <div className="min-w-0 flex-1">
        <div className="prose prose-sm max-w-none text-[13px] leading-relaxed text-foreground dark:prose-invert prose-p:my-1.5 prose-ul:my-1.5 prose-ol:my-1.5 prose-li:my-0.5 prose-code:rounded prose-code:bg-muted prose-code:px-1 prose-code:py-[1px] prose-code:font-mono prose-code:text-[11.5px] prose-code:before:content-none prose-code:after:content-none prose-pre:bg-muted prose-pre:text-[11.5px] prose-strong:font-semibold prose-em:italic">
          {m.content ? (
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {m.content}
            </ReactMarkdown>
          ) : (
            <span className="text-[12px] italic text-muted-foreground">
              thinking…
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
