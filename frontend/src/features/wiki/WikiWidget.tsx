"use client";

import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { usePathname } from "next/navigation";

import { createWikiRequest } from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import { cn } from "@/lib/cn";
import { buildWikiRequestPayload, buildWikiSupportHref } from "./request-support";
import { EvidenceBadge, ModeBadge, ToolCallBadge } from "./message-metadata";
import type { WikiChatMessage } from "./types";
import { useWikiChat } from "./useWikiChat";

function SourceBadge({ file }: { file: string }) {
  const short = file.split("/").pop() ?? file;
  return (
    <span className="inline-block rounded bg-green-50 px-1.5 py-0.5 text-xs text-green-700 border border-green-200">
      {short}
    </span>
  );
}

function ChatMessage({
  msg,
  onQuickRequest,
  supportHref,
}: {
  msg: WikiChatMessage;
  onQuickRequest: (intent: "help_request" | "bug_report" | "feature_request", answer: string) => void;
  supportHref: string | null;
}) {
  const isUser = msg.role === "user";

  return (
    <div className={cn("flex flex-col gap-1", isUser ? "items-end" : "items-start")}>
      <div
        className={cn(
          "max-w-[85%] rounded-2xl px-3 py-2 text-sm leading-relaxed",
          isUser
            ? "bg-[#1D4E35] text-white rounded-br-sm"
            : "bg-gray-100 text-gray-900 rounded-bl-sm"
        )}
      >
        {msg.content}
      </div>

      {!isUser ? (
        <div className="flex max-w-[85%] flex-wrap gap-1 px-1">
          <ModeBadge mode={msg.mode} />
          {msg.tool_calls?.map((toolCall, index) => <ToolCallBadge key={`${toolCall.tool_name}-${index}`} toolCall={toolCall} />)}
        </div>
      ) : null}

      {!isUser && msg.sources && msg.sources.length > 0 && (
        <div className="flex flex-wrap gap-1 px-1">
          {msg.sources.map((s, i) => (
            <SourceBadge key={i} file={s.source_file} />
          ))}
        </div>
      )}

      {!isUser && msg.evidences && msg.evidences.length > 0 && (
        <div className="grid max-w-[85%] gap-1.5 px-1">
          {msg.evidences.map((evidence, index) => (
            <EvidenceBadge key={`${evidence.source_key}-${index}`} evidence={evidence} />
          ))}
        </div>
      )}

      {!isUser && msg.found === false ? (
        <div className="ml-1 flex max-w-[85%] flex-wrap gap-2 pt-1">
          <button
            onClick={() => onQuickRequest("help_request", msg.content)}
            className="rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-800 hover:bg-emerald-100"
          >
            Chiedi supporto
          </button>
          <button
            onClick={() => onQuickRequest("bug_report", msg.content)}
            className="rounded-full border border-amber-200 bg-amber-50 px-2.5 py-1 text-xs font-medium text-amber-800 hover:bg-amber-100"
          >
            Segnala problema
          </button>
          <button
            onClick={() => onQuickRequest("feature_request", msg.content)}
            className="rounded-full border border-sky-200 bg-sky-50 px-2.5 py-1 text-xs font-medium text-sky-800 hover:bg-sky-100"
          >
            Richiedi funzionalità
          </button>
          {supportHref ? (
            <a
              href={supportHref}
              className="rounded-full border border-gray-200 bg-white px-2.5 py-1 text-xs font-medium text-gray-700 hover:border-[#1D4E35] hover:text-[#1D4E35]"
            >
              Apri supporto completo
            </a>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

export function WikiWidget() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState("");
  const [savedRequest, setSavedRequest] = useState(false);
  const [mounted, setMounted] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const { messages, conversationId, loading, sendMessage, clearMessages } = useWikiChat();

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (open) {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
      inputRef.current?.focus();
    }
  }, [open, messages]);

  useEffect(() => {
    setOpen(false);
  }, [pathname]);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!input.trim()) return;
    sendMessage(input);
    setInput("");
    setSavedRequest(false);
  }

  async function handleQuickRequest(intent: "help_request" | "bug_report" | "feature_request", answer: string) {
    const token = getStoredAccessToken();
    if (!token) {
      return;
    }
    await createWikiRequest(
      token,
      buildWikiRequestPayload({
        intent,
        pathname,
        contextArticle: undefined,
        conversationId,
        messages,
        assistantAnswer: answer,
        sourceChannel: "widget",
      }),
    );
    setSavedRequest(true);
  }

  const shouldHideWidget = pathname === "/wiki" || pathname.startsWith("/wiki/") || pathname === "/login";

  if (!mounted || shouldHideWidget) {
    return null;
  }

  const widget = (
    <>
      <button
        onClick={() => setOpen((v) => !v)}
        className={cn(
          "fixed z-[120] flex h-14 w-14 items-center justify-center rounded-full shadow-lg transition-all",
          "bg-[#1D4E35] text-white hover:bg-[#163d29] focus:outline-none focus:ring-2 focus:ring-[#1D4E35] focus:ring-offset-2",
          open && "rotate-45"
        )}
        style={{ position: "fixed", right: "1.5rem", bottom: "1.5rem" }}
        aria-label={open ? "Chiudi assistente" : "Apri assistente GAIA"}
        title={open ? "Chiudi assistente" : "Assistente GAIA"}
      >
        <span className="material-symbols-outlined text-2xl">
          {open ? "close" : "assistant"}
        </span>
      </button>

      {open && (
        <div
          className="fixed z-[120] flex w-96 max-w-[calc(100vw-3rem)] flex-col overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-2xl"
          style={{ position: "fixed", right: "1.5rem", bottom: "6rem" }}
        >
          <div className="flex items-center justify-between bg-[#1D4E35] px-4 py-3">
            <div className="flex items-center gap-2">
              <span className="material-symbols-outlined text-xl text-white">assistant</span>
              <span className="text-sm font-semibold text-white">Assistente GAIA</span>
            </div>
            <div className="flex items-center gap-2">
              {messages.length > 0 && (
                <button
                  onClick={clearMessages}
                  className="text-xs text-white/70 underline underline-offset-2 hover:text-white"
                  title="Nuova conversazione"
                >
                  Resetta
                </button>
              )}
              <a
                href={conversationId ? `/wiki?conversation=${conversationId}` : "/wiki"}
                className="text-white/70 hover:text-white"
                title="Apri Wiki completa"
              >
                <span className="material-symbols-outlined text-base">open_in_new</span>
              </a>
            </div>
          </div>

          <div className="flex h-80 flex-col gap-3 overflow-y-auto p-4">
            {messages.length === 0 && (
              <div className="flex h-full flex-col items-center justify-center gap-2 text-center text-sm text-gray-400">
                <span className="material-symbols-outlined text-4xl text-gray-300">assistant</span>
                <p>Ciao! Sono l&apos;assistente GAIA.</p>
                <p>Chiedi qualsiasi cosa sulla piattaforma.</p>
              </div>
            )}
            {messages.map((msg) => (
              <ChatMessage
                key={msg.id}
                msg={msg}
                onQuickRequest={handleQuickRequest}
                supportHref={
                  msg.role === "assistant" && msg.found === false
                    ? buildWikiSupportHref({
                        intent: "help_request",
                        pathname,
                        conversationId: msg.conversationId ?? conversationId,
                        messages,
                        assistantAnswer: msg.content,
                      })
                    : null
                }
              />
            ))}
            {loading && (
              <div className="flex items-start gap-2">
                <div className="rounded-2xl rounded-bl-sm bg-gray-100 px-3 py-2 text-sm text-gray-500">
                  <span className="animate-pulse">...</span>
                </div>
              </div>
            )}
            {savedRequest && <p className="text-center text-xs text-green-600">Richiesta registrata. Grazie!</p>}
            <div ref={messagesEndRef} />
          </div>

          <form onSubmit={handleSubmit} className="flex gap-2 border-t border-gray-200 p-3">
            <input
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Scrivi una domanda..."
              disabled={loading}
              className="flex-1 rounded-xl border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#1D4E35] disabled:opacity-50"
            />
            <button
              type="submit"
              disabled={!input.trim() || loading}
              className="flex h-9 w-9 items-center justify-center rounded-xl bg-[#1D4E35] text-white transition-colors hover:bg-[#163d29] disabled:opacity-40"
            >
              <span className="material-symbols-outlined text-base">send</span>
            </button>
          </form>
        </div>
      )}
    </>
  );

  return createPortal(widget, document.body);
}
