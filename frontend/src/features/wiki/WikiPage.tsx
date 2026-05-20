"use client";

import { useEffect, useState } from "react";

import { cn } from "@/lib/cn";
import type { WikiArticleGroup, WikiChatMessage, WikiRequestCreate } from "./types";
import { useWikiChat } from "./useWikiChat";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

async function fetchArticles(): Promise<WikiArticleGroup[]> {
  const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
  const res = await fetch(`${API_BASE}/api/wiki/articles`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) return [];
  return res.json();
}

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

function ArticleContent({ group }: { group: WikiArticleGroup }) {
  return (
    <div className="space-y-6">
      <h2 className="text-xl font-semibold text-gray-900">{group.source_file}</h2>
      {group.chunks.map((chunk, i) => (
        <div key={i} className="space-y-1">
          {chunk.section_title && (
            <h3 className="text-sm font-semibold text-[#1D4E35] uppercase tracking-wide">
              {chunk.section_title}
            </h3>
          )}
          <p className="text-sm text-gray-700 whitespace-pre-wrap leading-relaxed">
            {chunk.excerpt}
          </p>
        </div>
      ))}
    </div>
  );
}

function ChatPanel({
  contextArticle,
  messages,
  loading,
  onSend,
}: {
  contextArticle: string | undefined;
  messages: WikiChatMessage[];
  loading: boolean;
  onSend: (q: string) => void;
}) {
  const [input, setInput] = useState("");

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!input.trim()) return;
    onSend(input.trim());
    setInput("");
  }

  return (
    <div className="flex flex-col h-full border-l border-gray-200">
      <div className="bg-[#1D4E35] px-4 py-3">
        <p className="text-sm font-semibold text-white">Chat assistente</p>
        {contextArticle && (
          <p className="text-xs text-white/70 mt-0.5 truncate">Contesto: {contextArticle}</p>
        )}
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.length === 0 && (
          <p className="text-sm text-gray-400 text-center pt-8">
            Fai una domanda su questo documento o su GAIA in generale.
          </p>
        )}
        {messages.map((msg) => (
          <div key={msg.id} className={cn("flex flex-col gap-1", msg.role === "user" ? "items-end" : "items-start")}>
            <div
              className={cn(
                "max-w-[90%] rounded-2xl px-3 py-2 text-sm leading-relaxed",
                msg.role === "user"
                  ? "bg-[#1D4E35] text-white rounded-br-sm"
                  : "bg-gray-100 text-gray-900 rounded-bl-sm"
              )}
            >
              {msg.content}
            </div>
            {msg.role === "assistant" && msg.sources && msg.sources.length > 0 && (
              <div className="flex flex-wrap gap-1 px-1">
                {msg.sources.map((s, i) => (
                  <span key={i} className="text-xs bg-green-50 text-green-700 border border-green-200 rounded px-1.5 py-0.5">
                    {s.source_file.split("/").pop()}
                  </span>
                ))}
              </div>
            )}
            {msg.role === "assistant" && msg.found === false && (
              <button
                onClick={() => saveWikiRequest({
                  user_question: [...messages].reverse().find((m: WikiChatMessage) => m.role === "user")?.content ?? "",
                  agent_response: msg.content,
                  category: "feature_request",
                })}
                className="ml-1 text-xs text-[#1D4E35] underline underline-offset-2 hover:opacity-70"
              >
                Registra richiesta
              </button>
            )}
          </div>
        ))}
        {loading && (
          <div className="flex items-start">
            <div className="rounded-2xl rounded-bl-sm bg-gray-100 px-3 py-2 text-sm text-gray-500">
              <span className="animate-pulse">...</span>
            </div>
          </div>
        )}
      </div>

      <form onSubmit={handleSubmit} className="border-t border-gray-200 p-3 flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Domanda..."
          disabled={loading}
          className="flex-1 rounded-xl border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#1D4E35] disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={!input.trim() || loading}
          className="flex h-9 w-9 items-center justify-center rounded-xl bg-[#1D4E35] text-white disabled:opacity-40"
        >
          <span className="material-symbols-outlined text-base">send</span>
        </button>
      </form>
    </div>
  );
}

export function WikiPage() {
  const [articles, setArticles] = useState<WikiArticleGroup[]>([]);
  const [selected, setSelected] = useState<WikiArticleGroup | null>(null);
  const [loadingArticles, setLoadingArticles] = useState(true);

  const { messages, loading, sendMessage } = useWikiChat(selected?.source_file);

  useEffect(() => {
    fetchArticles()
      .then((data) => {
        setArticles(data);
        if (data.length > 0) setSelected(data[0]);
      })
      .finally(() => setLoadingArticles(false));
  }, []);

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar articoli */}
      <aside className="w-64 shrink-0 border-r border-gray-200 overflow-y-auto bg-gray-50">
        <div className="p-4 border-b border-gray-200">
          <h1 className="text-sm font-semibold text-gray-900 flex items-center gap-2">
            <span className="material-symbols-outlined text-[#1D4E35] text-base">menu_book</span>
            Wiki GAIA
          </h1>
        </div>
        {loadingArticles && (
          <p className="text-xs text-gray-400 p-4">Caricamento...</p>
        )}
        {!loadingArticles && articles.length === 0 && (
          <div className="p-4 text-xs text-gray-500 space-y-2">
            <p>Nessun articolo indicizzato.</p>
            <p>Eseguire <code className="bg-gray-100 px-1 rounded">make wiki-index</code> per indicizzare i documenti.</p>
          </div>
        )}
        <nav className="p-2 space-y-0.5">
          {articles.map((article) => (
            <button
              key={article.source_file}
              onClick={() => setSelected(article)}
              className={cn(
                "w-full text-left px-3 py-2 rounded-xl text-xs transition-colors truncate",
                selected?.source_file === article.source_file
                  ? "bg-[#1D4E35] text-white"
                  : "text-gray-700 hover:bg-gray-200"
              )}
              title={article.source_file}
            >
              {article.source_file.split("/").pop()}
            </button>
          ))}
        </nav>
      </aside>

      {/* Contenuto articolo */}
      <main className="flex-1 overflow-y-auto p-8">
        {selected ? (
          <ArticleContent group={selected} />
        ) : (
          <div className="flex items-center justify-center h-full text-gray-400 text-sm">
            Seleziona un documento dalla sidebar
          </div>
        )}
      </main>

      {/* Chat panel */}
      <aside className="w-80 shrink-0 flex flex-col bg-white">
        <ChatPanel
          contextArticle={selected?.source_file}
          messages={messages}
          loading={loading}
          onSend={sendMessage}
        />
      </aside>
    </div>
  );
}
