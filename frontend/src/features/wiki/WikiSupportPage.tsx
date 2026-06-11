"use client";

import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";

import { createWikiRequestWithArtifacts, getMyWikiRequests, getMyWikiRequestsSummary, markWikiRequestViewed, reopenWikiRequest, updateWikiRequestFeedback } from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import { captureWikiRequestArtifacts, consumeWikiSupportDraft } from "./request-support";
import type { WikiMyRequestsSummary, WikiRequest, WikiRequestCreateInput } from "@/types/api";

type SupportIntent = "help_request" | "bug_report" | "feature_request" | "access_issue" | "data_issue" | "other_request";

const REQUEST_TYPE_OPTIONS: Array<{ value: SupportIntent; label: string; category: "support_request" | "bug_report" | "feature_request" | "question" }> = [
  { value: "help_request", label: "Supporto operativo", category: "support_request" },
  { value: "bug_report", label: "Problema / anomalia", category: "bug_report" },
  { value: "feature_request", label: "Nuova funzionalità", category: "feature_request" },
  { value: "access_issue", label: "Problema di accesso", category: "support_request" },
  { value: "data_issue", label: "Problema dati", category: "support_request" },
  { value: "other_request", label: "Altro", category: "question" },
];

const SEVERITY_OPTIONS = [
  { value: "low", label: "Bassa" },
  { value: "medium", label: "Media" },
  { value: "high", label: "Alta" },
  { value: "critical", label: "Critica" },
] as const;

const IMPACT_OPTIONS = [
  { value: "single_user", label: "Solo me" },
  { value: "team", label: "Il mio team" },
  { value: "office", label: "Intero ufficio" },
  { value: "global", label: "Tutto GAIA" },
] as const;

function prettyRequestType(value: string): string {
  return REQUEST_TYPE_OPTIONS.find((option) => option.value === value)?.label ?? value;
}

function prettyStatus(value: WikiRequest["status"]): string {
  if (value === "new") return "Nuova";
  if (value === "triaged") return "Triaged";
  if (value === "investigating") return "In analisi";
  if (value === "waiting_user") return "In attesa di te";
  if (value === "planned") return "Pianificata";
  if (value === "resolved") return "Risolta";
  if (value === "duplicate") return "Duplicata";
  if (value === "rejected") return "Respinta";
  return value;
}

function statusTone(value: WikiRequest["status"]): string {
  if (value === "resolved") return "border-green-200 bg-green-50 text-green-700";
  if (value === "planned") return "border-sky-200 bg-sky-50 text-sky-700";
  if (value === "waiting_user") return "border-violet-200 bg-violet-50 text-violet-700";
  if (value === "investigating") return "border-amber-200 bg-amber-50 text-amber-700";
  if (value === "duplicate") return "border-gray-200 bg-gray-50 text-gray-700";
  if (value === "rejected") return "border-rose-200 bg-rose-50 text-rose-700";
  return "border-emerald-200 bg-emerald-50 text-emerald-700";
}

function formatDateTime(value: string | null): string {
  if (!value) return "n/d";
  try {
    return new Intl.DateTimeFormat("it-IT", { dateStyle: "short", timeStyle: "short" }).format(new Date(value));
  } catch {
    return value;
  }
}

