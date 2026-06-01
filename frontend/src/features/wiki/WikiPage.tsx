"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";

import { getStoredAccessToken } from "@/lib/auth";
import { cn } from "@/lib/cn";
import { EvidenceBadge, ModeBadge, ToolCallBadge } from "./message-metadata";
import type { WikiArticleGroup, WikiChatMessage, WikiRequestCreate } from "./types";
import { useWikiChat } from "./useWikiChat";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

async function fetchArticles(): Promise<WikiArticleGroup[]> {
  const token = getStoredAccessToken();
  const res = await fetch(`${API_BASE}/api/wiki/articles`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) return [];
  return res.json();
}

async function saveWikiRequest(payload: WikiRequestCreate): Promise<void> {
  const token = getStoredAccessToken();
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
  scope,
  onScopeChange,
  messages,
  loading,
  error,
  onSend,
}: {
  contextArticle: string | undefined;
  scope: "article" | "codebase";
  onScopeChange: (scope: "article" | "codebase") => void;
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
    <div className="flex h-full min-h-[28rem] flex-col">
      <div className="border-b border-gray-100 pb-4">
        <p className="label-caption text-[#1D4E35]">Assistente</p>
        <p className="mt-1 text-sm font-semibold text-gray-900">Chat documentale</p>
        <div className="mt-3 inline-flex rounded-xl border border-gray-200 bg-[#f7f8f5] p-1">
          <button
            type="button"
            onClick={() => onScopeChange("article")}
            className={cn(
              "rounded-lg px-3 py-1.5 text-xs font-medium transition",
              scope === "article" ? "bg-white text-[#1D4E35] shadow-sm" : "text-gray-500 hover:text-gray-700"
            )}
          >
            Documento selezionato
          </button>
          <button
            type="button"
            onClick={() => onScopeChange("codebase")}
            className={cn(
              "rounded-lg px-3 py-1.5 text-xs font-medium transition",
              scope === "codebase" ? "bg-white text-[#1D4E35] shadow-sm" : "text-gray-500 hover:text-gray-700"
            )}
          >
            Intera codebase
          </button>
        </div>
        {scope === "article" && contextArticle ? (
          <p className="mt-1 truncate text-xs text-gray-500">Contesto: {contextArticle}</p>
        ) : null}
        {scope === "codebase" ? (
          <p className="mt-1 text-xs text-gray-500">Ricerca su documentazione e codice indicizzati.</p>
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
            {msg.role === "assistant" ? (
              <div className="flex max-w-[90%] flex-wrap gap-1 px-1">
                <ModeBadge mode={msg.mode} />
                {msg.tool_calls?.map((toolCall, index) => (
                  <ToolCallBadge key={`${toolCall.tool_name}-${index}`} toolCall={toolCall} />
                ))}
              </div>
            ) : null}
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
            {msg.role === "assistant" && msg.evidences && msg.evidences.length > 0 ? (
              <div className="grid max-w-[90%] gap-1.5 px-1">
                {msg.evidences.map((evidence, index) => (
                  <EvidenceBadge key={`${evidence.source_key}-${index}`} evidence={evidence} />
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
  const searchParams = useSearchParams();
  const [articles, setArticles] = useState<WikiArticleGroup[]>([]);
  const [selected, setSelected] = useState<WikiArticleGroup | null>(null);
  const [loadingArticles, setLoadingArticles] = useState(true);
  const [articleQuery, setArticleQuery] = useState("");
  const initialConversationId = searchParams.get("conversation");

  const [chatScope, setChatScope] = useState<"article" | "codebase">("codebase");
  const {
    messages,
    conversationId,
    conversations,
    loading,
    error,
    sendMessage,
    loadConversation,
  } = useWikiChat(chatScope === "article" ? selected?.source_file : undefined, initialConversationId);
  const normalizedQuery = articleQuery.trim().toLowerCase();
  const filteredArticles = normalizedQuery
    ? articles.filter((article) => {
        const label = formatArticleLabel(article.source_file).toLowerCase();
        return (
          label.includes(normalizedQuery) ||
          article.source_file.toLowerCase().includes(normalizedQuery)
        );
      })
    : articles;

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

  useEffect(() => {
    if (filteredArticles.length === 0) {
      return;
    }

    if (!selected || !filteredArticles.some((article) => article.source_file === selected.source_file)) {
      setSelected(filteredArticles[0]);
    }
  }, [filteredArticles, selected]);

  return (
    <div className="space-y-4">
      <div className="grid items-start gap-4 xl:grid-cols-[minmax(0,1fr)_420px]">
        <article className="panel-card border-[#e7eee8] bg-gradient-to-r from-white via-[#fbfcf8] to-[#f3f7f0] px-5 py-4">
          <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-3">
                <p className="label-caption text-[#1D4E35]">Knowledge Base</p>
                <span className="rounded-full bg-[#eaf4ec] px-2.5 py-1 text-[11px] font-semibold text-[#1D4E35]">
                  {articles.length} documenti
                </span>
                <span className="rounded-full bg-white px-2.5 py-1 text-[11px] font-semibold text-gray-600 ring-1 ring-[#dbe7dc]">
                  {messages.length} messaggi
                </span>
              </div>
              <h3 className="mt-2 font-newsreader text-2xl text-[#173224]">Wiki operativa GAIA</h3>
              <p className="mt-1 max-w-3xl text-sm text-gray-600">
                Indice, assistente e documento nello stesso workspace. L&apos;assistente resta subito visibile senza scorrere la pagina.
              </p>
            </div>
          </div>
        </article>

        <article className="panel-card min-w-0 xl:sticky xl:top-4">
          <ChatPanel
            contextArticle={selected?.source_file}
            scope={chatScope}
            onScopeChange={setChatScope}
            messages={messages}
            loading={loading}
            error={error}
            onSend={sendMessage}
          />
        </article>
      </div>

      <article className="panel-card">
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="label-caption text-[#1D4E35]">Conversazioni</p>
            <p className="mt-1 text-sm text-gray-500">Thread recenti del Wiki Agent.</p>
          </div>
          <span className="rounded-full bg-[#f3f7f0] px-2.5 py-1 text-[11px] font-semibold text-[#1D4E35]">
            {conversations.length} thread
          </span>
        </div>
        <div className="mt-4 grid gap-2 md:grid-cols-2 xl:grid-cols-3">
          {conversations.length > 0 ? conversations.map((conversation) => (
            <button
              key={conversation.id}
              type="button"
              onClick={() => void loadConversation(conversation.id)}
              className={cn(
                "rounded-xl border px-3 py-3 text-left text-sm transition",
                conversation.id === conversationId
                  ? "border-[#1D4E35] bg-[#f8fbf8]"
                  : "border-gray-200 bg-white hover:border-[#1D4E35]/30"
              )}
            >
              <p className="truncate font-medium text-gray-900">{conversation.title}</p>
              <p className="mt-1 text-xs text-gray-500">
                {conversation.message_count} messaggi
                {conversation.context_article ? ` · ${formatArticleLabel(conversation.context_article)}` : ""}
              </p>
            </button>
          )) : <p className="text-sm text-gray-400">Nessuna conversazione salvata.</p>}
        </div>
      </article>

      <div className="grid items-start gap-4 xl:grid-cols-[420px_minmax(0,1fr)]">
        <article className="panel-card h-[calc(100vh-12rem)] min-h-[32rem] p-0 xl:sticky xl:top-4">
          <div className="border-b border-gray-100 px-5 py-4">
            <p className="label-caption text-[#1D4E35]">Indice</p>
            <h3 className="mt-1 text-sm font-semibold text-gray-900">Documenti indicizzati</h3>
            <p className="mt-1 text-xs text-gray-400">
              {filteredArticles.length} di {articles.length} documenti visibili
            </p>
            <div className="mt-3">
              <input
                value={articleQuery}
                onChange={(e) => setArticleQuery(e.target.value)}
                placeholder="Filtra documenti..."
                className="w-full rounded-xl border border-gray-200 bg-white px-3 py-2 text-sm text-gray-700 outline-none transition focus:border-[#1D4E35] focus:ring-2 focus:ring-[#1D4E35]/10"
              />
            </div>
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
          {!loadingArticles && articles.length > 0 && filteredArticles.length === 0 ? (
            <div className="px-5 py-5 text-sm text-gray-500">
              Nessun documento corrisponde al filtro corrente.
            </div>
          ) : null}
          <div className="h-[calc(100%-7.75rem)] overflow-y-auto p-3">
            <nav className="grid gap-2 sm:grid-cols-2">
              {filteredArticles.map((article) => (
                <button
                  key={article.source_file}
                  onClick={() => setSelected(article)}
                  className={cn(
                    "w-full rounded-xl border px-3 py-3 text-left text-sm transition-colors",
                    selected?.source_file === article.source_file
                      ? "border-[#1D4E35] bg-[#1D4E35] text-white"
                      : "border-[#dfe7e1] bg-white text-gray-700 hover:bg-[#f8fbf8]"
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
                    {article.chunks.length} estratti
                  </span>
                  <span
                    className={cn(
                      "mt-1 block truncate text-[11px]",
                      selected?.source_file === article.source_file ? "text-white/65" : "text-gray-350"
                    )}
                  >
                    {article.source_file}
                  </span>
                </button>
              ))}
            </nav>
          </div>
        </article>

        <div className="grid gap-4">
          <article className="panel-card h-[calc(100vh-28rem)] min-h-[22rem] min-w-0">
            <div className="border-b border-gray-100 pb-4">
              <p className="label-caption text-[#1D4E35]">Contenuto</p>
              <h3 className="mt-1 text-sm font-semibold text-gray-900">
                {selected ? formatArticleLabel(selected.source_file) : "Documento"}
              </h3>
            </div>

            <div className="mt-5 h-[calc(100%-4rem)]">
              {selected ? (
                <div className="h-full overflow-y-auto pr-1">
                  <ArticleContent group={selected} />
                </div>
              ) : (
                <div className="flex h-full items-center justify-center rounded-xl border border-dashed border-gray-200 bg-[#fafaf7] text-sm text-gray-400">
                  Seleziona un documento dall&apos;indice per vedere il contenuto.
                </div>
              )}
            </div>
          </article>
        </div>
      </div>
    </div>
  );
}
