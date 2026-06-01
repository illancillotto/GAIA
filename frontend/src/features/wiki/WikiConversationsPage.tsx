"use client";

import { useEffect, useMemo, useState } from "react";

import { EmptyState } from "@/components/ui/empty-state";
import { SearchIcon } from "@/components/ui/icons";
import { buildWikiContextHref } from "./context-links";
import { getWikiToolAuditLogs, resolveWikiConversationContextLink } from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import type { CurrentUser, WikiToolAuditLog } from "@/types/api";
import type { WikiConversation, WikiConversationContextLink, WikiConversationSummary, WikiConversationSummaryMetrics } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

type StatusFilter = "all" | "open" | "in_review" | "waiting_user" | "resolved";
type PriorityFilter = "all" | "low" | "medium" | "high";
type ReviewReasonFilter = "all" | "denied_present" | "fallback_heavy" | "no_match_repeated" | "high_latency" | "manual_flag";
type ReviewFilter = "all" | "needs_review" | "clean";
type SortOption = "recent" | "oldest" | "denied" | "fallback" | "urgent";

async function fetchCurrentUser(): Promise<CurrentUser> {
  const token = getStoredAccessToken();
  const response = await fetch(`${API_BASE}/api/auth/me`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail ?? `Errore ${response.status}`);
  }
  return response.json();
}

async function fetchConversations(params: {
  search: string;
  status: StatusFilter;
  priority: PriorityFilter;
  assignedTo: string;
  reviewReason: ReviewReasonFilter;
  reviewFilter: ReviewFilter;
}): Promise<WikiConversationSummary[]> {
  const token = getStoredAccessToken();
  const query = new URLSearchParams({ limit: "100" });
  if (params.search.trim()) query.set("search", params.search.trim());
  if (params.status !== "all") query.set("status", params.status);
  if (params.priority !== "all") query.set("priority", params.priority);
  if (params.assignedTo.trim()) query.set("assigned_to", params.assignedTo.trim());
  if (params.reviewReason !== "all") query.set("review_reason", params.reviewReason);
  if (params.reviewFilter === "needs_review") query.set("needs_review", "true");
  if (params.reviewFilter === "clean") query.set("needs_review", "false");
  const response = await fetch(`${API_BASE}/api/wiki/conversations?${query.toString()}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail ?? `Errore ${response.status}`);
  }
  return response.json();
}

async function fetchConversationSummary(): Promise<WikiConversationSummaryMetrics> {
  const token = getStoredAccessToken();
  const response = await fetch(`${API_BASE}/api/wiki/conversations/summary`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail ?? `Errore ${response.status}`);
  }
  return response.json();
}

async function fetchConversationDetail(conversationId: string): Promise<WikiConversation> {
  const token = getStoredAccessToken();
  const response = await fetch(`${API_BASE}/api/wiki/conversations/${conversationId}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail ?? `Errore ${response.status}`);
  }
  return response.json();
}

