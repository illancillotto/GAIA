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

function formatArticleLabel(sourceFile: string): string {
  const filename = sourceFile.split("/").pop() ?? sourceFile;
  return filename.replace(/\.(md|txt|rst)$/i, "");
}

function ArticleContent({ group }: { group: WikiArticleGroup }) {
  return (
    <div className="space-y-6">
      <div className="space-y-2 border-b border-gray-100 pb-4">
        <p className="label-caption text-[#1D4E35]">Documento indicizzato</p>
        <h2 className="text-xl font-semibold text-gray-900">{formatArticleLabel(group.source_file)}</h2>
        <p className="text-xs text-gray-400">{group.source_file}</p>
      </div>
      {group.chunks.map((chunk, i) => (
        <div key={i} className="space-y-1">
          {chunk.section_title ? (
            <h3 className="text-sm font-semibold uppercase tracking-wide text-[#1D4E35]">
              {chunk.section_title}
            </h3>
          ) : null}
          <p className="whitespace-pre-wrap text-sm leading-relaxed text-gray-700">{chunk.excerpt}</p>
        </div>
      ))}
    </div>
  );
}

function ChatPanel({
  contextArticle,
  messages,
  loading,
  error,
  onSend,
}: {
  contextArticle: string | undefined;
  messages: WikiChatMessage[];
  loading: boolean;
  error: string | null;
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
    <div className="flex min-h-[32rem] flex-col">
      <div className="border-b border-gray-100 pb-4">
        <p className="label-caption text-[#1D4E35]">Assistente</p>
        <p className="mt-1 text-sm font-semibold text-gray-900">Chat documentale</p>
        {contextArticle ? (
          <p className="mt-1 truncate text-xs text-gray-500">Contesto: {contextArticle}</p>
        ) : null}
      </div>

      <div className="mt-4 flex-1 space-y-3 overflow-y-auto rounded-xl border border-gray-100 bg-[#fafaf7] p-4">
        {messages.length === 0 ? (
          <p className="pt-8 text-center text-sm text-gray-400">
            Fai una domanda su questo documento o su GAIA in generale.
          </p>
        ) : null}
        {messages.map((msg) => (
          <div key={msg.id} className={cn("flex flex-col gap-1", msg.role === "user" ? "items-end" : "items-start")}>
            <div
              className={cn(
                "max-w-[90%] rounded-2xl px-3 py-2 text-sm leading-relaxed",
                msg.role === "user"
                  ? "rounded-br-sm bg-[#1D4E35] text-white"
                  : "rounded-bl-sm bg-gray-100 text-gray-900"
              )}
            >
              {msg.content}
            </div>
            {msg.role === "assistant" && msg.sources && msg.sources.length > 0 ? (
              <div className="flex flex-wrap gap-1 px-1">
                {msg.sources.map((s, i) => (
                  <span
                    key={i}
                    className="rounded border border-green-200 bg-green-50 px-1.5 py-0.5 text-xs text-green-700"
                  >
                    {s.source_file.split("/").pop()}
                  </span>
                ))}
              </div>
            ) : null}
            {msg.role === "assistant" && msg.found === false ? (
              <button
                onClick={() =>
                  saveWikiRequest({
                    user_question:
                      [...messages].reverse().find((m: WikiChatMessage) => m.role === "user")?.content ?? "",
                    agent_response: msg.content,
                    category: "feature_request",
                  })
                }
                className="ml-1 text-xs text-[#1D4E35] underline underline-offset-2 hover:opacity-70"
              >
                Registra richiesta
              </button>
            ) : null}
          </div>
        ))}
        {loading ? (
          <div className="flex items-start">
            <div className="rounded-2xl rounded-bl-sm bg-gray-100 px-3 py-2 text-sm text-gray-500">
              <span className="animate-pulse">...</span>
            </div>
          </div>
        ) : null}
        {error ? (
          <div className="rounded-xl border border-red-100 bg-red-50 px-3 py-2 text-xs text-red-700">{error}</div>
        ) : null}
      </div>

      <form onSubmit={handleSubmit} className="mt-4 flex gap-2">
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

  const { messages, loading, error, sendMessage } = useWikiChat(selected?.source_file);

  useEffect(() => {
    fetchArticles()
      .then((data) => {
        setArticles(data);
        if (data.length > 0) {
          setSelected(data[0]);
        }
      })
      .finally(() => setLoadingArticles(false));
  }, []);

  return (
    <div className="page-stack">
      <article className="panel-card border-[#e7eee8] bg-gradient-to-r from-white via-[#f9fbf7] to-[#f2f7f1]">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div className="space-y-2">
            <p className="label-caption text-[#1D4E35]">Knowledge Base</p>
            <h3 className="font-newsreader text-3xl text-[#173224]">Wiki operativa GAIA</h3>
            <p className="max-w-3xl text-sm leading-6 text-gray-600">
              Consulta la documentazione indicizzata e interroga l&apos;assistente sul documento selezionato o sul
              comportamento generale della piattaforma.
            </p>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="rounded-2xl border border-white/70 bg-white/80 px-4 py-3 shadow-sm">
              <p className="label-caption">Documenti</p>
              <p className="mt-1 text-2xl font-semibold text-gray-900">{articles.length}</p>
            </div>
            <div className="rounded-2xl border border-white/70 bg-white/80 px-4 py-3 shadow-sm">
              <p className="label-caption">Chat corrente</p>
              <p className="mt-1 text-2xl font-semibold text-gray-900">{messages.length}</p>
            </div>
          </div>
        </div>
      </article>

      <div className="grid gap-6 xl:grid-cols-[280px_minmax(0,1fr)_360px]">
        <article className="panel-card p-0">
          <div className="border-b border-gray-100 px-5 py-4">
            <p className="label-caption text-[#1D4E35]">Indice</p>
            <h3 className="mt-1 text-sm font-semibold text-gray-900">Documenti indicizzati</h3>
          </div>
          {loadingArticles ? <p className="p-5 text-sm text-gray-400">Caricamento...</p> : null}
          {!loadingArticles && articles.length === 0 ? (
            <div className="space-y-2 px-5 py-5 text-sm text-gray-500">
              <p>Nessun articolo indicizzato.</p>
              <p>
                Esegui <code className="rounded bg-gray-100 px-1.5 py-0.5 text-xs">make wiki-index</code> per
                popolare la wiki.
              </p>
            </div>
          ) : null}
          <nav className="max-h-[42rem] space-y-1 overflow-y-auto p-3">
            {articles.map((article) => (
              <button
                key={article.source_file}
                onClick={() => setSelected(article)}
                className={cn(
                  "w-full rounded-xl px-3 py-3 text-left text-sm transition-colors",
                  selected?.source_file === article.source_file
                    ? "bg-[#1D4E35] text-white"
                    : "text-gray-700 hover:bg-gray-50"
                )}
                title={article.source_file}
              >
                <span className="block truncate font-medium">{formatArticleLabel(article.source_file)}</span>
                <span
                  className={cn(
                    "mt-1 block text-xs",
                    selected?.source_file === article.source_file ? "text-white/70" : "text-gray-400"
                  )}
                >
                  {article.chunks.length} estratti indicizzati
                </span>
              </button>
            ))}
          </nav>
        </article>

        <article className="panel-card min-w-0">
          {selected ? (
            <div className="max-h-[42rem] overflow-y-auto pr-1">
              <ArticleContent group={selected} />
            </div>
          ) : (
            <div className="flex min-h-[32rem] items-center justify-center rounded-xl border border-dashed border-gray-200 bg-[#fafaf7] text-sm text-gray-400">
              Seleziona un documento dall&apos;indice per vedere il contenuto.
            </div>
          )}
        </article>

        <article className="panel-card">
          <ChatPanel
            contextArticle={selected?.source_file}
            messages={messages}
            loading={loading}
            error={error}
            onSend={sendMessage}
          />
        </article>
      </div>
    </div>
  );
}
