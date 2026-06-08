"use client";

import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";

import { createWikiRequest, getMyWikiRequests } from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import type { WikiRequest } from "@/types/api";

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
  const [saving, setSaving] = useState(false);
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
        const items = await getMyWikiRequests(token);
        setMyRequests(items);
      } catch {
        setMyRequests([]);
      }
    }
    void loadMyRequests();
  }, []);

  const selectedType = useMemo(
    () => REQUEST_TYPE_OPTIONS.find((option) => option.value === requestType) ?? REQUEST_TYPE_OPTIONS[0],
    [requestType],
  );

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
      const created = await createWikiRequest(token, {
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
      });
      setMyRequests((current) => [created, ...current.filter((item) => item.id !== created.id)]);
      setSuccessMessage("Richiesta registrata correttamente nel supporto Wiki.");
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Errore registrazione supporto Wiki");
    } finally {
      setSaving(false);
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
            <p className="text-sm font-semibold text-[#223d30]">Le tue richieste recenti</p>
            <div className="mt-3 space-y-2">
              {myRequests.length > 0 ? myRequests.slice(0, 6).map((item) => (
                <div key={item.id} className="rounded-2xl border border-gray-200 bg-[#fafaf7] px-4 py-3">
                  <div className="flex flex-wrap gap-2">
                    <span className="rounded-full border border-gray-200 bg-white px-2 py-0.5 text-xs font-medium text-gray-700">{prettyRequestType(item.request_type)}</span>
                    <span className="rounded-full border border-gray-200 bg-white px-2 py-0.5 text-xs font-medium text-gray-700">{item.status}</span>
                  </div>
                  <p className="mt-2 text-sm font-medium text-gray-900">{item.user_question}</p>
                  {item.module_key ? <p className="mt-1 text-xs text-gray-500">Modulo: {item.module_key}</p> : null}
                </div>
              )) : <p className="text-sm text-gray-500">Nessuna richiesta registrata dal tuo account.</p>}
            </div>
          </section>
        </aside>
      </div>
    </div>
  );
}
