import { useEffect, useRef, useState } from "react";
import { ArrowUp, ExternalLink, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Skeleton } from "@/components/ui/skeleton";
import { Input } from "@/components/ui/input";
import { getChatHistory, streamAssistantReply } from "@/lib/mockApi";
import type { ChatMessage } from "@/lib/types";
import { cn } from "@/lib/utils";

const SUGGESTIONS = [
  "Why is NSE stuck at 0.58?",
  "What does ALPHA_BF do physically?",
  "Is my warmup period long enough?",
  "Draft a results paragraph for publication",
];

export default function Chat() {
  const [messages, setMessages] = useState<ChatMessage[] | null>(null);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    getChatHistory().then(setMessages);
  }, []);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streaming]);

  const send = async (text: string) => {
    if (!text.trim() || streaming) return;
    const userMsg: ChatMessage = {
      id: `u-${Date.now()}`,
      role: "user",
      content: text.trim(),
      timestamp: new Date().toISOString(),
    };
    const botId = `a-${Date.now()}`;
    const botMsg: ChatMessage = {
      id: botId,
      role: "assistant",
      content: "",
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => (prev ? [...prev, userMsg, botMsg] : [userMsg, botMsg]));
    setInput("");
    setStreaming(true);
    await streamAssistantReply(text, (chunk) => {
      setMessages((prev) =>
        prev
          ? prev.map((m) => (m.id === botId ? { ...m, content: m.content + chunk } : m))
          : prev
      );
    });
    setStreaming(false);
  };

  return (
    <div className="flex h-[calc(100vh-7rem)] flex-col gap-4">
      <div className="flex items-start justify-between">
        <div>
          <div className="text-sm text-muted-foreground">Conversational Q&A</div>
          <h2 className="text-2xl font-semibold tracking-tight">Chat</h2>
          <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
            Always-on chat grounded in your project's parsed state, findings,
            and the Literature DB.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center gap-1.5 rounded-full border bg-card px-3 py-1 text-xs">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
            URU Basin · 15 findings in context
          </span>
        </div>
      </div>

      <Card className="flex flex-1 flex-col overflow-hidden">
        <CardContent className="flex flex-1 flex-col gap-0 p-0">
          <ScrollArea className="flex-1 px-6 py-6">
            {messages ? (
              <div className="mx-auto max-w-3xl space-y-6">
                {messages.map((m) => (
                  <Message key={m.id} m={m} />
                ))}
                {streaming && (
                  <div className="flex items-center gap-2 text-xs text-muted-foreground">
                    <span className="inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-primary" />
                    Streaming…
                  </div>
                )}
                <div ref={endRef} />
              </div>
            ) : (
              <div className="mx-auto max-w-3xl space-y-6">
                <Skeleton className="h-16 w-2/3" />
                <Skeleton className="ml-auto h-24 w-4/5" />
                <Skeleton className="h-16 w-3/5" />
              </div>
            )}
          </ScrollArea>

          <div className="border-t bg-muted/30 px-6 py-4">
            <div className="mx-auto max-w-3xl">
              <div className="mb-3 flex flex-wrap gap-2">
                {SUGGESTIONS.map((s) => (
                  <button
                    key={s}
                    type="button"
                    onClick={() => send(s)}
                    disabled={streaming}
                    className="rounded-full border bg-background px-3 py-1 text-xs text-muted-foreground transition-colors hover:bg-accent hover:text-foreground disabled:opacity-50"
                  >
                    {s}
                  </button>
                ))}
              </div>
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  send(input);
                }}
                className="flex items-center gap-2"
              >
                <Input
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder="Ask about diagnostics, calibration, or evaluation…"
                  className="h-11 bg-background"
                  disabled={streaming}
                />
                <Button
                  type="submit"
                  size="icon"
                  className="h-11 w-11 shrink-0"
                  disabled={!input.trim() || streaming}
                  aria-label="Send"
                >
                  <ArrowUp className="h-4 w-4" />
                </Button>
              </form>
              <div className="mt-2 flex items-center justify-between text-[11px] text-muted-foreground">
                <span>Anthropic · claude-opus-4-7 · grounded retrieval ON</span>
                <span>Press ⏎ to send · Shift+⏎ for newline</span>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function Message({ m }: { m: ChatMessage }) {
  const isUser = m.role === "user";
  return (
    <div className={cn("flex gap-3", isUser && "flex-row-reverse")}>
      <div
        className={cn(
          "flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-[10px] font-semibold",
          isUser
            ? "bg-secondary text-secondary-foreground"
            : "bg-primary text-primary-foreground"
        )}
      >
        {isUser ? "ER" : <Sparkles className="h-3.5 w-3.5" />}
      </div>
      <div
        className={cn(
          "max-w-[78%] rounded-2xl px-4 py-3 text-sm leading-relaxed",
          isUser
            ? "bg-primary text-primary-foreground"
            : "border bg-card text-foreground"
        )}
      >
        <div className="whitespace-pre-wrap">{m.content}</div>
        {!isUser && m.citations && m.citations.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-1.5">
            {m.citations.map((c) => (
              <span
                key={c.id}
                title={c.source}
                className="inline-flex items-center gap-1 rounded-full border bg-background px-2 py-0.5 text-[10px] text-muted-foreground"
              >
                <ExternalLink className="h-2.5 w-2.5" />
                {c.label}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