async function patchConversation(
  conversationId: string,
  payload: Partial<Pick<WikiConversationSummary, "status" | "priority" | "assigned_to">>,
): Promise<void> {
  const token = getStoredAccessToken();
  const response = await fetch(`${API_BASE}/api/wiki/conversations/${conversationId}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail ?? `Errore ${response.status}`);
  }
}

function formatDate(value: string | null | undefined): string {
  if (!value) return "n/d";
  return new Intl.DateTimeFormat("it-IT", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(new Date(value));
}

function eventLabel(eventType: string): string {
  switch (eventType) {
    case "created":
      return "Thread creato";
    case "message_appended":
      return "Nuovo messaggio";
    case "status_changed":
      return "Cambio stato";
    case "priority_changed":
      return "Cambio priorita";
    case "assignment_changed":
      return "Cambio owner";
    case "flagged":
      return "Flag review";
    default:
      return eventType;
  }
}

function statusBadgeClasses(status: WikiConversationSummary["status"]): string {
  if (status === "resolved") return "bg-emerald-100 text-emerald-800";
  if (status === "in_review") return "bg-amber-100 text-amber-800";
  if (status === "waiting_user") return "bg-sky-100 text-sky-800";
  return "bg-[#fff6e8] text-[#8a5a00]";
}

function priorityBadgeClasses(priority: WikiConversationSummary["priority"]): string {
  if (priority === "high") return "bg-rose-100 text-rose-800";
  if (priority === "low") return "bg-slate-100 text-slate-700";
  return "bg-gray-100 text-gray-700";
}

function reasonLabel(reason: WikiConversationSummary["review_reason"]): string {
  switch (reason) {
    case "denied_present":
      return "Denied";
    case "fallback_heavy":
      return "Fallback heavy";
    case "no_match_repeated":
      return "No match";
    case "high_latency":
      return "High latency";
    case "manual_flag":
      return "Manual flag";
    default:
      return "n/d";
  }
}

function reasonHint(reason: WikiConversationSummary["review_reason"]): string {
  switch (reason) {
    case "denied_present":
      return "Possibile blocco policy o permesso tool.";
    case "fallback_heavy":
      return "Coverage tool insufficiente, forte dipendenza dai docs.";
    case "no_match_repeated":
      return "Dato mancante o chiave entità non risolta.";
    case "high_latency":
      return "Tempo risposta sopra soglia.";
    case "manual_flag":
      return "Flag manuale amministrativo.";
    default:
      return "Nessun segnale review attivo.";
  }
}

export function WikiConversationsPage() {
  const [currentUser, setCurrentUser] = useState<CurrentUser | null>(null);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [priorityFilter, setPriorityFilter] = useState<PriorityFilter>("all");
  const [assignedToFilter, setAssignedToFilter] = useState("");
  const [reviewReasonFilter, setReviewReasonFilter] = useState<ReviewReasonFilter>("all");
  const [reviewFilter, setReviewFilter] = useState<ReviewFilter>("all");
  const [sortBy, setSortBy] = useState<SortOption>("urgent");
  const [summary, setSummary] = useState<WikiConversationSummaryMetrics | null>(null);
  const [items, setItems] = useState<WikiConversationSummary[]>([]);
  const [selectedConversation, setSelectedConversation] = useState<WikiConversation | null>(null);
  const [selectedAuditLogs, setSelectedAuditLogs] = useState<WikiToolAuditLog[]>([]);
  const [selectedContextLink, setSelectedContextLink] = useState<WikiConversationContextLink | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    const [user, summaryData, data] = await Promise.all([
      fetchCurrentUser(),
      fetchConversationSummary(),
      fetchConversations({
        search,
        status: statusFilter,
        priority: priorityFilter,
        assignedTo: assignedToFilter,
        reviewReason: reviewReasonFilter,
        reviewFilter,
      }),
    ]);
    setCurrentUser(user);
    setSummary(summaryData);
    setItems(data);
    setError(null);
  }

  useEffect(() => {
    let active = true;
    setLoading(true);
    refresh()
      .catch((loadError) => {
        if (!active) return;
        setItems([]);
        setError(loadError instanceof Error ? loadError.message : "Errore caricamento conversazioni Wiki");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [search, statusFilter, priorityFilter, assignedToFilter, reviewReasonFilter, reviewFilter]);

  const grouped = useMemo(() => {
    const cloned = [...items];
    if (sortBy === "oldest") {
      cloned.sort((a, b) => new Date(a.updated_at).getTime() - new Date(b.updated_at).getTime());
      return cloned;
    }
    if (sortBy === "denied") {
      cloned.sort((a, b) => b.denied_count - a.denied_count || b.review_score - a.review_score);
      return cloned;
    }
    if (sortBy === "fallback") {
      cloned.sort((a, b) => b.fallback_count - a.fallback_count || b.review_score - a.review_score);
      return cloned;
    }
    if (sortBy === "urgent") {
      cloned.sort((a, b) => b.review_score - a.review_score || new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime());
      return cloned;
    }
    cloned.sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime());
    return cloned;
  }, [items, sortBy]);

  async function runQuickAction(
    conversationId: string,
    payload: Partial<Pick<WikiConversationSummary, "status" | "priority" | "assigned_to">>,
  ) {
    try {
      await patchConversation(conversationId, payload);
      await refresh();
    } catch (updateError) {
      setError(updateError instanceof Error ? updateError.message : "Errore aggiornamento conversazione");
    }
  }

  async function openConversationDetail(conversationId: string) {
    try {
      const token = getStoredAccessToken();
      if (!token) throw new Error("Sessione non disponibile.");
      const [detail, auditResponse] = await Promise.all([
        fetchConversationDetail(conversationId),
        getWikiToolAuditLogs(token, { conversationId, page: 1, pageSize: 2 }),
      ]);
      const contextLink = await resolveWikiConversationContextLink(token, {
        entityKey: detail.latest_entity_key,
        moduleKey: detail.top_module,
      });
      setSelectedConversation(detail);
      setSelectedAuditLogs(auditResponse.items);
      setSelectedContextLink(contextLink);
      setError(null);
    } catch (detailError) {
      setError(detailError instanceof Error ? detailError.message : "Errore caricamento dettaglio conversazione");
    }
  }

  if (error && !loading && items.length === 0) {
    return <EmptyState icon={SearchIcon} title="Conversazioni Wiki non disponibili" description={error} />;
  }

  return (
    <div className="space-y-6">
      <section>
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Thread persistiti</p>
        <h2 className="mt-1 text-xl font-semibold text-gray-900">Conversazioni Wiki</h2>
        <p className="mt-1 text-sm text-gray-500">Coda operativa dei thread Wiki con ownership, priorità e review backlog.</p>
      </section>

      <section className="grid gap-3 lg:grid-cols-7">
        <label className="space-y-1 lg:col-span-2">
          <span className="text-xs font-medium uppercase tracking-wide text-gray-400">Ricerca</span>
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="titolo, articolo, testo..."
            className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm text-gray-700 outline-none transition focus:border-[#1D4E35] focus:ring-2 focus:ring-[#1D4E35]/10"
          />
        </label>
        <label className="space-y-1">
          <span className="text-xs font-medium uppercase tracking-wide text-gray-400">Stato</span>
          <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value as StatusFilter)} className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm text-gray-700">
            <option value="all">Tutti</option>
            <option value="open">Open</option>
            <option value="in_review">In review</option>
            <option value="waiting_user">Waiting user</option>
            <option value="resolved">Resolved</option>
          </select>
        </label>
        <label className="space-y-1">
          <span className="text-xs font-medium uppercase tracking-wide text-gray-400">Priorità</span>
          <select value={priorityFilter} onChange={(event) => setPriorityFilter(event.target.value as PriorityFilter)} className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm text-gray-700">
            <option value="all">Tutte</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
        </label>
        <label className="space-y-1">
          <span className="text-xs font-medium uppercase tracking-wide text-gray-400">Review</span>
          <select value={reviewFilter} onChange={(event) => setReviewFilter(event.target.value as ReviewFilter)} className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm text-gray-700">
            <option value="all">Tutte</option>
            <option value="needs_review">Solo backlog</option>
            <option value="clean">Solo pulite</option>
          </select>
        </label>
        <label className="space-y-1">
          <span className="text-xs font-medium uppercase tracking-wide text-gray-400">Reason</span>
          <select value={reviewReasonFilter} onChange={(event) => setReviewReasonFilter(event.target.value as ReviewReasonFilter)} className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm text-gray-700">
            <option value="all">Tutte</option>
            <option value="denied_present">Denied</option>
            <option value="fallback_heavy">Fallback heavy</option>
            <option value="no_match_repeated">No match</option>
            <option value="high_latency">High latency</option>
            <option value="manual_flag">Manual flag</option>
          </select>
        </label>
        <label className="space-y-1">
          <span className="text-xs font-medium uppercase tracking-wide text-gray-400">Assegnatario</span>
          <input
            value={assignedToFilter}
            onChange={(event) => setAssignedToFilter(event.target.value)}
            placeholder="username"
            className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm text-gray-700 outline-none transition focus:border-[#1D4E35] focus:ring-2 focus:ring-[#1D4E35]/10"
          />
        </label>
        <label className="space-y-1">
          <span className="text-xs font-medium uppercase tracking-wide text-gray-400">Ordina</span>
          <select value={sortBy} onChange={(event) => setSortBy(event.target.value as SortOption)} className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm text-gray-700">
            <option value="urgent">Più urgenti</option>
            <option value="recent">Più recenti</option>
            <option value="oldest">Più vecchi</option>
            <option value="denied">Più denied</option>
            <option value="fallback">Più fallback</option>
          </select>
        </label>
      </section>

      <section className="grid gap-3 md:grid-cols-2 xl:grid-cols-6">
        <article className="rounded-2xl border border-gray-200 bg-white p-4 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Open</p>
          <p className="mt-2 text-2xl font-semibold text-gray-900">{summary?.open_count ?? 0}</p>
        </article>
        <article className="rounded-2xl border border-amber-200 bg-amber-50 p-4 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-amber-700">In review</p>
          <p className="mt-2 text-2xl font-semibold text-amber-900">{summary?.in_review_count ?? 0}</p>
        </article>
        <article className="rounded-2xl border border-sky-200 bg-sky-50 p-4 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-sky-700">Waiting user</p>
          <p className="mt-2 text-2xl font-semibold text-sky-900">{summary?.waiting_user_count ?? 0}</p>
        </article>
        <article className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">Resolved</p>
          <p className="mt-2 text-2xl font-semibold text-emerald-900">{summary?.resolved_count ?? 0}</p>
        </article>
        <article className="rounded-2xl border border-rose-200 bg-rose-50 p-4 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-rose-700">High priority</p>
          <p className="mt-2 text-2xl font-semibold text-rose-900">{summary?.high_priority_count ?? 0}</p>
        </article>
        <article className="rounded-2xl border border-gray-200 bg-white p-4 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Da rivedere</p>
          <p className="mt-2 text-2xl font-semibold text-gray-900">{summary?.needs_review_count ?? 0}</p>
          <p className="mt-1 text-sm text-gray-500">Non assegnate: {summary?.unassigned_review_count ?? 0}</p>
        </article>
      </section>

      <section className="grid gap-3 lg:grid-cols-2">
        <article className="rounded-2xl border border-gray-200 bg-white p-4 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Backlog review</p>
          <h3 className="mt-1 text-lg font-semibold text-gray-900">Conversazioni da rivedere</h3>
          <p className="mt-1 text-sm text-gray-500">
            Open con denied o fallback: {summary?.open_denied_count ?? 0} / {summary?.open_fallback_count ?? 0}
          </p>
          <div className="mt-3 space-y-2">
            {(summary?.items_needing_review ?? []).map((conversation) => (
              <div key={`review-${conversation.id}`} className="rounded-xl border border-amber-200 bg-amber-50/50 p-3">
                <a href={`/wiki?conversation=${conversation.id}`} className="font-medium text-gray-900 hover:text-[#1D4E35]">
                  {conversation.title}
                </a>
                <p className="mt-1 text-xs text-gray-600">
                  {reasonLabel(conversation.review_reason)} · denied {conversation.denied_count} · fallback {conversation.fallback_count} · no match {conversation.no_match_count}
                </p>
              </div>
            ))}
          </div>
        </article>
        <article className="rounded-2xl border border-gray-200 bg-white p-4 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Trend rapido</p>
          <h3 className="mt-1 text-lg font-semibold text-gray-900">Ownership e tempi</h3>
          <p className="mt-2 text-sm text-gray-600">Tempo medio prima review: {summary?.avg_time_to_review_hours ?? 0}h</p>
          <p className="mt-1 text-sm text-gray-600">Tempo medio risoluzione: {summary?.avg_time_to_resolve_hours ?? 0}h</p>
          <p className="mt-3 text-sm text-gray-600">Top tool: {summary?.top_tool ?? "n/d"} · Top mode: {summary?.top_mode ?? "n/d"}</p>
          <p className="mt-1 text-sm text-gray-600">Top review reason: {summary?.top_review_reasons?.[0]?.key ?? "n/d"}</p>
        </article>
      </section>

      <section className="grid gap-4 xl:grid-cols-[minmax(0,2fr)_minmax(320px,1fr)]">
        <div className="grid gap-3 md:grid-cols-2">
        {grouped.length > 0 ? grouped.map((conversation) => (
          <article key={conversation.id} className="rounded-2xl border border-gray-200 bg-white p-4 shadow-sm">
            <a href={`/wiki?conversation=${conversation.id}`} className="block transition hover:text-[#1D4E35]">
              <div className="flex flex-wrap items-start gap-2">
                <p className="min-w-0 flex-1 truncate font-medium text-gray-900">{conversation.title}</p>
                <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${statusBadgeClasses(conversation.status)}`}>{conversation.status}</span>
                <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${priorityBadgeClasses(conversation.priority)}`}>{conversation.priority}</span>
              </div>
              <p className="mt-1 text-xs text-gray-500">
                {conversation.message_count} messaggi
                {conversation.context_article ? ` · ${conversation.context_article.split("/").pop()}` : ""}
              </p>
            </a>
            <div className="mt-3 grid gap-1 text-xs text-gray-500">
              <p>Creato da {conversation.created_by} · owner {conversation.assigned_to ?? "non assegnato"}</p>
              <p>Review reason: {reasonLabel(conversation.review_reason)}</p>
              <p>{reasonHint(conversation.review_reason)}</p>
              <p>Denied {conversation.denied_count} · fallback {conversation.fallback_count} · no match {conversation.no_match_count}</p>
              <p>Ultimo evento {conversation.last_event_type ?? "n/d"} · riaperture {conversation.reopen_count}</p>
              <p>{conversation.top_tool_name ? `${conversation.top_tool_name}` : "Nessun tool"}{conversation.last_mode ? ` · ${conversation.last_mode}` : ""}</p>
              <p>{conversation.top_module ?? "modulo n/d"} · {conversation.top_intent ?? "intent n/d"}</p>
              <p>Aggiornato {formatDate(conversation.updated_at)} · last reviewed {formatDate(conversation.last_reviewed_at)}</p>
            </div>
            <div className="mt-3 flex flex-wrap gap-2 text-xs">
              <button type="button" onClick={() => void openConversationDetail(conversation.id)} className="rounded-full bg-[#eef6ef] px-3 py-1 font-medium text-[#1D4E35]">
                Dettaglio
              </button>
              {currentUser ? (
                <button type="button" onClick={() => void runQuickAction(conversation.id, { assigned_to: currentUser.username })} className="rounded-full bg-gray-100 px-3 py-1 font-medium text-gray-700">
                  Assegna a me
                </button>
              ) : null}
              <button type="button" onClick={() => void runQuickAction(conversation.id, { priority: conversation.priority === "high" ? "medium" : "high" })} className="rounded-full bg-rose-50 px-3 py-1 font-medium text-rose-700">
                {conversation.priority === "high" ? "Priorità media" : "Priorità alta"}
              </button>
              <button type="button" onClick={() => void runQuickAction(conversation.id, { status: "in_review" })} className="rounded-full bg-amber-50 px-3 py-1 font-medium text-amber-700">
                Metti in review
              </button>
              <button type="button" onClick={() => void runQuickAction(conversation.id, { status: "waiting_user" })} className="rounded-full bg-sky-50 px-3 py-1 font-medium text-sky-700">
                Waiting user
              </button>
              <button type="button" onClick={() => void runQuickAction(conversation.id, { status: conversation.status === "resolved" ? "open" : "resolved" })} className="rounded-full bg-emerald-50 px-3 py-1 font-medium text-emerald-700">
                {conversation.status === "resolved" ? "Riapri" : "Risolvi"}
              </button>
            </div>
          </article>
        )) : (
          <div className="rounded-2xl border border-dashed border-gray-200 bg-[#fafaf7] px-4 py-6 text-sm text-gray-500">
            {loading ? "Caricamento conversazioni..." : "Nessuna conversazione corrisponde al filtro corrente."}
          </div>
        )}
        </div>
        <aside className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Dettaglio thread</p>
          {selectedConversation ? (
            <div className="mt-3 space-y-3">
              <div>
                <h3 className="text-lg font-semibold text-gray-900">{selectedConversation.title}</h3>
                <p className="mt-1 text-sm text-gray-500">{selectedConversation.created_by} · {selectedConversation.assigned_to ?? "non assegnato"}</p>
              </div>
              <div className="grid gap-2 text-sm text-gray-600">
                <p>Status: <span className="font-medium text-gray-900">{selectedConversation.status}</span></p>
                <p>Priority: <span className="font-medium text-gray-900">{selectedConversation.priority}</span></p>
                <p>Review reason: <span className="font-medium text-gray-900">{reasonLabel(selectedConversation.review_reason)}</span></p>
                <p>Diagnosi: <span className="font-medium text-gray-900">{reasonHint(selectedConversation.review_reason)}</span></p>
                <p>Denied {selectedConversation.denied_count} · fallback {selectedConversation.fallback_count} · no match {selectedConversation.no_match_count}</p>
                <p>Mode: <span className="font-medium text-gray-900">{selectedConversation.last_mode ?? "n/d"}</span></p>
                <p>Tool: <span className="font-medium text-gray-900">{selectedConversation.top_tool_name ?? "n/d"}</span></p>
                <p>Modulo: <span className="font-medium text-gray-900">{selectedConversation.top_module ?? "n/d"}</span></p>
                <p>Intent: <span className="font-medium text-gray-900">{selectedConversation.top_intent ?? "n/d"}</span></p>
                <p>Entity key: <span className="break-all font-medium text-gray-900">{selectedConversation.latest_entity_key ?? "n/d"}</span></p>
                <p>Contesto: <span className="font-medium text-gray-900">{selectedConversation.latest_context_article ?? selectedConversation.context_article ?? "n/d"}</span></p>
                <p>Ultimo evento: <span className="font-medium text-gray-900">{selectedConversation.last_event_type ?? "n/d"}</span></p>
                <p>Ultimo cambio owner: <span className="font-medium text-gray-900">{formatDate(selectedConversation.last_owner_change_at)}</span></p>
                <p>Riaperture: <span className="font-medium text-gray-900">{selectedConversation.reopen_count}</span></p>
              </div>
              <div className="flex flex-wrap gap-2 text-xs">
                <a href={`/wiki?conversation=${selectedConversation.id}`} className="rounded-full bg-[#eef6ef] px-3 py-1 font-medium text-[#1D4E35]">Apri conversazione</a>
                <a href={`/wiki/audit?conversation_id=${selectedConversation.id}`} className="rounded-full bg-gray-100 px-3 py-1 font-medium text-gray-700">Apri audit correlato</a>
                {(selectedContextLink?.href ?? buildWikiContextHref(selectedConversation.latest_entity_key, selectedConversation.top_module)) ? (
                  <a
                    href={selectedContextLink?.href ?? buildWikiContextHref(selectedConversation.latest_entity_key, selectedConversation.top_module) ?? "#"}
                    className="rounded-full bg-sky-50 px-3 py-1 font-medium text-sky-700"
                  >
                    {selectedContextLink?.resolved ? "Apri record modulo" : "Apri contesto modulo"}
                  </a>
                ) : null}
              </div>
              <div className="rounded-xl bg-[#f7f8f5] p-3 text-xs text-gray-600">
                <p className="font-medium text-gray-900">Messaggi: {selectedConversation.messages.length}</p>
                <p className="mt-1">Ultimo aggiornamento {formatDate(selectedConversation.updated_at)}</p>
              </div>
              <div className="rounded-xl border border-gray-200 p-3">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Timeline</p>
                <div className="mt-2 space-y-2">
                  {selectedConversation.events.length > 0 ? selectedConversation.events.map((event) => (
                    <div key={event.id} className="rounded-lg bg-[#f7f8f5] p-2 text-xs text-gray-600">
                      <p className="font-medium text-gray-900">{eventLabel(event.event_type)}</p>
                      <p className="mt-1">
                        {event.actor_username ?? "system"} · {formatDate(event.created_at)}
                      </p>
                      {event.from_status || event.to_status ? (
                        <p className="mt-1">
                          {event.from_status ?? "n/d"} → {event.to_status ?? "n/d"}
                        </p>
                      ) : null}
                      {event.payload ? (
                        <p className="mt-1 break-all">
                          {Object.entries(event.payload).map(([key, value]) => `${key}: ${String(value)}`).join(" · ")}
                        </p>
                      ) : null}
                    </div>
                  )) : (
                    <p className="text-xs text-gray-500">Nessun evento registrato per questo thread.</p>
                  )}
                </div>
              </div>
              <div className="rounded-xl border border-gray-200 p-3">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Ultimi audit</p>
                <div className="mt-2 space-y-2">
                  {selectedAuditLogs.length > 0 ? selectedAuditLogs.map((item) => (
                    <div key={item.id} className="rounded-lg bg-[#f7f8f5] p-2 text-xs text-gray-600">
                      <p className="font-medium text-gray-900">{item.tool_name} · {item.mode}</p>
                      <p className="mt-1">{item.question_preview}</p>
                      <p className="mt-1">
                        {item.success ? "ok" : "denied"} · {item.fallback_reason ?? "no fallback"} · {item.found ? "found" : "no match"}
                      </p>
                    </div>
                  )) : (
                    <p className="text-xs text-gray-500">Nessun audit recente per questo thread.</p>
                  )}
                </div>
              </div>
            </div>
          ) : (
            <p className="mt-3 text-sm text-gray-500">Seleziona un thread per vedere metadata completi, contatori review e shortcut amministrativi.</p>
          )}
        </aside>
      </section>

      {error ? (
        <article className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</article>
      ) : null}
    </div>
  );
}
