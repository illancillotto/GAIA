"use client";

import { useDeferredValue, useEffect, useMemo, useState } from "react";

import { EmptyState } from "@/components/ui/empty-state";
import { MetricCard } from "@/components/ui/metric-card";
import { SearchIcon } from "@/components/ui/icons";
import { getWikiRequestAssignees, getWikiRequestEvents, getWikiRequests, updateWikiRequest } from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import type { WikiRequest, WikiRequestAssignee, WikiRequestEvent } from "@/types/api";

type RequestStatusFilter = "all" | "new" | "triaged" | "investigating" | "waiting_user" | "planned" | "resolved" | "duplicate" | "rejected";
type RequestCategoryFilter = "all" | "feature_request" | "bug_report" | "question" | "support_request";
type RequestPriorityFilter = "all" | "low" | "medium" | "high" | "urgent";
type RequestTypeFilter = "all" | "help_request" | "bug_report" | "feature_request" | "access_issue" | "data_issue" | "other_request";
type RequestSeverityFilter = "all" | "low" | "medium" | "high" | "critical";

const statusOptions: Array<{ value: RequestStatusFilter; label: string }> = [
  { value: "all", label: "Tutti gli stati" },
  { value: "new", label: "Nuova" },
  { value: "triaged", label: "Triaged" },
  { value: "investigating", label: "Investigating" },
  { value: "waiting_user", label: "Waiting user" },
  { value: "planned", label: "Planned" },
  { value: "resolved", label: "Resolved" },
  { value: "duplicate", label: "Duplicate" },
  { value: "rejected", label: "Rejected" },
];

const categoryOptions: Array<{ value: RequestCategoryFilter; label: string }> = [
  { value: "all", label: "Tutte le categorie" },
  { value: "feature_request", label: "Feature request" },
  { value: "bug_report", label: "Bug report" },
  { value: "question", label: "Question" },
  { value: "support_request", label: "Support request" },
];

const requestTypeOptions: Array<{ value: RequestTypeFilter; label: string }> = [
  { value: "all", label: "Tutti i tipi" },
  { value: "help_request", label: "Supporto operativo" },
  { value: "bug_report", label: "Problema / anomalia" },
  { value: "feature_request", label: "Nuova funzionalità" },
  { value: "access_issue", label: "Problema di accesso" },
  { value: "data_issue", label: "Problema dati" },
  { value: "other_request", label: "Altro" },
];

const priorityOptions: Array<{ value: RequestPriorityFilter; label: string }> = [
  { value: "all", label: "Tutte le priorità" },
  { value: "low", label: "Bassa" },
  { value: "medium", label: "Media" },
  { value: "high", label: "Alta" },
  { value: "urgent", label: "Urgente" },
];

const severityOptions: Array<{ value: RequestSeverityFilter; label: string }> = [
  { value: "all", label: "Tutte le severità" },
  { value: "low", label: "Bassa" },
  { value: "medium", label: "Media" },
  { value: "high", label: "Alta" },
  { value: "critical", label: "Critica" },
];

function statusBadgeClasses(status: WikiRequest["status"]): string {
  switch (status) {
    case "resolved":
      return "border-green-200 bg-green-50 text-green-700";
    case "planned":
      return "border-blue-200 bg-blue-50 text-blue-700";
    case "triaged":
      return "border-amber-200 bg-amber-50 text-amber-700";
    case "investigating":
      return "border-orange-200 bg-orange-50 text-orange-700";
    case "waiting_user":
      return "border-violet-200 bg-violet-50 text-violet-700";
    case "duplicate":
      return "border-gray-200 bg-gray-50 text-gray-700";
    case "rejected":
      return "border-rose-200 bg-rose-50 text-rose-700";
    default:
      return "border-emerald-200 bg-emerald-50 text-emerald-700";
  }
}

function statusLabel(status: WikiRequest["status"]): string {
  if (status === "new") return "Nuova";
  if (status === "triaged") return "Triaged";
  if (status === "investigating") return "Investigating";
  if (status === "waiting_user") return "Waiting user";
  if (status === "planned") return "Planned";
  if (status === "resolved") return "Resolved";
  if (status === "duplicate") return "Duplicate";
  if (status === "rejected") return "Rejected";
  return status;
}

function categoryLabel(category: WikiRequest["category"]): string {
  if (category === "feature_request") return "Feature request";
  if (category === "bug_report") return "Bug report";
  if (category === "question") return "Question";
  if (category === "support_request") return "Support request";
  return category;
}

