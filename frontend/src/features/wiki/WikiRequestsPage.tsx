"use client";

import { useDeferredValue, useEffect, useMemo, useState } from "react";

import { EmptyState } from "@/components/ui/empty-state";
import { MetricCard } from "@/components/ui/metric-card";
import { SearchIcon } from "@/components/ui/icons";
import { getWikiRequestAssignees, getWikiRequests, updateWikiRequest } from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import type { WikiRequest, WikiRequestAssignee } from "@/types/api";

type RequestStatusFilter = "all" | "pending" | "reviewed" | "planned" | "done";
type RequestCategoryFilter = "all" | "feature_request" | "bug_report" | "question";
type RequestPriorityFilter = "all" | "low" | "medium" | "high" | "urgent";

const statusOptions: Array<{ value: RequestStatusFilter; label: string }> = [
  { value: "all", label: "Tutti gli stati" },
  { value: "pending", label: "Pending" },
  { value: "reviewed", label: "Reviewed" },
  { value: "planned", label: "Planned" },
  { value: "done", label: "Done" },
];

const categoryOptions: Array<{ value: RequestCategoryFilter; label: string }> = [
  { value: "all", label: "Tutte le categorie" },
  { value: "feature_request", label: "Feature request" },
  { value: "bug_report", label: "Bug report" },
  { value: "question", label: "Question" },
];

const priorityOptions: Array<{ value: RequestPriorityFilter; label: string }> = [
  { value: "all", label: "Tutte le priorità" },
  { value: "low", label: "Bassa" },
  { value: "medium", label: "Media" },
  { value: "high", label: "Alta" },
  { value: "urgent", label: "Urgente" },
];

function statusBadgeClasses(status: WikiRequest["status"]): string {
  switch (status) {
    case "done":
      return "border-green-200 bg-green-50 text-green-700";
    case "planned":
      return "border-blue-200 bg-blue-50 text-blue-700";
    case "reviewed":
      return "border-amber-200 bg-amber-50 text-amber-700";
    default:
      return "border-red-200 bg-red-50 text-red-700";
  }
}

function categoryLabel(category: WikiRequest["category"]): string {
  if (category === "feature_request") return "Feature request";
  if (category === "bug_report") return "Bug report";
  if (category === "question") return "Question";
  return category;
}

function priorityBadgeClasses(priority: WikiRequest["priority"]): string {
  switch (priority) {
    case "urgent":
      return "border-red-200 bg-red-50 text-red-700";
    case "high":
      return "border-amber-200 bg-amber-50 text-amber-700";
    case "low":
      return "border-gray-200 bg-gray-50 text-gray-600";
    default:
      return "border-blue-200 bg-blue-50 text-blue-700";
  }
}

function priorityLabel(priority: WikiRequest["priority"]): string {
  if (priority === "low") return "Bassa";
  if (priority === "medium") return "Media";
  if (priority === "high") return "Alta";
  if (priority === "urgent") return "Urgente";
  return priority;
}

function formatDateTime(value: string): string {
  try {
    return new Intl.DateTimeFormat("it-IT", {
      dateStyle: "short",
      timeStyle: "short",
    }).format(new Date(value));
  } catch {
    return value;
  }
}

