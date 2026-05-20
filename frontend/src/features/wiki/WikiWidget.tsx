"use client";

import { useEffect, useRef, useState } from "react";

import { cn } from "@/lib/cn";
import type { WikiChatMessage, WikiRequestCreate } from "./types";
import { useWikiChat } from "./useWikiChat";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

async function saveWikiRequest(payload: WikiRequestCreate): Promise<void> {
  const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
  await fetch(`${API_BASE}/api/wiki/requests`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(payload),
  });
}

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
  onSaveRequest,
}: {
  msg: WikiChatMessage;
  onSaveRequest: (question: string, answer: string) => void;
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

      {!isUser && msg.sources && msg.sources.length > 0 && (
        <div className="flex flex-wrap gap-1 px-1">
          {msg.sources.map((s, i) => (
            <SourceBadge key={i} file={s.source_file} />
          ))}
        </div>
      )}

      {!isUser && msg.found === false && (
        <button
          onClick={() => onSaveRequest(
            messages_ref_hack(msg),
            msg.content
          )}
          className="ml-1 text-xs text-[#1D4E35] underline underline-offset-2 hover:opacity-70"
        >
          Registra come richiesta
        </button>
      )}
    </div>
  );
}

// Workaround: il messaggio utente precedente non è accessibile nel componente figlio.
// ChatMessage riceve solo il messaggio corrente; il genitore passa la domanda nel handler.
function messages_ref_hack(_msg: WikiChatMessage): string {
  return "";
}

export function WikiWidget() {
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState("");
  const [savedRequest, setSavedRequest] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const { messages, loading, sendMessage, clearMessages } = useWikiChat();

  useEffect(() => {
    if (open) {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
      inputRef.current?.focus();
    }
  }, [open, messages]);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!input.trim()) return;
    sendMessage(input);
    setInput("");
    setSavedRequest(false);
  }

  async function handleSaveRequest(question: string, answer: string) {
    // Recupera l'ultima domanda utente dalla lista messaggi
    const lastUserMsg = [...messages].reverse().find((m) => m.role === "user");
    await saveWikiRequest({
      user_question: lastUserMsg?.content ?? question,
      agent_response: answer,
      category: "feature_request",
    });
    setSavedRequest(true);
  }

  return (
    <>
      {/* Floating button */}
      <button
        onClick={() => setOpen((v) => !v)}
        className={cn(
          "fixed bottom-6 right-6 z-50 flex h-14 w-14 items-center justify-center rounded-full shadow-lg transition-all",
          "bg-[#1D4E35] text-white hover:bg-[#163d29] focus:outline-none focus:ring-2 focus:ring-[#1D4E35] focus:ring-offset-2",
          open && "rotate-45"
        )}
        aria-label={open ? "Chiudi assistente" : "Apri assistente GAIA"}
        title={open ? "Chiudi assistente" : "Assistente GAIA"}
      >
        <span className="material-symbols-outlined text-2xl">
          {open ? "close" : "assistant"}
        </span>
      </button>

      {/* Chat overlay */}
      {open && (
        <div className="fixed bottom-24 right-6 z-50 flex w-96 max-w-[calc(100vw-3rem)] flex-col rounded-2xl bg-white shadow-2xl border border-gray-200 overflow-hidden">
          {/* Header */}
          <div className="flex items-center justify-between bg-[#1D4E35] px-4 py-3">
            <div className="flex items-center gap-2">
              <span className="material-symbols-outlined text-white text-xl">assistant</span>
              <span className="text-sm font-semibold text-white">Assistente GAIA</span>
            </div>
            <div className="flex items-center gap-2">
              {messages.length > 0 && (
                <button
                  onClick={clearMessages}
                  className="text-white/70 hover:text-white text-xs underline underline-offset-2"
                  title="Nuova conversazione"
                >
                  Resetta
                </button>
              )}
              <a
                href="/wiki"
                className="text-white/70 hover:text-white"
                title="Apri Wiki completa"
              >
                <span className="material-symbols-outlined text-base">open_in_new</span>
              </a>
            </div>
          </div>

          {/* Messages */}
          <div className="flex flex-col gap-3 overflow-y-auto p-4 h-80">
            {messages.length === 0 && (
              <div className="flex flex-col items-center justify-center h-full gap-2 text-center text-sm text-gray-400">
                <span className="material-symbols-outlined text-4xl text-gray-300">assistant</span>
                <p>Ciao! Sono l&apos;assistente GAIA.</p>
                <p>Chiedi qualsiasi cosa sulla piattaforma.</p>
              </div>
            )}
            {messages.map((msg) => (
              <ChatMessage
                key={msg.id}
                msg={msg}
                onSaveRequest={handleSaveRequest}
              />
            ))}
            {loading && (
              <div className="flex items-start gap-2">
                <div className="rounded-2xl rounded-bl-sm bg-gray-100 px-3 py-2 text-sm text-gray-500">
                  <span className="animate-pulse">...</span>
                </div>
              </div>
            )}
            {savedRequest && (
              <p className="text-center text-xs text-green-600">
                Richiesta registrata. Grazie!
              </p>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input */}
          <form onSubmit={handleSubmit} className="border-t border-gray-200 p-3 flex gap-2">
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
              className="flex h-9 w-9 items-center justify-center rounded-xl bg-[#1D4E35] text-white hover:bg-[#163d29] disabled:opacity-40 transition-colors"
            >
              <span className="material-symbols-outlined text-base">send</span>
            </button>
          </form>
        </div>
      )}
    </>
  );
}