function requestTypeLabel(requestType: WikiRequest["request_type"]): string {
  if (requestType === "help_request") return "Supporto operativo";
  if (requestType === "bug_report") return "Problema / anomalia";
  if (requestType === "feature_request") return "Nuova funzionalità";
  if (requestType === "access_issue") return "Problema di accesso";
  if (requestType === "data_issue") return "Problema dati";
  if (requestType === "other_request") return "Altro";
  return requestType;
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

function severityBadgeClasses(severity: WikiRequest["severity"]): string {
  switch (severity) {
    case "critical":
      return "border-red-200 bg-red-50 text-red-700";
    case "high":
      return "border-amber-200 bg-amber-50 text-amber-700";
    case "low":
      return "border-gray-200 bg-gray-50 text-gray-600";
    default:
      return "border-blue-200 bg-blue-50 text-blue-700";
  }
}

function severityLabel(severity: WikiRequest["severity"]): string {
  if (severity === "low") return "Bassa";
  if (severity === "medium") return "Media";
  if (severity === "high") return "Alta";
  if (severity === "critical") return "Critica";
  return severity;
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

export function WikiRequestsPage({ supportOnly = false, initialRequestId = null }: { supportOnly?: boolean; initialRequestId?: string | null }) {
  const [items, setItems] = useState<WikiRequest[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<RequestStatusFilter>("all");
  const [categoryFilter, setCategoryFilter] = useState<RequestCategoryFilter>("all");
  const [requestTypeFilter, setRequestTypeFilter] = useState<RequestTypeFilter>("all");
  const [priorityFilter, setPriorityFilter] = useState<RequestPriorityFilter>("all");
  const [severityFilter, setSeverityFilter] = useState<RequestSeverityFilter>("all");
  const [query, setQuery] = useState("");
  const [draftStatus, setDraftStatus] = useState<WikiRequest["status"]>("new");
  const [draftPriority, setDraftPriority] = useState<WikiRequest["priority"]>("medium");
  const [draftSeverity, setDraftSeverity] = useState<WikiRequest["severity"]>("medium");
  const [draftAssignedTo, setDraftAssignedTo] = useState("");
  const [draftNotes, setDraftNotes] = useState("");
  const [assignees, setAssignees] = useState<WikiRequestAssignee[]>([]);
  const [timeline, setTimeline] = useState<WikiRequestEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [timelineLoading, setTimelineLoading] = useState(false);
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
        setSelectedId((current) => current ?? initialRequestId ?? requestsResponse[0]?.id ?? null);
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
  }, [initialRequestId]);

  const filteredItems = useMemo(() => {
    return items.filter((item) => {
      if (supportOnly && !["help_request", "bug_report", "access_issue", "data_issue", "other_request"].includes(item.request_type)) {
        return false;
      }
      if (statusFilter !== "all" && item.status !== statusFilter) {
        return false;
      }
      if (categoryFilter !== "all" && item.category !== categoryFilter) {
        return false;
      }
      if (requestTypeFilter !== "all" && item.request_type !== requestTypeFilter) {
        return false;
      }
      if (priorityFilter !== "all" && item.priority !== priorityFilter) {
        return false;
      }
      if (severityFilter !== "all" && item.severity !== severityFilter) {
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
        item.module_key ?? "",
        item.request_type,
        item.page_path ?? "",
        item.severity,
        item.source_channel,
        item.category,
        item.status,
        item.priority,
      ]
        .join(" ")
        .toLowerCase();
      return haystack.includes(deferredQuery);
    });
  }, [items, supportOnly, statusFilter, categoryFilter, requestTypeFilter, priorityFilter, severityFilter, deferredQuery]);

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
    setDraftSeverity(selectedRequest.severity);
    setDraftAssignedTo(selectedRequest.assigned_to ?? "");
    setDraftNotes(selectedRequest.admin_notes ?? "");
    setSuccessMessage(null);
  }, [selectedRequest, filteredItems]);

  const scopedItems = useMemo(
    () => (supportOnly ? items.filter((item) => ["help_request", "bug_report", "access_issue", "data_issue", "other_request"].includes(item.request_type)) : items),
    [items, supportOnly],
  );

  const summary = useMemo(() => {
    return {
      total: scopedItems.length,
      newCount: scopedItems.filter((item) => item.status === "new").length,
      triaged: scopedItems.filter((item) => item.status === "triaged").length,
      planned: scopedItems.filter((item) => item.status === "planned").length,
      urgent: scopedItems.filter((item) => item.priority === "urgent").length,
      resolved: scopedItems.filter((item) => item.status === "resolved").length,
    };
  }, [scopedItems]);

  useEffect(() => {
    async function loadTimeline() {
      if (!selectedRequest) {
        setTimeline([]);
        return;
      }
      const token = getStoredAccessToken();
      if (!token) {
        setTimeline([]);
        return;
      }
      setTimelineLoading(true);
      try {
        const items = await getWikiRequestEvents(token, selectedRequest.id);
        setTimeline(items);
      } catch {
        setTimeline([]);
      } finally {
        setTimelineLoading(false);
      }
    }
    void loadTimeline();
  }, [selectedRequest]);

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
        severity: draftSeverity as "low" | "medium" | "high" | "critical",
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
        <MetricCard label="Nuove" value={summary.newCount.toString()} sub="da prendere in carico" />
        <MetricCard label="Triaged" value={summary.triaged.toString()} sub="qualificate" />
        <MetricCard label="Urgenti" value={summary.urgent.toString()} sub="da trattare subito" />
        <MetricCard label="Planned" value={summary.planned.toString()} sub="in roadmap" />
        <MetricCard label="Resolved" value={summary.resolved.toString()} sub="chiuse" />
      </section>

      <section className="rounded-3xl border border-[#d9dfd4] bg-white p-5 shadow-sm">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Governance richieste</p>
            <h2 className="mt-1 text-xl font-semibold text-gray-900">{supportOnly ? "Inbox supporto Wiki" : "Richieste registrate dal Wiki"}</h2>
            <p className="mt-1 text-sm text-gray-500">
              {supportOnly
                ? "Coda operativa su supporto, anomalie, accesso e problemi dati generati dal Wiki."
                : "Le richieste vengono generate dai fallback `found=false` del widget e della pagina Wiki."}
            </p>
          </div>
          <div className="grid gap-3 md:grid-cols-6">
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
            <select
              value={requestTypeFilter}
              onChange={(event) => setRequestTypeFilter(event.target.value as RequestTypeFilter)}
              className="rounded-xl border border-gray-200 px-3 py-2 text-sm text-gray-700 outline-none transition focus:border-[#1D4E35] focus:ring-2 focus:ring-[#1D4E35]/10"
            >
              {requestTypeOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
            <select
              value={severityFilter}
              onChange={(event) => setSeverityFilter(event.target.value as RequestSeverityFilter)}
              className="rounded-xl border border-gray-200 px-3 py-2 text-sm text-gray-700 outline-none transition focus:border-[#1D4E35] focus:ring-2 focus:ring-[#1D4E35]/10"
            >
              {severityOptions.map((option) => (
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
                      {statusLabel(item.status)}
                      </span>
                      <span className="rounded-full border border-gray-200 bg-gray-50 px-2 py-0.5 text-xs text-gray-600">
                        {requestTypeLabel(item.request_type)}
                      </span>
                      <span className={`rounded-full border px-2 py-0.5 text-xs font-medium ${priorityBadgeClasses(item.priority)}`}>
                        {priorityLabel(item.priority)}
                      </span>
                      <span className={`rounded-full border px-2 py-0.5 text-xs font-medium ${severityBadgeClasses(item.severity)}`}>
                        {severityLabel(item.severity)}
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
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className={`rounded-full border px-2 py-0.5 text-xs font-medium ${statusBadgeClasses(selectedRequest.status)}`}>
                      {statusLabel(selectedRequest.status)}
                    </span>
                    <span className="rounded-full border border-gray-200 bg-gray-50 px-2 py-0.5 text-xs text-gray-600">
                      {requestTypeLabel(selectedRequest.request_type)}
                    </span>
                    <span className={`rounded-full border px-2 py-0.5 text-xs font-medium ${priorityBadgeClasses(selectedRequest.priority)}`}>
                      Priorità {priorityLabel(selectedRequest.priority)}
                    </span>
                    <span className={`rounded-full border px-2 py-0.5 text-xs font-medium ${severityBadgeClasses(selectedRequest.severity)}`}>
                      Severità {severityLabel(selectedRequest.severity)}
                    </span>
                  </div>
                  <a
                    href={`/wiki/requests/${selectedRequest.id}`}
                    className="text-xs font-medium text-[#1D4E35] underline underline-offset-2"
                  >
                    Apri pagina richiesta
                  </a>
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

              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                <div className="rounded-2xl border border-gray-200 bg-[#fafaf7] px-4 py-3 text-sm text-gray-700">
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Modulo</p>
                  <p className="mt-2">{selectedRequest.module_key || "n/d"}</p>
                </div>
                <div className="rounded-2xl border border-gray-200 bg-[#fafaf7] px-4 py-3 text-sm text-gray-700">
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Canale</p>
                  <p className="mt-2">{selectedRequest.source_channel || "n/d"}</p>
                </div>
                <div className="rounded-2xl border border-gray-200 bg-[#fafaf7] px-4 py-3 text-sm text-gray-700">
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Impatto</p>
                  <p className="mt-2">{selectedRequest.impact_scope || "n/d"}</p>
                </div>
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <div className="rounded-2xl border border-gray-200 bg-[#fafaf7] px-4 py-3 text-sm text-gray-700">
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Pagina</p>
                  <p className="mt-2 break-all">{selectedRequest.page_path || "n/d"}</p>
                </div>
                <div className="rounded-2xl border border-gray-200 bg-[#fafaf7] px-4 py-3 text-sm text-gray-700">
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Conversation ID</p>
                  <p className="mt-2 break-all">{selectedRequest.conversation_id || "n/d"}</p>
                </div>
              </div>

              {selectedRequest.desired_outcome || selectedRequest.observed_behavior || selectedRequest.expected_behavior ? (
                <div className="grid gap-4 xl:grid-cols-3">
                  <div className="rounded-2xl border border-gray-200 bg-[#fafaf7] px-4 py-3 text-sm text-gray-700">
                    <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Comportamento osservato</p>
                    <p className="mt-2 whitespace-pre-wrap">{selectedRequest.observed_behavior || "n/d"}</p>
                  </div>
                  <div className="rounded-2xl border border-gray-200 bg-[#fafaf7] px-4 py-3 text-sm text-gray-700">
                    <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Comportamento atteso</p>
                    <p className="mt-2 whitespace-pre-wrap">{selectedRequest.expected_behavior || "n/d"}</p>
                  </div>
                  <div className="rounded-2xl border border-gray-200 bg-[#fafaf7] px-4 py-3 text-sm text-gray-700">
                    <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Esito desiderato</p>
                    <p className="mt-2 whitespace-pre-wrap">{selectedRequest.desired_outcome || "n/d"}</p>
                  </div>
                </div>
              ) : null}

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

              <div className="grid gap-4 md:grid-cols-3">
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
                  <span className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Severità</span>
                  <select
                    value={draftSeverity}
                    onChange={(event) => setDraftSeverity(event.target.value as WikiRequest["severity"])}
                    className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm text-gray-700 outline-none transition focus:border-[#1D4E35] focus:ring-2 focus:ring-[#1D4E35]/10"
                  >
                    {severityOptions.filter((option) => option.value !== "all").map((option) => (
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

              <div className="space-y-2">
                <span className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Timeline caso</span>
                <div className="rounded-2xl border border-gray-200 bg-[#fafaf7] p-3">
                  {timelineLoading ? (
                    <p className="text-sm text-gray-500">Caricamento timeline...</p>
                  ) : timeline.length === 0 ? (
                    <p className="text-sm text-gray-500">Nessun evento registrato.</p>
                  ) : (
                    <div className="space-y-3">
                      {timeline.map((event) => (
                        <div key={event.id} className="rounded-xl border border-gray-100 bg-white px-3 py-3">
                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <p className="text-sm font-medium text-gray-900">{event.event_type.replaceAll("_", " ")}</p>
                            <span className="text-xs text-gray-400">{formatDateTime(event.created_at)}</span>
                          </div>
                          <p className="mt-1 text-xs text-gray-500">
                            {event.actor_username || "sistema"}
                            {event.from_status || event.to_status ? ` · ${event.from_status || "n/d"} → ${event.to_status || "n/d"}` : ""}
                          </p>
                          {event.payload ? (
                            <div className="mt-2 flex flex-wrap gap-2">
                              {Object.entries(event.payload).map(([key, value]) => (
                                <span key={key} className="rounded-full border border-gray-200 bg-gray-50 px-2 py-1 text-[11px] text-gray-600">
                                  {key}: {String(value)}
                                </span>
                              ))}
                            </div>
                          ) : null}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>

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