export function WikiRequestsPage() {
  const [items, setItems] = useState<WikiRequest[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<RequestStatusFilter>("all");
  const [categoryFilter, setCategoryFilter] = useState<RequestCategoryFilter>("all");
  const [priorityFilter, setPriorityFilter] = useState<RequestPriorityFilter>("all");
  const [query, setQuery] = useState("");
  const [draftStatus, setDraftStatus] = useState<WikiRequest["status"]>("pending");
  const [draftPriority, setDraftPriority] = useState<WikiRequest["priority"]>("medium");
  const [draftAssignedTo, setDraftAssignedTo] = useState("");
  const [draftNotes, setDraftNotes] = useState("");
  const [assignees, setAssignees] = useState<WikiRequestAssignee[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const deferredQuery = useDeferredValue(query.trim().toLowerCase());

  useEffect(() => {
    async function loadRequests() {
      const token = getStoredAccessToken();
      if (!token) {
        setError("Sessione non disponibile.");
        setItems([]);
        setLoading(false);
        return;
      }

      setLoading(true);
      try {
        const [requestsResponse, assigneesResponse] = await Promise.all([
          getWikiRequests(token),
          getWikiRequestAssignees(token),
        ]);
        setItems(requestsResponse);
        setAssignees(assigneesResponse);
        setSelectedId((current) => current ?? requestsResponse[0]?.id ?? null);
        setError(null);
      } catch (loadError) {
        setItems([]);
        setAssignees([]);
        setSelectedId(null);
        setError(loadError instanceof Error ? loadError.message : "Errore caricamento richieste Wiki");
      } finally {
        setLoading(false);
      }
    }

    void loadRequests();
  }, []);

  const filteredItems = useMemo(() => {
    return items.filter((item) => {
      if (statusFilter !== "all" && item.status !== statusFilter) {
        return false;
      }
      if (categoryFilter !== "all" && item.category !== categoryFilter) {
        return false;
      }
      if (priorityFilter !== "all" && item.priority !== priorityFilter) {
        return false;
      }
      if (!deferredQuery) {
        return true;
      }
      const haystack = [
        item.user_question,
        item.agent_response ?? "",
        item.created_by ?? "",
        item.admin_notes ?? "",
        item.assigned_to ?? "",
        item.assigned_to_name ?? "",
        item.category,
        item.status,
        item.priority,
      ]
        .join(" ")
        .toLowerCase();
      return haystack.includes(deferredQuery);
    });
  }, [items, statusFilter, categoryFilter, priorityFilter, deferredQuery]);

  const selectedRequest = useMemo(
    () => filteredItems.find((item) => item.id === selectedId) ?? items.find((item) => item.id === selectedId) ?? null,
    [filteredItems, items, selectedId],
  );

  useEffect(() => {
    if (!selectedRequest) {
      if (filteredItems[0]) {
        setSelectedId(filteredItems[0].id);
      }
      return;
    }
    setDraftStatus(selectedRequest.status);
    setDraftPriority(selectedRequest.priority);
    setDraftAssignedTo(selectedRequest.assigned_to ?? "");
    setDraftNotes(selectedRequest.admin_notes ?? "");
    setSuccessMessage(null);
  }, [selectedRequest, filteredItems]);

  const summary = useMemo(() => {
    return {
      total: items.length,
      pending: items.filter((item) => item.status === "pending").length,
      planned: items.filter((item) => item.status === "planned").length,
      urgent: items.filter((item) => item.priority === "urgent").length,
      done: items.filter((item) => item.status === "done").length,
    };
  }, [items]);

  async function handleSave() {
    if (!selectedRequest) {
      return;
    }
    const token = getStoredAccessToken();
    if (!token) {
      setError("Sessione non disponibile.");
      return;
    }

    setSaving(true);
    setSuccessMessage(null);
    try {
      const updated = await updateWikiRequest(token, selectedRequest.id, {
        status: draftStatus,
        priority: draftPriority as "low" | "medium" | "high" | "urgent",
        assigned_to: draftAssignedTo || null,
        admin_notes: draftNotes || null,
      });
      setItems((current) => current.map((item) => (item.id === updated.id ? updated : item)));
      setSuccessMessage("Richiesta aggiornata.");
      setError(null);
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Errore aggiornamento richiesta Wiki");
    } finally {
      setSaving(false);
    }
  }

  if (error && !loading && items.length === 0) {
    return <EmptyState icon={SearchIcon} title="Richieste Wiki non disponibili" description={error} />;
  }

  return (
    <div className="space-y-6">
      <section className="grid gap-4 md:grid-cols-3 xl:grid-cols-5">
        <MetricCard label="Totale richieste" value={summary.total.toString()} sub="storico registrato" />
        <MetricCard label="Pending" value={summary.pending.toString()} sub="da prendere in carico" />
        <MetricCard label="Urgenti" value={summary.urgent.toString()} sub="da trattare subito" />
        <MetricCard label="Planned" value={summary.planned.toString()} sub="in roadmap" />
        <MetricCard label="Done" value={summary.done.toString()} sub="chiuse" />
      </section>

      <section className="rounded-3xl border border-[#d9dfd4] bg-white p-5 shadow-sm">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Governance richieste</p>
            <h2 className="mt-1 text-xl font-semibold text-gray-900">Richieste registrate dal Wiki</h2>
            <p className="mt-1 text-sm text-gray-500">
              Le richieste vengono generate dai fallback `found=false` del widget e della pagina Wiki.
            </p>
          </div>
          <div className="grid gap-3 md:grid-cols-4">
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Cerca per testo, autore o note"
              className="rounded-xl border border-gray-200 px-3 py-2 text-sm text-gray-700 outline-none transition focus:border-[#1D4E35] focus:ring-2 focus:ring-[#1D4E35]/10"
            />
            <select
              value={statusFilter}
              onChange={(event) => setStatusFilter(event.target.value as RequestStatusFilter)}
              className="rounded-xl border border-gray-200 px-3 py-2 text-sm text-gray-700 outline-none transition focus:border-[#1D4E35] focus:ring-2 focus:ring-[#1D4E35]/10"
            >
              {statusOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
            <select
              value={categoryFilter}
              onChange={(event) => setCategoryFilter(event.target.value as RequestCategoryFilter)}
              className="rounded-xl border border-gray-200 px-3 py-2 text-sm text-gray-700 outline-none transition focus:border-[#1D4E35] focus:ring-2 focus:ring-[#1D4E35]/10"
            >
              {categoryOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
            <select
              value={priorityFilter}
              onChange={(event) => setPriorityFilter(event.target.value as RequestPriorityFilter)}
              className="rounded-xl border border-gray-200 px-3 py-2 text-sm text-gray-700 outline-none transition focus:border-[#1D4E35] focus:ring-2 focus:ring-[#1D4E35]/10"
            >
              {priorityOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-[minmax(0,1.1fr)_minmax(24rem,0.9fr)]">
        <article className="rounded-3xl border border-[#d9dfd4] bg-white p-4 shadow-sm">
          <div className="flex items-center justify-between gap-3 border-b border-gray-100 pb-3">
            <div>
              <p className="text-sm font-semibold text-gray-900">Coda richieste</p>
              <p className="text-xs text-gray-500">{filteredItems.length} elementi nel filtro corrente.</p>
            </div>
          </div>
          <div className="mt-4 space-y-3">
            {loading ? (
              <p className="text-sm text-gray-500">Caricamento richieste...</p>
            ) : filteredItems.length === 0 ? (
              <EmptyState icon={SearchIcon} title="Nessuna richiesta trovata" description="Prova a modificare i filtri o la ricerca." />
            ) : (
              filteredItems.map((item) => {
                const isSelected = item.id === selectedId;
                return (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => setSelectedId(item.id)}
                    className={`w-full rounded-2xl border px-4 py-3 text-left transition ${
                      isSelected
                        ? "border-[#1D4E35] bg-[#eef6ef] shadow-sm"
                        : "border-gray-200 bg-white hover:border-[#bfd0c3] hover:bg-[#f8fbf8]"
                    }`}
                  >
                    <div className="flex flex-wrap items-center gap-2">
                      <span className={`rounded-full border px-2 py-0.5 text-xs font-medium ${statusBadgeClasses(item.status)}`}>
                        {item.status}
                      </span>
                      <span className="rounded-full border border-gray-200 bg-gray-50 px-2 py-0.5 text-xs text-gray-600">
                        {categoryLabel(item.category)}
                      </span>
                      <span className={`rounded-full border px-2 py-0.5 text-xs font-medium ${priorityBadgeClasses(item.priority)}`}>
                        {priorityLabel(item.priority)}
                      </span>
                      <span className="text-xs text-gray-400">{formatDateTime(item.created_at)}</span>
                    </div>
                    <p className="mt-2 line-clamp-2 text-sm font-medium text-gray-900">{item.user_question}</p>
                    <p className="mt-2 text-xs text-gray-500">
                      Creata da <span className="font-medium text-gray-700">{item.created_by ?? "n/d"}</span>
                      {item.assigned_to_name ? (
                        <>
                          {" · "}Assegnata a <span className="font-medium text-gray-700">{item.assigned_to_name}</span>
                        </>
                      ) : null}
                    </p>
                  </button>
                );
              })
            )}
          </div>
        </article>

        <article className="rounded-3xl border border-[#d9dfd4] bg-white p-5 shadow-sm">
          {selectedRequest ? (
            <div className="space-y-5">
              <div className="space-y-2 border-b border-gray-100 pb-4">
                <div className="flex flex-wrap items-center gap-2">
                  <span className={`rounded-full border px-2 py-0.5 text-xs font-medium ${statusBadgeClasses(selectedRequest.status)}`}>
                    {selectedRequest.status}
                  </span>
                  <span className="rounded-full border border-gray-200 bg-gray-50 px-2 py-0.5 text-xs text-gray-600">
                    {categoryLabel(selectedRequest.category)}
                  </span>
                  <span className={`rounded-full border px-2 py-0.5 text-xs font-medium ${priorityBadgeClasses(selectedRequest.priority)}`}>
                    Priorità {priorityLabel(selectedRequest.priority)}
                  </span>
                </div>
                <h3 className="text-lg font-semibold text-gray-900">Dettaglio richiesta</h3>
                <p className="text-xs text-gray-500">
                  Creata da {selectedRequest.created_by ?? "n/d"} il {formatDateTime(selectedRequest.created_at)}.
                </p>
              </div>

              <div className="space-y-2">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Domanda utente</p>
                <div className="rounded-2xl border border-gray-200 bg-[#fafaf7] px-4 py-3 text-sm leading-relaxed text-gray-800">
                  {selectedRequest.user_question}
                </div>
              </div>

              <div className="space-y-2">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Risposta agente</p>
                <div className="rounded-2xl border border-gray-200 bg-[#fafaf7] px-4 py-3 text-sm leading-relaxed text-gray-700">
                  {selectedRequest.agent_response || "Nessuna risposta registrata."}
                </div>
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <label className="space-y-2">
                  <span className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Stato</span>
                  <select
                    value={draftStatus}
                    onChange={(event) => setDraftStatus(event.target.value as WikiRequest["status"])}
                    className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm text-gray-700 outline-none transition focus:border-[#1D4E35] focus:ring-2 focus:ring-[#1D4E35]/10"
                  >
                    {statusOptions.filter((option) => option.value !== "all").map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </label>
                <div className="space-y-2">
                  <span className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Ultimo aggiornamento</span>
                  <div className="rounded-xl border border-gray-200 bg-[#fafaf7] px-3 py-2 text-sm text-gray-700">
                    {formatDateTime(selectedRequest.updated_at)}
                  </div>
                </div>
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <label className="space-y-2">
                  <span className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Priorità</span>
                  <select
                    value={draftPriority}
                    onChange={(event) => setDraftPriority(event.target.value as WikiRequest["priority"])}
                    className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm text-gray-700 outline-none transition focus:border-[#1D4E35] focus:ring-2 focus:ring-[#1D4E35]/10"
                  >
                    {priorityOptions.filter((option) => option.value !== "all").map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="space-y-2">
                  <span className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Assegnatario</span>
                  <select
                    value={draftAssignedTo}
                    onChange={(event) => setDraftAssignedTo(event.target.value)}
                    className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm text-gray-700 outline-none transition focus:border-[#1D4E35] focus:ring-2 focus:ring-[#1D4E35]/10"
                  >
                    <option value="">Non assegnata</option>
                    {assignees.map((assignee) => (
                      <option key={assignee.username} value={assignee.username}>
                        {(assignee.full_name || assignee.username) + ` · ${assignee.role}`}
                      </option>
                    ))}
                  </select>
                </label>
              </div>

              <label className="block space-y-2">
                <span className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Note admin</span>
                <textarea
                  value={draftNotes}
                  onChange={(event) => setDraftNotes(event.target.value)}
                  rows={7}
                  placeholder="Aggiungi il motivo della decisione, riferimento ticket o prossimi passi."
                  className="w-full rounded-2xl border border-gray-200 px-3 py-3 text-sm text-gray-700 outline-none transition focus:border-[#1D4E35] focus:ring-2 focus:ring-[#1D4E35]/10"
                />
              </label>

              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="space-y-1 text-xs">
                  {error ? <p className="text-red-600">{error}</p> : null}
                  {successMessage ? <p className="text-green-600">{successMessage}</p> : null}
                </div>
                <button
                  type="button"
                  onClick={handleSave}
                  disabled={saving}
                  className="rounded-full bg-[#1D4E35] px-4 py-2 text-sm font-medium text-white transition hover:bg-[#163d29] disabled:opacity-50"
                >
                  {saving ? "Salvataggio..." : "Salva aggiornamento"}
                </button>
              </div>
            </div>
          ) : (
            <EmptyState icon={SearchIcon} title="Seleziona una richiesta" description="Apri un elemento dalla coda per aggiornare stato e note." />
          )}
        </article>
      </section>
    </div>
  );
}