export function WikiSupportPage() {
  const searchParams = useSearchParams();
  const [requestType, setRequestType] = useState<SupportIntent>("help_request");
  const [question, setQuestion] = useState("");
  const [agentResponse, setAgentResponse] = useState("");
  const [moduleKey, setModuleKey] = useState("");
  const [pagePath, setPagePath] = useState("");
  const [severity, setSeverity] = useState<(typeof SEVERITY_OPTIONS)[number]["value"]>("medium");
  const [impactScope, setImpactScope] = useState<(typeof IMPACT_OPTIONS)[number]["value"]>("single_user");
  const [contextArticle, setContextArticle] = useState("");
  const [conversationId, setConversationId] = useState("");
  const [desiredOutcome, setDesiredOutcome] = useState("");
  const [observedBehavior, setObservedBehavior] = useState("");
  const [expectedBehavior, setExpectedBehavior] = useState("");
  const [myRequests, setMyRequests] = useState<WikiRequest[]>([]);
  const [summary, setSummary] = useState<WikiMyRequestsSummary | null>(null);
  const [selectedRequestId, setSelectedRequestId] = useState<string | null>(null);
  const [feedbackRating, setFeedbackRating] = useState<"helpful" | "not_helpful">("helpful");
  const [feedbackNotes, setFeedbackNotes] = useState("");
  const [saving, setSaving] = useState(false);
  const [feedbackSaving, setFeedbackSaving] = useState(false);
  const [reopenReason, setReopenReason] = useState("");
  const [reopening, setReopening] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setRequestType((searchParams.get("request_type") as SupportIntent) || (searchParams.get("intent") as SupportIntent) || "help_request");
    setQuestion(searchParams.get("question") ?? "");
    setAgentResponse(searchParams.get("answer") ?? "");
    setModuleKey(searchParams.get("module_key") ?? "");
    setPagePath(searchParams.get("page_path") ?? "");
    setContextArticle(searchParams.get("context_article") ?? "");
    setConversationId(searchParams.get("conversation_id") ?? "");
    setDesiredOutcome(searchParams.get("desired_outcome") ?? "");
    setObservedBehavior(searchParams.get("observed_behavior") ?? "");
    setExpectedBehavior(searchParams.get("expected_behavior") ?? "");
  }, [searchParams]);

  useEffect(() => {
    async function loadMyRequests() {
      const token = getStoredAccessToken();
      if (!token) return;
      try {
        const [items, summaryResponse] = await Promise.all([getMyWikiRequests(token), getMyWikiRequestsSummary(token)]);
        setMyRequests(items);
        setSummary(summaryResponse);
        setSelectedRequestId((current) => current ?? items[0]?.id ?? null);
      } catch {
        setMyRequests([]);
        setSummary(null);
      }
    }
    void loadMyRequests();
  }, []);

  const selectedType = useMemo(
    () => REQUEST_TYPE_OPTIONS.find((option) => option.value === requestType) ?? REQUEST_TYPE_OPTIONS[0],
    [requestType],
  );

  const selectedRequest = useMemo(
    () => myRequests.find((item) => item.id === selectedRequestId) ?? myRequests[0] ?? null,
    [myRequests, selectedRequestId],
  );

  useEffect(() => {
    if (!selectedRequest) {
      setFeedbackRating("helpful");
      setFeedbackNotes("");
      return;
    }
    setFeedbackRating(selectedRequest.user_feedback_rating === "not_helpful" ? "not_helpful" : "helpful");
    setFeedbackNotes(selectedRequest.user_feedback_notes ?? "");
  }, [selectedRequest]);

  useEffect(() => {
    async function syncViewed() {
      if (!selectedRequest || !selectedRequest.has_unread_update) {
        return;
      }
      const token = getStoredAccessToken();
      if (!token) {
        return;
      }
      try {
        const updated = await markWikiRequestViewed(token, selectedRequest.id);
        setMyRequests((current) => current.map((item) => (item.id === updated.id ? updated : item)));
      } catch {
        // no-op: non bloccare la UI se la marcatura letta fallisce
      }
    }
    void syncViewed();
  }, [selectedRequest?.id, selectedRequest?.has_unread_update]);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    const token = getStoredAccessToken();
    if (!token) {
      setError("Sessione non disponibile.");
      return;
    }
    if (!question.trim()) {
      setError("Inserisci la domanda o la segnalazione principale.");
      return;
    }

    setSaving(true);
    setError(null);
    setSuccessMessage(null);
    try {
      const payload: WikiRequestCreateInput = {
        user_question: question.trim(),
        agent_response: agentResponse.trim() || null,
        category: selectedType.category,
        request_type: requestType,
        module_key: moduleKey.trim() || null,
        page_path: pagePath.trim() || null,
        source_channel: "support_page",
        severity,
        impact_scope: impactScope,
        conversation_id: conversationId.trim() || null,
        context_article: contextArticle.trim() || null,
        desired_outcome: desiredOutcome.trim() || null,
        observed_behavior: observedBehavior.trim() || null,
        expected_behavior: expectedBehavior.trim() || null,
      };
      const draftArtifacts = consumeWikiSupportDraft(searchParams.get("draft_id"));
      const fallbackArtifacts = draftArtifacts ?? (await captureWikiRequestArtifacts());
      const created = await createWikiRequestWithArtifacts(token, payload, fallbackArtifacts);
      setMyRequests((current) => [created, ...current.filter((item) => item.id !== created.id)]);
      setSelectedRequestId(created.id);
      setSummary((current) =>
        current
          ? {
              ...current,
              total_requests: current.total_requests + 1,
              open_requests: current.open_requests + 1,
            }
          : current,
      );
      setSuccessMessage("Richiesta registrata correttamente nel supporto Wiki.");
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Errore registrazione supporto Wiki");
    } finally {
      setSaving(false);
    }
  }

  async function handleFeedbackSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!selectedRequest) {
      return;
    }
    const token = getStoredAccessToken();
    if (!token) {
      setError("Sessione non disponibile.");
      return;
    }
    setFeedbackSaving(true);
    setError(null);
    setSuccessMessage(null);
    try {
        const updated = await updateWikiRequestFeedback(token, selectedRequest.id, {
          rating: feedbackRating,
          notes: feedbackNotes.trim() || null,
        });
      setMyRequests((current) => current.map((item) => (item.id === updated.id ? updated : item)));
      setSummary((current) =>
        current
          ? {
              ...current,
              resolved_feedback_pending: Math.max(
                0,
                current.resolved_feedback_pending - (selectedRequest.user_feedback_submitted_at ? 0 : 1),
              ),
            }
          : current,
      );
      setSuccessMessage("Feedback registrato. Grazie.");
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Errore invio feedback");
    } finally {
      setFeedbackSaving(false);
    }
  }

  async function handleReopenSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!selectedRequest) {
      return;
    }
    const token = getStoredAccessToken();
    if (!token) {
      setError("Sessione non disponibile.");
      return;
    }
    setReopening(true);
    setError(null);
    setSuccessMessage(null);
    try {
      const updated = await reopenWikiRequest(token, selectedRequest.id, {
        reason: reopenReason.trim() || null,
      });
      setMyRequests((current) => current.map((item) => (item.id === updated.id ? updated : item)));
      setSummary((current) =>
        current
          ? {
              ...current,
              open_requests: current.open_requests + (selectedRequest.status === "resolved" || selectedRequest.status === "duplicate" || selectedRequest.status === "rejected" ? 1 : 0),
              unread_updates: Math.max(0, current.unread_updates - (selectedRequest.has_unread_update ? 1 : 0)),
              resolved_feedback_pending:
                selectedRequest.status === "resolved" && !selectedRequest.user_feedback_submitted_at
                  ? Math.max(0, current.resolved_feedback_pending - 1)
                  : current.resolved_feedback_pending,
            }
          : current,
      );
      setReopenReason("");
      setSuccessMessage("Richiesta riaperta correttamente.");
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Errore riapertura richiesta");
    } finally {
      setReopening(false);
    }
  }

  return (
    <div className="space-y-6">
      <section className="overflow-hidden rounded-[28px] border border-[#d7dfd6] bg-[radial-gradient(circle_at_top_left,_rgba(221,238,227,0.95),_rgba(248,246,239,0.98)_55%,_rgba(255,255,255,0.99))] p-6 shadow-sm">
        <div className="grid gap-6 xl:grid-cols-[minmax(0,1.45fr)_minmax(340px,0.95fr)]">
          <div className="space-y-4">
            <div className="inline-flex items-center rounded-full border border-white/70 bg-white/75 px-4 py-1 text-[11px] font-semibold uppercase tracking-[0.24em] text-[#1D4E35] shadow-sm">
              Supporto Wiki
            </div>
            <h2 className="max-w-3xl text-3xl font-semibold tracking-tight text-[#1b3126]">
              Un solo punto per chiedere aiuto, segnalare anomalie e proporre miglioramenti su GAIA.
            </h2>
            <p className="max-w-3xl text-sm leading-7 text-[#3f5a4d]">
              Questa pagina trasforma una domanda o una frizione del Wiki in un caso strutturato che gli admin possono
              prendere in carico, classificare e usare per capire i bisogni reali degli utenti.
            </p>
          </div>
          <div className="space-y-3">
            <div className="rounded-3xl border border-sky-200 bg-sky-50/70 p-4">
              <p className="text-sm font-semibold text-sky-900">Come usarla</p>
              <div className="mt-2 space-y-2 text-sm text-sky-800">
                <p>1. Scegli il tipo di richiesta più vicino al tuo bisogno.</p>
                <p>2. Conferma modulo, pagina e contesto del problema.</p>
                <p>3. Lascia il caso già strutturato per il triage admin.</p>
              </div>
            </div>
            <div className="rounded-3xl border border-emerald-200 bg-emerald-50/70 p-4">
              <p className="text-sm font-semibold text-emerald-900">Ingressi supportati</p>
              <div className="mt-2 flex flex-wrap gap-2 text-xs text-emerald-900">
                {REQUEST_TYPE_OPTIONS.map((option) => (
                  <span key={option.value} className="rounded-full border border-emerald-200 bg-white px-2 py-1">
                    {option.label}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

        <div className="grid gap-6 xl:grid-cols-[minmax(0,1.1fr)_400px]">
        <section className="rounded-[28px] border border-[#e3e6dc] bg-white p-6 shadow-sm">
          <div className="space-y-2">
            <p className="text-sm font-semibold text-[#223d30]">Nuova segnalazione</p>
            <p className="text-sm text-[#5f6e67]">Compila il caso con il livello di dettaglio minimo utile per il triage.</p>
          </div>

          <form onSubmit={handleSubmit} className="mt-5 space-y-5">
            <div className="grid gap-4 md:grid-cols-2">
              <label className="space-y-2">
                <span className="text-xs font-medium uppercase tracking-wide text-gray-400">Tipo richiesta</span>
                <select
                  className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm text-gray-700 outline-none transition focus:border-[#1D4E35] focus:ring-2 focus:ring-[#1D4E35]/10"
                  value={requestType}
                  onChange={(event) => setRequestType(event.target.value as SupportIntent)}
                >
                  {REQUEST_TYPE_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>{option.label}</option>
                  ))}
                </select>
              </label>
              <label className="space-y-2">
                <span className="text-xs font-medium uppercase tracking-wide text-gray-400">Modulo</span>
                <input value={moduleKey} onChange={(event) => setModuleKey(event.target.value)} className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm text-gray-700 outline-none transition focus:border-[#1D4E35] focus:ring-2 focus:ring-[#1D4E35]/10" placeholder="es. rete, accessi, catasto" />
              </label>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <label className="space-y-2">
                <span className="text-xs font-medium uppercase tracking-wide text-gray-400">Severità</span>
                <select
                  className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm text-gray-700 outline-none transition focus:border-[#1D4E35] focus:ring-2 focus:ring-[#1D4E35]/10"
                  value={severity}
                  onChange={(event) => setSeverity(event.target.value as (typeof SEVERITY_OPTIONS)[number]["value"])}
                >
                  {SEVERITY_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>{option.label}</option>
                  ))}
                </select>
              </label>
              <label className="space-y-2">
                <span className="text-xs font-medium uppercase tracking-wide text-gray-400">Impatto</span>
                <select
                  className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm text-gray-700 outline-none transition focus:border-[#1D4E35] focus:ring-2 focus:ring-[#1D4E35]/10"
                  value={impactScope}
                  onChange={(event) => setImpactScope(event.target.value as (typeof IMPACT_OPTIONS)[number]["value"])}
                >
                  {IMPACT_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>{option.label}</option>
                  ))}
                </select>
              </label>
            </div>

            <label className="space-y-2">
              <span className="text-xs font-medium uppercase tracking-wide text-gray-400">Domanda o sintesi problema</span>
              <textarea value={question} onChange={(event) => setQuestion(event.target.value)} rows={3} className="w-full rounded-2xl border border-gray-200 px-4 py-3 text-sm text-gray-700 outline-none transition focus:border-[#1D4E35] focus:ring-2 focus:ring-[#1D4E35]/10" placeholder="Descrivi in una frase cosa ti serve o cosa non sta funzionando." />
            </label>

            <div className="grid gap-4 md:grid-cols-2">
              <label className="space-y-2">
                <span className="text-xs font-medium uppercase tracking-wide text-gray-400">Pagina</span>
                <input value={pagePath} onChange={(event) => setPagePath(event.target.value)} className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm text-gray-700 outline-none transition focus:border-[#1D4E35] focus:ring-2 focus:ring-[#1D4E35]/10" placeholder="/wiki, /network/devices, ..." />
              </label>
              <label className="space-y-2">
                <span className="text-xs font-medium uppercase tracking-wide text-gray-400">Conversation ID</span>
                <input value={conversationId} onChange={(event) => setConversationId(event.target.value)} className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm text-gray-700 outline-none transition focus:border-[#1D4E35] focus:ring-2 focus:ring-[#1D4E35]/10" placeholder="UUID conversazione Wiki" />
              </label>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <label className="space-y-2">
                <span className="text-xs font-medium uppercase tracking-wide text-gray-400">Contesto articolo</span>
                <input value={contextArticle} onChange={(event) => setContextArticle(event.target.value)} className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm text-gray-700 outline-none transition focus:border-[#1D4E35] focus:ring-2 focus:ring-[#1D4E35]/10" placeholder="source_file indicizzato" />
              </label>
              <label className="space-y-2">
                <span className="text-xs font-medium uppercase tracking-wide text-gray-400">Risposta del Wiki</span>
                <textarea value={agentResponse} onChange={(event) => setAgentResponse(event.target.value)} rows={2} className="w-full rounded-2xl border border-gray-200 px-4 py-3 text-sm text-gray-700 outline-none transition focus:border-[#1D4E35] focus:ring-2 focus:ring-[#1D4E35]/10" placeholder="Ultima risposta data dall'assistente" />
              </label>
            </div>

            <div className="grid gap-4 md:grid-cols-3">
              <label className="space-y-2">
                <span className="text-xs font-medium uppercase tracking-wide text-gray-400">Comportamento osservato</span>
                <textarea value={observedBehavior} onChange={(event) => setObservedBehavior(event.target.value)} rows={4} className="w-full rounded-2xl border border-gray-200 px-4 py-3 text-sm text-gray-700 outline-none transition focus:border-[#1D4E35] focus:ring-2 focus:ring-[#1D4E35]/10" placeholder="Cosa succede oggi" />
              </label>
              <label className="space-y-2">
                <span className="text-xs font-medium uppercase tracking-wide text-gray-400">Comportamento atteso</span>
                <textarea value={expectedBehavior} onChange={(event) => setExpectedBehavior(event.target.value)} rows={4} className="w-full rounded-2xl border border-gray-200 px-4 py-3 text-sm text-gray-700 outline-none transition focus:border-[#1D4E35] focus:ring-2 focus:ring-[#1D4E35]/10" placeholder="Come dovrebbe andare" />
              </label>
              <label className="space-y-2">
                <span className="text-xs font-medium uppercase tracking-wide text-gray-400">Esito desiderato</span>
                <textarea value={desiredOutcome} onChange={(event) => setDesiredOutcome(event.target.value)} rows={4} className="w-full rounded-2xl border border-gray-200 px-4 py-3 text-sm text-gray-700 outline-none transition focus:border-[#1D4E35] focus:ring-2 focus:ring-[#1D4E35]/10" placeholder="Quale aiuto o miglioramento ti aspetti" />
              </label>
            </div>

            {successMessage ? <div className="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">{successMessage}</div> : null}
            {error ? <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">{error}</div> : null}

            <div className="flex justify-end">
              <button type="submit" disabled={saving} className="rounded-full bg-[#1D4E35] px-5 py-2.5 text-sm font-medium text-white hover:bg-[#163d29] disabled:opacity-50">
                {saving ? "Registrazione..." : "Registra segnalazione"}
              </button>
            </div>
          </form>
        </section>

        <aside className="space-y-4">
          <section className="grid grid-cols-2 gap-3">
            <div className="rounded-[24px] border border-[#e3e6dc] bg-white p-4 shadow-sm">
              <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-gray-400">Aggiornamenti</p>
              <p className="mt-2 text-2xl font-semibold text-[#223d30]">{summary?.unread_updates ?? 0}</p>
              <p className="mt-1 text-xs text-gray-500">da leggere</p>
            </div>
            <div className="rounded-[24px] border border-[#e3e6dc] bg-white p-4 shadow-sm">
              <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-gray-400">Attese tue</p>
              <p className="mt-2 text-2xl font-semibold text-[#223d30]">{summary?.waiting_user_requests ?? 0}</p>
              <p className="mt-1 text-xs text-gray-500">in waiting user</p>
            </div>
            <div className="rounded-[24px] border border-[#e3e6dc] bg-white p-4 shadow-sm">
              <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-gray-400">Aperte</p>
              <p className="mt-2 text-2xl font-semibold text-[#223d30]">{summary?.open_requests ?? 0}</p>
              <p className="mt-1 text-xs text-gray-500">casi attivi</p>
            </div>
            <div className="rounded-[24px] border border-[#e3e6dc] bg-white p-4 shadow-sm">
              <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-gray-400">Feedback atteso</p>
              <p className="mt-2 text-2xl font-semibold text-[#223d30]">{summary?.resolved_feedback_pending ?? 0}</p>
              <p className="mt-1 text-xs text-gray-500">chiuse senza riscontro</p>
            </div>
          </section>

          <section className="rounded-[28px] border border-[#e3e6dc] bg-white p-5 shadow-sm">
            <p className="text-sm font-semibold text-[#223d30]">Tipi di richiesta</p>
            <div className="mt-3 space-y-2">
              {REQUEST_TYPE_OPTIONS.map((option) => (
                <div key={option.value} className={`rounded-2xl border px-4 py-3 text-sm ${requestType === option.value ? "border-[#1D4E35] bg-[#f5f9f6] text-[#1D4E35]" : "border-gray-200 bg-[#fafaf7] text-gray-700"}`}>
                  <p className="font-medium">{option.label}</p>
                  <p className="mt-1 text-xs text-gray-500">Categoria: {option.category}</p>
                </div>
              ))}
            </div>
          </section>

          <section className="rounded-[28px] border border-[#e3e6dc] bg-white p-5 shadow-sm">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-sm font-semibold text-[#223d30]">Le tue richieste recenti</p>
                <p className="mt-1 text-xs text-gray-500">Qui trovi aggiornamenti admin, messaggi di risoluzione e la raccolta del tuo feedback.</p>
              </div>
              <div className="rounded-full border border-amber-200 bg-amber-50 px-3 py-1 text-xs font-medium text-amber-800">
                {myRequests.filter((item) => item.has_unread_update).length} aggiornamenti da leggere
              </div>
            </div>
            <div className="mt-3 space-y-2">
              {myRequests.length > 0 ? myRequests.slice(0, 8).map((item) => (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => setSelectedRequestId(item.id)}
                  className={`w-full rounded-2xl border px-4 py-3 text-left transition ${selectedRequest?.id === item.id ? "border-[#1D4E35] bg-[#f5f9f6]" : "border-gray-200 bg-[#fafaf7] hover:border-[#bfd0c3]"}`}
                >
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="rounded-full border border-gray-200 bg-white px-2 py-0.5 text-xs font-medium text-gray-700">{prettyRequestType(item.request_type)}</span>
                    <span className={`rounded-full border px-2 py-0.5 text-xs font-medium ${statusTone(item.status)}`}>{prettyStatus(item.status)}</span>
                    {item.has_unread_update ? (
                      <span className="rounded-full border border-amber-200 bg-amber-50 px-2 py-0.5 text-xs font-medium text-amber-800">Nuovo aggiornamento</span>
                    ) : null}
                  </div>
                  <p className="mt-2 text-sm font-medium text-gray-900">{item.user_question}</p>
                  <p className="mt-1 text-xs text-gray-500">
                    {item.module_key ? `Modulo ${item.module_key}` : "Modulo non indicato"} · aggiornato {formatDateTime(item.updated_at)}
                  </p>
                </button>
              )) : <p className="text-sm text-gray-500">Nessuna richiesta registrata dal tuo account.</p>}
            </div>
          </section>

          <section className="rounded-[28px] border border-[#e3e6dc] bg-white p-5 shadow-sm">
            <p className="text-sm font-semibold text-[#223d30]">Stato della richiesta selezionata</p>
            {selectedRequest ? (
              <div className="mt-3 space-y-4">
                <div className="flex flex-wrap gap-2">
                  <span className={`rounded-full border px-2 py-0.5 text-xs font-medium ${statusTone(selectedRequest.status)}`}>{prettyStatus(selectedRequest.status)}</span>
                  <span className="rounded-full border border-gray-200 bg-white px-2 py-0.5 text-xs font-medium text-gray-700">{prettyRequestType(selectedRequest.request_type)}</span>
                  <span className="rounded-full border border-gray-200 bg-white px-2 py-0.5 text-xs font-medium text-gray-700">Ultimo update {formatDateTime(selectedRequest.last_admin_update_at ?? selectedRequest.updated_at)}</span>
                </div>

                {selectedRequest.resolution_message ? (
                  <div className="rounded-2xl border border-sky-200 bg-sky-50 px-4 py-3">
                    <p className="text-xs font-semibold uppercase tracking-wide text-sky-800">Messaggio dall&apos;amministrazione</p>
                    <p className="mt-2 text-sm leading-relaxed text-sky-950">{selectedRequest.resolution_message}</p>
                  </div>
                ) : null}

                {selectedRequest.admin_notes ? (
                  <div className="rounded-2xl border border-gray-200 bg-[#fafaf7] px-4 py-3">
                    <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">Note operative</p>
                    <p className="mt-2 text-sm leading-relaxed text-gray-700">{selectedRequest.admin_notes}</p>
                  </div>
                ) : (
                  <div className="rounded-2xl border border-dashed border-gray-200 bg-[#fafaf7] px-4 py-3 text-sm text-gray-500">
                    Nessuna nota admin disponibile al momento.
                  </div>
                )}

                <form onSubmit={handleFeedbackSubmit} className="space-y-3 rounded-2xl border border-gray-200 bg-[#fafaf7] px-4 py-4">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">Feedback finale</p>
                    <p className="mt-1 text-sm text-gray-600">Aiuta gli admin a capire se il supporto è stato utile o se il caso va riaperto.</p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <button
                      type="button"
                      onClick={() => setFeedbackRating("helpful")}
                      className={`rounded-full border px-3 py-1.5 text-xs font-medium ${feedbackRating === "helpful" ? "border-emerald-300 bg-emerald-50 text-emerald-800" : "border-gray-200 bg-white text-gray-700"}`}
                    >
                      Utile / risolto
                    </button>
                    <button
                      type="button"
                      onClick={() => setFeedbackRating("not_helpful")}
                      className={`rounded-full border px-3 py-1.5 text-xs font-medium ${feedbackRating === "not_helpful" ? "border-rose-300 bg-rose-50 text-rose-800" : "border-gray-200 bg-white text-gray-700"}`}
                    >
                      Non risolto / incompleto
                    </button>
                  </div>
                  <textarea
                    value={feedbackNotes}
                    onChange={(event) => setFeedbackNotes(event.target.value)}
                    rows={3}
                    placeholder="Cosa ti è stato utile o cosa manca ancora?"
                    className="w-full rounded-2xl border border-gray-200 px-4 py-3 text-sm text-gray-700 outline-none transition focus:border-[#1D4E35] focus:ring-2 focus:ring-[#1D4E35]/10"
                  />
                  <div className="flex items-center justify-between gap-3">
                    <p className="text-xs text-gray-500">
                      {selectedRequest.user_feedback_submitted_at ? `Ultimo feedback: ${formatDateTime(selectedRequest.user_feedback_submitted_at)}` : "Nessun feedback inviato."}
                    </p>
                    <button type="submit" disabled={feedbackSaving} className="rounded-full bg-[#1D4E35] px-4 py-2 text-xs font-medium text-white hover:bg-[#163d29] disabled:opacity-50">
                      {feedbackSaving ? "Invio..." : "Invia feedback"}
                    </button>
                  </div>
                </form>

                {(selectedRequest.status === "resolved" || selectedRequest.status === "duplicate" || selectedRequest.status === "rejected" || selectedRequest.status === "planned") ? (
                  <form onSubmit={handleReopenSubmit} className="space-y-3 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-4">
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-wide text-rose-700">Riapri il caso</p>
                      <p className="mt-1 text-sm text-rose-900">Usalo se il problema non è risolto o il caso è stato accorpato in modo non corretto.</p>
                    </div>
                    <textarea
                      value={reopenReason}
                      onChange={(event) => setReopenReason(event.target.value)}
                      rows={3}
                      placeholder="Spiega perché vuoi riaprire la richiesta."
                      className="w-full rounded-2xl border border-rose-200 bg-white px-4 py-3 text-sm text-gray-700 outline-none transition focus:border-rose-400 focus:ring-2 focus:ring-rose-200"
                    />
                    <div className="flex justify-end">
                      <button type="submit" disabled={reopening} className="rounded-full bg-rose-700 px-4 py-2 text-xs font-medium text-white hover:bg-rose-800 disabled:opacity-50">
                        {reopening ? "Riapertura..." : "Riapri richiesta"}
                      </button>
                    </div>
                  </form>
                ) : null}
              </div>
            ) : (
              <p className="mt-3 text-sm text-gray-500">Seleziona una richiesta per leggere gli ultimi aggiornamenti.</p>
            )}
          </section>
        </aside>
      </div>
    </div>
  );
}
