"use client";

import { useDeferredValue, useEffect, useMemo, useState } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import { useSearchParams } from "next/navigation";

import { DataTable } from "@/components/table/data-table";
import { FilterPillGroup } from "@/components/network/filter-pill-group";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { MetricCard } from "@/components/ui/metric-card";
import { SearchIcon } from "@/components/ui/icons";
import {
  exportWikiToolAuditLogs,
  resolveWikiConversationContextLink,
  getWikiToolAuditLogDetail,
  getWikiToolAuditLogs,
  getWikiToolAuditRelatedLogs,
  getWikiToolAuditSummary,
} from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import type { WikiConversationContextLink, WikiToolAuditLog, WikiToolAuditSummary } from "@/types/api";
import { buildWikiContextHref } from "./context-links";
import {
  buildWikiAuditStats,
  formatWikiAuditBoolean,
  formatWikiAuditCreatedAt,
  formatWikiAuditLatency,
} from "./audit-utils";

type AuditModeFilter = "all" | "docs_only" | "live_data" | "logic" | "hybrid";
type AuditIntentFilter = "all" | "docs_only" | "live_data" | "logic";
type AuditSuccessFilter = "all" | "success" | "denied";

const PAGE_SIZE = 25;

const modeOptions: Array<{ value: AuditModeFilter; label: string }> = [
  { value: "all", label: "Tutte le mode" },
  { value: "docs_only", label: "Docs" },
  { value: "live_data", label: "Live" },
  { value: "logic", label: "Logic" },
  { value: "hybrid", label: "Hybrid" },
];

const intentOptions: Array<{ value: AuditIntentFilter; label: string }> = [
  { value: "all", label: "Tutti gli intent" },
  { value: "docs_only", label: "Docs only" },
  { value: "live_data", label: "Live data" },
  { value: "logic", label: "Logic" },
];

const successOptions: Array<{ value: AuditSuccessFilter; label: string }> = [
  { value: "all", label: "Tutti gli esiti" },
  { value: "success", label: "Successo" },
  { value: "denied", label: "Denied / failure" },
];

const quickModeOptions = [
  { value: "all", label: "Tutto" },
  { value: "docs_only", label: "Docs" },
  { value: "live_data", label: "Live" },
  { value: "logic", label: "Logic" },
  { value: "hybrid", label: "Hybrid" },
] as const;

const quickSuccessOptions = [
  { value: "all", label: "Tutti" },
  { value: "success", label: "Successi" },
  { value: "denied", label: "Denied" },
] as const;

function modeBadgeVariant(mode: string): "success" | "info" | "warning" | "neutral" {
  if (mode === "live_data") {
    return "info";
  }
  if (mode === "logic") {
    return "warning";
  }
  if (mode === "hybrid") {
    return "neutral";
  }
  return "success";
}

function successBadgeVariant(success: boolean): "success" | "danger" {
  return success ? "success" : "danger";
}

function humanizeMode(mode: string): string {
  if (mode === "docs_only") return "Docs";
  if (mode === "live_data") return "Live";
  if (mode === "logic") return "Logic";
  if (mode === "hybrid") return "Hybrid";
  return mode;
}

function humanizeIntent(intent: string): string {
  if (intent === "docs_only") return "Docs only";
  if (intent === "live_data") return "Live data";
  if (intent === "logic") return "Logic";
  if (intent === "hybrid") return "Hybrid";
  return intent;
}

function humanizeModule(moduleKey: string | null | undefined): string {
  if (!moduleKey || moduleKey === "n/d") return "Modulo non dichiarato";
  if (moduleKey === "rete") return "Rete";
  if (moduleKey === "accessi") return "Accessi";
  if (moduleKey === "catasto") return "Catasto";
  if (moduleKey === "operazioni") return "Operazioni";
  if (moduleKey === "riordino") return "Riordino";
  if (moduleKey === "ruolo") return "Ruolo";
  if (moduleKey === "wiki") return "Wiki";
  return moduleKey;
}

function humanizeFallback(value: string | null | undefined): string {
  if (!value || value === "n/d") return "Nessun fallback";
  if (value === "docs_only") return "Docs only";
  if (value === "docs_insufficient_context") return "Contesto docs insufficiente";
  if (value === "unsupported_access_request") return "Richiesta accesso bloccata";
  if (value === "unsupported_action_request") return "Richiesta azione bloccata";
  if (value === "unsupported_external_live") return "Richiesta live esterna bloccata";
  return value;
}

export function WikiAuditPage() {
  const searchParams = useSearchParams();
  const [items, setItems] = useState<WikiToolAuditLog[]>([]);
  const [summary, setSummary] = useState<WikiToolAuditSummary | null>(null);
  const [selectedLog, setSelectedLog] = useState<WikiToolAuditLog | null>(null);
  const [selectedDetail, setSelectedDetail] = useState<WikiToolAuditLog | null>(null);
  const [relatedLogs, setRelatedLogs] = useState<WikiToolAuditLog[]>([]);
  const [resolvedContextLink, setResolvedContextLink] = useState<WikiConversationContextLink | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [refreshTick, setRefreshTick] = useState(0);
  const [usernameFilter, setUsernameFilter] = useState("");
  const [toolFilter, setToolFilter] = useState("");
  const [moduleFilter, setModuleFilter] = useState("");
  const [intentFilter, setIntentFilter] = useState<AuditIntentFilter>("all");
  const [modeFilter, setModeFilter] = useState<AuditModeFilter>("all");
  const [successFilter, setSuccessFilter] = useState<AuditSuccessFilter>("all");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const deferredUsernameFilter = useDeferredValue(usernameFilter.trim());
  const deferredToolFilter = useDeferredValue(toolFilter.trim());
  const deferredModuleFilter = useDeferredValue(moduleFilter.trim());
  const conversationIdFilter = searchParams?.get("conversation_id")?.trim() ?? "";

  useEffect(() => {
    setPage(1);
  }, [deferredUsernameFilter, deferredToolFilter, deferredModuleFilter, intentFilter, modeFilter, successFilter, conversationIdFilter]);

  useEffect(() => {
    async function loadAudit() {
      const token = getStoredAccessToken();
      if (!token) {
        setError("Sessione non disponibile.");
        setItems([]);
        setTotal(0);
        setIsLoading(false);
        return;
      }

      setIsLoading(true);
      try {
        const params = {
          username: deferredUsernameFilter || undefined,
          toolName: deferredToolFilter || undefined,
          moduleKey: deferredModuleFilter || undefined,
          conversationId: conversationIdFilter || undefined,
          intent: intentFilter === "all" ? undefined : intentFilter,
          mode: modeFilter === "all" ? undefined : modeFilter,
          success:
            successFilter === "all"
              ? null
              : successFilter === "success",
        } as const;
        const [response, summaryResponse] = await Promise.all([
          getWikiToolAuditLogs(token, {
            page,
            pageSize: PAGE_SIZE,
            ...params,
          }),
          getWikiToolAuditSummary(token, params),
        ]);
        setItems(response.items);
        setTotal(response.total);
        setSummary(summaryResponse);
        setError(null);
      } catch (loadError) {
        setItems([]);
        setTotal(0);
        setSummary(null);
        setError(loadError instanceof Error ? loadError.message : "Errore caricamento audit Wiki");
      } finally {
        setIsLoading(false);
      }
    }

    void loadAudit();
  }, [page, deferredUsernameFilter, deferredToolFilter, deferredModuleFilter, intentFilter, modeFilter, successFilter, refreshTick, conversationIdFilter]);

  useEffect(() => {
    async function loadDetail() {
      if (!selectedLog) {
        setSelectedDetail(null);
        setRelatedLogs([]);
        return;
      }
      const token = getStoredAccessToken();
      if (!token) {
        return;
      }
      setDetailLoading(true);
      try {
        const response = await getWikiToolAuditLogDetail(token, selectedLog.id);
        const relatedResponse = await getWikiToolAuditRelatedLogs(token, selectedLog.id, { limit: 8 });
        const contextLink = await resolveWikiConversationContextLink(token, {
          entityKey: response.item.entity_key,
          moduleKey: response.item.module_key,
        });
        setSelectedDetail(response.item);
        setRelatedLogs(relatedResponse.items);
        setResolvedContextLink(contextLink);
      } catch {
        setSelectedDetail(selectedLog);
        setRelatedLogs([]);
        setResolvedContextLink(null);
      } finally {
        setDetailLoading(false);
      }
    }

    void loadDetail();
  }, [selectedLog]);

  const pageStats = useMemo(() => buildWikiAuditStats(items), [items]);
  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const detailHref = resolvedContextLink?.href ?? buildWikiContextHref(selectedDetail?.entity_key ?? selectedLog?.entity_key, selectedDetail?.module_key ?? selectedLog?.module_key);
  const conversationHref = selectedDetail?.conversation_id ? `/wiki?conversation=${selectedDetail.conversation_id}` : null;
  const topTools = summary?.top_tools ?? pageStats.topTools;
  const topModules = summary?.top_modules ?? pageStats.topModules;
  const topIntents = summary?.top_intents ?? pageStats.topIntents;
  const topDeniedTools = summary?.top_denied_tools ?? pageStats.topDeniedTools;
  const latencyByMode = summary?.latency_by_mode ?? [];
  const dailyCounts = summary?.daily_counts ?? [];
  const activeFilters = [
    deferredUsernameFilter ? `Utente: ${deferredUsernameFilter}` : null,
    deferredToolFilter ? `Tool: ${deferredToolFilter}` : null,
    deferredModuleFilter ? `Modulo: ${humanizeModule(deferredModuleFilter)}` : null,
    intentFilter !== "all" ? `Intent: ${humanizeIntent(intentFilter)}` : null,
    modeFilter !== "all" ? `Mode: ${humanizeMode(modeFilter)}` : null,
    successFilter !== "all" ? `Esito: ${successFilter === "success" ? "Successo" : "Denied"}` : null,
    conversationIdFilter ? "Filtro conversazione attivo" : null,
  ].filter(Boolean) as string[];

  async function handleExportAudit() {
    const token = getStoredAccessToken();
    if (!token) {
      setError("Sessione non disponibile.");
      return;
    }
    try {
      const blob = await exportWikiToolAuditLogs(token, {
        username: deferredUsernameFilter || undefined,
        toolName: deferredToolFilter || undefined,
        moduleKey: deferredModuleFilter || undefined,
        intent: intentFilter === "all" ? undefined : intentFilter,
        mode: modeFilter === "all" ? undefined : modeFilter,
        success: successFilter === "all" ? null : successFilter === "success",
      });
      const href = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = href;
      link.download = "wiki-audit-tool-calls.csv";
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(href);
    } catch (downloadError) {
      setError(downloadError instanceof Error ? downloadError.message : "Errore export audit Wiki");
    }
  }

  const columns = useMemo<ColumnDef<WikiToolAuditLog>[]>(
    () => [
      {
        header: "Quando",
        accessorKey: "created_at",
        cell: ({ row }) => <span className="text-sm text-gray-700">{formatWikiAuditCreatedAt(row.original.created_at)}</span>,
      },
      {
        header: "Utente",
        accessorKey: "username",
        cell: ({ row }) => (
          <div className="min-w-0">
            <p className="truncate text-sm font-medium text-gray-900">{row.original.username}</p>
            <p className="truncate text-xs text-gray-400">{row.original.role}</p>
          </div>
        ),
      },
      {
        header: "Tool",
        accessorKey: "tool_name",
        cell: ({ row }) => (
          <div className="min-w-0">
            <p className="truncate text-sm font-medium text-[#1D4E35]">{row.original.tool_name}</p>
            <p className="truncate text-xs text-gray-400">{humanizeModule(row.original.module_key)}</p>
          </div>
        ),
      },
      {
        header: "Intent / Mode",
        accessorKey: "intent",
        cell: ({ row }) => (
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="neutral">{humanizeIntent(row.original.intent)}</Badge>
            <Badge variant={modeBadgeVariant(row.original.mode)}>{humanizeMode(row.original.mode)}</Badge>
          </div>
        ),
      },
      {
        header: "Esito",
        accessorKey: "success",
        cell: ({ row }) => (
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant={successBadgeVariant(row.original.success)}>
              {formatWikiAuditBoolean(row.original.success, "Successo", "Denied")}
            </Badge>
            <Badge variant={row.original.found ? "info" : "warning"}>
              {formatWikiAuditBoolean(row.original.found, "Found", "No match")}
            </Badge>
          </div>
        ),
      },
      {
        header: "Domanda",
        accessorKey: "question_preview",
        cell: ({ row }) => (
          <div className="min-w-[16rem] max-w-[28rem]">
            <p className="line-clamp-2 text-sm text-gray-700">{row.original.question_preview}</p>
            <p className="mt-1 truncate font-mono text-[11px] text-gray-400">{row.original.question_hash}</p>
          </div>
        ),
      },
      {
        header: "Latenza",
        accessorKey: "latency_ms",
        cell: ({ row }) => <span className="text-sm text-gray-700">{formatWikiAuditLatency(row.original.latency_ms)}</span>,
      },
    ],
    [],
  );

  if (error && !isLoading && items.length === 0) {
    return (
      <EmptyState
        icon={SearchIcon}
        title="Audit Wiki non disponibile"
        description={error}
      />
    );
  }

  return (
    <div className="space-y-6">
      <section className="rounded-[2rem] border border-[#d9dfd4] bg-[radial-gradient(circle_at_top_left,_rgba(220,239,227,0.9),_rgba(255,255,255,0.98)_58%)] p-6 shadow-sm">
        <div className="grid gap-6 xl:grid-cols-[minmax(0,1.15fr)_26rem]">
          <div className="space-y-4">
            <div>
              <p className="inline-flex items-center rounded-full border border-white/70 bg-white/80 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.22em] text-[#1D4E35]">
                Audit operativo Wiki
              </p>
              <h2 className="mt-4 max-w-3xl text-3xl font-semibold tracking-tight text-gray-950">
                Traccia tool call, fallback e tempi di risposta del Wiki Agent.
              </h2>
              <p className="mt-3 max-w-2xl text-sm leading-6 text-gray-600">
                Questa vista serve a capire se il router sta instradando bene, quali moduli vengono interrogati e dove il Wiki
                cade in fallback documentale o blocco strutturale.
              </p>
            </div>

            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              <div className="rounded-2xl border border-white/70 bg-white/80 p-4">
                <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-gray-400">Tasso successo</p>
                <p className="mt-3 text-2xl font-semibold text-gray-950">
                  {summary?.total ? `${Math.round((summary.success_count / summary.total) * 100)}%` : "0%"}
                </p>
                <p className="mt-1 text-xs text-gray-500">Tool call andate a buon fine nel filtro corrente.</p>
              </div>
              <div className="rounded-2xl border border-white/70 bg-white/80 p-4">
                <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-gray-400">Fallback docs</p>
                <p className="mt-3 text-2xl font-semibold text-gray-950">{(summary?.docs_only_count ?? pageStats.docsCount).toLocaleString("it-IT")}</p>
                <p className="mt-1 text-xs text-gray-500">Risposte documentali pure senza lettura live.</p>
              </div>
              <div className="rounded-2xl border border-white/70 bg-white/80 p-4">
                <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-gray-400">No match</p>
                <p className="mt-3 text-2xl font-semibold text-gray-950">{(summary?.no_match_count ?? pageStats.noMatchCount).toLocaleString("it-IT")}</p>
                <p className="mt-1 text-xs text-gray-500">Dialoghi in cui il contesto non era abbastanza forte.</p>
              </div>
              <div className="rounded-2xl border border-white/70 bg-white/80 p-4">
                <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-gray-400">Latenza media</p>
                <p className="mt-3 text-2xl font-semibold text-gray-950">{formatWikiAuditLatency(summary?.avg_latency_ms ?? pageStats.avgLatencyMs)}</p>
                <p className="mt-1 text-xs text-gray-500">Tempo medio risposta sul dataset filtrato.</p>
              </div>
            </div>
          </div>

          <div className="space-y-3">
            <div className="rounded-2xl border border-emerald-200 bg-white/90 p-4">
              <p className="text-sm font-semibold text-[#1D4E35]">Perimetro osservato</p>
              <p className="mt-2 text-sm text-gray-600">
                {total.toLocaleString("it-IT")} record filtrati. Focus principale su{" "}
                <span className="font-medium text-gray-900">{topTools[0]?.key ?? "n/d"}</span> e modulo{" "}
                <span className="font-medium text-gray-900">{humanizeModule(topModules[0]?.key)}</span>.
              </p>
            </div>
            <div className="rounded-2xl border border-sky-200 bg-white/90 p-4">
              <p className="text-sm font-semibold text-sky-900">Segnale rapido</p>
              <p className="mt-2 text-sm text-gray-600">
                {topDeniedTools.length > 0
                  ? `Il tool più problematico è ${topDeniedTools[0].key} con ${topDeniedTools[0].count} denied.`
                  : "Non ci sono denied nel dataset filtrato."}
              </p>
            </div>
            <div className="rounded-2xl border border-amber-200 bg-white/90 p-4">
              <p className="text-sm font-semibold text-amber-900">Composizione query</p>
              <div className="mt-3 flex flex-wrap gap-2">
                {topIntents.slice(0, 3).map((item) => (
                  <span key={item.key} className="rounded-full border border-amber-200 bg-amber-50 px-3 py-1 text-xs font-medium text-amber-800">
                    {humanizeIntent(item.key)} · {item.count}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        <MetricCard label="Record totali" value={(summary?.total ?? total).toLocaleString("it-IT")} sub="Filtri server-side correnti" />
        <MetricCard label="Righe caricate" value={items.length.toLocaleString("it-IT")} sub={`Pagina ${page} di ${pageCount}`} />
        <MetricCard label="Successi" value={(summary?.success_count ?? pageStats.successCount).toLocaleString("it-IT")} sub="Nel dataset filtrato" variant="success" />
        <MetricCard label="Denied" value={(summary?.denied_count ?? pageStats.deniedCount).toLocaleString("it-IT")} sub="Tool negati o falliti" variant="danger" />
        <MetricCard
          label="Live / Logic / Hybrid"
          value={`${summary?.live_count ?? pageStats.liveCount} / ${summary?.logic_count ?? pageStats.logicCount} / ${summary?.hybrid_count ?? pageStats.hybridCount}`}
          sub={`Latenza media ${formatWikiAuditLatency(summary?.avg_latency_ms ?? pageStats.avgLatencyMs)}`}
          variant="info"
        />
      </section>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="No match" value={(summary?.no_match_count ?? pageStats.noMatchCount).toLocaleString("it-IT")} sub="Risposte senza match utile" variant="warning" />
        <MetricCard label="Docs only" value={(summary?.docs_only_count ?? pageStats.docsCount).toLocaleString("it-IT")} sub="Fallback documentali puri" />
        <MetricCard label="Top intent" value={summary?.top_intents[0]?.key ?? pageStats.topIntents[0]?.key ?? "n/d"} sub={`Ricorrenze ${summary?.top_intents[0]?.count ?? pageStats.topIntents[0]?.count ?? 0}`} />
        <MetricCard label="Top tool" value={summary?.top_tools[0]?.key ?? pageStats.topTools[0]?.key ?? "n/d"} sub={`Ricorrenze ${summary?.top_tools[0]?.count ?? pageStats.topTools[0]?.count ?? 0}`} />
      </section>

      <section className="grid gap-4 xl:grid-cols-3">
        <article className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Top tool</p>
          <div className="mt-3 space-y-2">
            {(summary?.top_tools ?? pageStats.topTools).length > 0 ? (summary?.top_tools ?? pageStats.topTools).map((item) => (
              <div key={item.key} className="flex items-center justify-between rounded-xl bg-[#f7f8f5] px-3 py-2 text-sm">
                <span className="truncate font-medium text-[#1D4E35]">{item.key}</span>
                <span className="text-gray-500">{item.count}</span>
              </div>
            )) : <p className="text-sm text-gray-500">Nessun dato nella pagina corrente.</p>}
          </div>
        </article>
        <article className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Top moduli</p>
          <div className="mt-3 space-y-2">
            {(summary?.top_modules ?? pageStats.topModules).length > 0 ? (summary?.top_modules ?? pageStats.topModules).map((item) => (
              <div key={item.key} className="flex items-center justify-between rounded-xl bg-[#f7f8f5] px-3 py-2 text-sm">
                <span className="truncate font-medium text-[#1D4E35]">{item.key}</span>
                <span className="text-gray-500">{item.count}</span>
              </div>
            )) : <p className="text-sm text-gray-500">Nessun dato nella pagina corrente.</p>}
          </div>
        </article>
        <article className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Top intent</p>
          <div className="mt-3 space-y-2">
            {(summary?.top_intents ?? pageStats.topIntents).length > 0 ? (summary?.top_intents ?? pageStats.topIntents).map((item) => (
              <div key={item.key} className="flex items-center justify-between rounded-xl bg-[#f7f8f5] px-3 py-2 text-sm">
                <span className="truncate font-medium text-[#1D4E35]">{item.key}</span>
                <span className="text-gray-500">{item.count}</span>
              </div>
            )) : <p className="text-sm text-gray-500">Nessun dato nel dataset filtrato.</p>}
          </div>
        </article>
        <article className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Denied frequenti</p>
          <div className="mt-3 space-y-2">
            {(summary?.top_denied_tools ?? pageStats.topDeniedTools).length > 0 ? (summary?.top_denied_tools ?? pageStats.topDeniedTools).map((item) => (
              <div key={item.key} className="flex items-center justify-between rounded-xl bg-[#fff6f6] px-3 py-2 text-sm">
                <span className="truncate font-medium text-rose-700">{item.key}</span>
                <span className="text-rose-500">{item.count}</span>
              </div>
            )) : <p className="text-sm text-gray-500">Nessun denied nel dataset filtrato.</p>}
          </div>
        </article>
      </section>

      <section className="grid gap-4 xl:grid-cols-2">
        <article className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Latenza per mode</p>
          <div className="mt-3 space-y-2">
            {(summary?.latency_by_mode ?? []).length > 0 ? summary?.latency_by_mode.map((item) => (
              <div key={item.mode} className="flex items-center justify-between rounded-xl bg-[#f7f8f5] px-3 py-2 text-sm">
                <span className="truncate font-medium text-[#1D4E35]">{item.mode}</span>
                <span className="text-gray-500">{formatWikiAuditLatency(item.avg_latency_ms)}</span>
              </div>
            )) : <p className="text-sm text-gray-500">Nessuna aggregazione disponibile.</p>}
          </div>
        </article>
        <article className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Trend ultimi 7 giorni</p>
          <div className="mt-3 space-y-2">
            {(summary?.daily_counts ?? []).length > 0 ? summary?.daily_counts.map((item) => (
              <div key={item.day} className="flex items-center justify-between rounded-xl bg-[#f7f8f5] px-3 py-2 text-sm">
                <span className="truncate font-medium text-[#1D4E35]">{item.day}</span>
                <span className="text-gray-500">Tot {item.total} / Denied {item.denied}</span>
              </div>
            )) : <p className="text-sm text-gray-500">Nessun trend disponibile.</p>}
          </div>
        </article>
      </section>

      <section className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_24rem]">
      <div className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Audit tool call</p>
            <h3 className="mt-1 text-lg font-semibold text-gray-900">Registro operativo Wiki Agent</h3>
            <p className="mt-1 text-sm text-gray-500">
              Filtri esatti lato backend su utente, tool e modulo. La preview domanda resta redatta e troncata.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              className="btn-secondary"
              type="button"
              onClick={() => setRefreshTick((current) => current + 1)}
              disabled={isLoading}
            >
              Aggiorna
            </button>
            <button className="btn-secondary" type="button" onClick={() => void handleExportAudit()}>
              Export CSV
            </button>
          </div>
        </div>

        {activeFilters.length > 0 ? (
          <div className="mt-4 rounded-2xl border border-[#dfe7df] bg-[#fbfcfa] px-4 py-3">
            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-gray-400">Perimetro attivo</p>
            <div className="mt-2 flex flex-wrap gap-2">
              {activeFilters.map((item) => (
                <span
                  key={item}
                  className="rounded-full border border-[#d7e5db] bg-white px-3 py-1 text-xs font-medium text-[#1D4E35]"
                >
                  {item}
                </span>
              ))}
            </div>
          </div>
        ) : null}

        <div className="mt-4 flex flex-wrap items-center gap-3 rounded-2xl border border-[#dfe7df] bg-[#f8fbf8] px-4 py-3">
          <div className="min-w-[12rem] flex-1">
            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-gray-400">Quick filter mode</p>
            <div className="mt-2">
              <FilterPillGroup options={quickModeOptions} value={modeFilter} onChange={setModeFilter} />
            </div>
          </div>
          <div className="min-w-[11rem] flex-1">
            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-gray-400">Quick filter esito</p>
            <div className="mt-2">
              <FilterPillGroup options={quickSuccessOptions} value={successFilter} onChange={setSuccessFilter} />
            </div>
          </div>
        </div>

        <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-6">
          <label className="space-y-1">
            <span className="text-xs font-medium uppercase tracking-wide text-gray-400">Utente</span>
            <input
              className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm text-gray-700 outline-none transition focus:border-[#1D4E35] focus:ring-2 focus:ring-[#1D4E35]/10"
              value={usernameFilter}
              onChange={(event) => setUsernameFilter(event.target.value)}
              placeholder="username esatto"
            />
          </label>
          <label className="space-y-1">
            <span className="text-xs font-medium uppercase tracking-wide text-gray-400">Tool</span>
            <input
              className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm text-gray-700 outline-none transition focus:border-[#1D4E35] focus:ring-2 focus:ring-[#1D4E35]/10"
              value={toolFilter}
              onChange={(event) => setToolFilter(event.target.value)}
              placeholder="find_nas_user"
            />
          </label>
          <label className="space-y-1">
            <span className="text-xs font-medium uppercase tracking-wide text-gray-400">Modulo</span>
            <input
              className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm text-gray-700 outline-none transition focus:border-[#1D4E35] focus:ring-2 focus:ring-[#1D4E35]/10"
              value={moduleFilter}
              onChange={(event) => setModuleFilter(event.target.value)}
              placeholder="accessi"
            />
          </label>
          <label className="space-y-1">
            <span className="text-xs font-medium uppercase tracking-wide text-gray-400">Intent</span>
            <select
              className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm text-gray-700 outline-none transition focus:border-[#1D4E35] focus:ring-2 focus:ring-[#1D4E35]/10"
              value={intentFilter}
              onChange={(event) => setIntentFilter(event.target.value as AuditIntentFilter)}
            >
              {intentOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <label className="space-y-1">
            <span className="text-xs font-medium uppercase tracking-wide text-gray-400">Mode</span>
            <select
              className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm text-gray-700 outline-none transition focus:border-[#1D4E35] focus:ring-2 focus:ring-[#1D4E35]/10"
              value={modeFilter}
              onChange={(event) => setModeFilter(event.target.value as AuditModeFilter)}
            >
              {modeOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <label className="space-y-1">
            <span className="text-xs font-medium uppercase tracking-wide text-gray-400">Esito</span>
            <select
              className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm text-gray-700 outline-none transition focus:border-[#1D4E35] focus:ring-2 focus:ring-[#1D4E35]/10"
              value={successFilter}
              onChange={(event) => setSuccessFilter(event.target.value as AuditSuccessFilter)}
            >
              {successOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
        </div>

        <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <div className="rounded-2xl border border-gray-100 bg-[#fafcf9] p-3">
            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-gray-400">Tool più usato</p>
            <p className="mt-2 truncate text-sm font-semibold text-[#1D4E35]">{topTools[0]?.key ?? "n/d"}</p>
          </div>
          <div className="rounded-2xl border border-gray-100 bg-[#fafcf9] p-3">
            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-gray-400">Modulo dominante</p>
            <p className="mt-2 truncate text-sm font-semibold text-[#1D4E35]">{humanizeModule(topModules[0]?.key)}</p>
          </div>
          <div className="rounded-2xl border border-gray-100 bg-[#fafcf9] p-3">
            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-gray-400">Intent dominante</p>
            <p className="mt-2 truncate text-sm font-semibold text-[#1D4E35]">{humanizeIntent(topIntents[0]?.key ?? "n/d")}</p>
          </div>
          <div className="rounded-2xl border border-gray-100 bg-[#fff8f6] p-3">
            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-gray-400">Denied più frequente</p>
            <p className="mt-2 truncate text-sm font-semibold text-rose-700">{topDeniedTools[0]?.key ?? "nessuno"}</p>
          </div>
        </div>

        <div className="mt-5">
          <DataTable
            data={items}
            columns={columns}
            disableSorting={false}
            onRowClick={(row) => setSelectedLog(row)}
            pagination={{
              pageIndex: page - 1,
              pageCount,
              canPreviousPage: page > 1,
              canNextPage: page < pageCount,
              onPreviousPage: () => setPage((current) => Math.max(1, current - 1)),
              onNextPage: () => setPage((current) => Math.min(pageCount, current + 1)),
            }}
          />
        </div>
      </div>

      <aside className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Drill-down</p>
        <h3 className="mt-1 text-lg font-semibold text-gray-900">Dettaglio tool call</h3>
        {!selectedLog ? (
          <p className="mt-3 text-sm text-gray-500">Seleziona una riga della tabella per vedere contesto, fallback e segnali operativi.</p>
        ) : detailLoading ? (
          <p className="mt-3 text-sm text-gray-500">Caricamento dettaglio audit...</p>
        ) : (
          <div className="mt-4 space-y-3 text-sm">
            <div className="rounded-xl bg-[#f7f8f5] p-3">
              <p className="font-medium text-[#1D4E35]">{selectedDetail?.tool_name ?? selectedLog.tool_name}</p>
              <p className="mt-1 text-gray-600">{selectedDetail?.question_preview ?? selectedLog.question_preview}</p>
              <div className="mt-3 flex flex-wrap gap-2">
                <Badge variant={modeBadgeVariant(selectedDetail?.mode ?? selectedLog.mode)}>
                  {humanizeMode(selectedDetail?.mode ?? selectedLog.mode)}
                </Badge>
                <Badge variant="neutral">
                  {humanizeIntent(selectedDetail?.intent ?? selectedLog.intent)}
                </Badge>
                <Badge variant={successBadgeVariant(selectedDetail?.success ?? selectedLog.success)}>
                  {formatWikiAuditBoolean(selectedDetail?.success ?? selectedLog.success, "Successo", "Denied")}
                </Badge>
                <Badge variant={(selectedDetail?.found ?? selectedLog.found) ? "info" : "warning"}>
                  {formatWikiAuditBoolean(selectedDetail?.found ?? selectedLog.found, "Found", "No match")}
                </Badge>
              </div>
              {detailHref ? (
                <a href={detailHref} className="mt-2 inline-flex text-xs font-medium text-[#1D4E35] underline underline-offset-2">
                  {resolvedContextLink?.resolved ? "Apri record modulo" : "Apri contesto modulo"}
                </a>
              ) : null}
              {conversationHref ? (
                <a href={conversationHref} className="mt-2 ml-3 inline-flex text-xs font-medium text-[#1D4E35] underline underline-offset-2">
                  Apri conversazione
                </a>
              ) : null}
            </div>
            <div className="grid gap-2 sm:grid-cols-2">
              <div className="rounded-xl border border-gray-100 p-3">
                <p className="text-xs uppercase tracking-wide text-gray-400">Utente</p>
                <p className="mt-1 font-medium text-gray-900">{selectedDetail?.username ?? selectedLog.username}</p>
              </div>
              <div className="rounded-xl border border-gray-100 p-3">
                <p className="text-xs uppercase tracking-wide text-gray-400">Modulo</p>
                <p className="mt-1 font-medium text-gray-900">{humanizeModule(selectedDetail?.module_key ?? selectedLog.module_key)}</p>
              </div>
              <div className="rounded-xl border border-gray-100 p-3">
                <p className="text-xs uppercase tracking-wide text-gray-400">Entity key</p>
                <p className="mt-1 break-all font-medium text-gray-900">{selectedDetail?.entity_key ?? "n/d"}</p>
              </div>
              <div className="rounded-xl border border-gray-100 p-3">
                <p className="text-xs uppercase tracking-wide text-gray-400">Entity label</p>
                <p className="mt-1 font-medium text-gray-900">{selectedDetail?.entity_label ?? "n/d"}</p>
              </div>
              <div className="rounded-xl border border-gray-100 p-3">
                <p className="text-xs uppercase tracking-wide text-gray-400">Context article</p>
                <p className="mt-1 break-all font-medium text-gray-900">{selectedDetail?.context_article ?? "n/d"}</p>
              </div>
              <div className="rounded-xl border border-gray-100 p-3">
                <p className="text-xs uppercase tracking-wide text-gray-400">Fallback reason</p>
                <p className="mt-1 font-medium text-gray-900">
                  {humanizeFallback(selectedDetail?.fallback_reason)}
                </p>
              </div>
            </div>
            <div className="rounded-xl border border-gray-100 p-3">
              <p className="text-xs uppercase tracking-wide text-gray-400">Response excerpt</p>
              <p className="mt-1 text-gray-700">{selectedDetail?.response_excerpt ?? "n/d"}</p>
            </div>
            <div className="grid gap-2 sm:grid-cols-2">
              <div className="rounded-xl border border-gray-100 p-3">
                <p className="text-xs uppercase tracking-wide text-gray-400">Lat. media tool call</p>
                <p className="mt-1 font-medium text-gray-900">
                  {formatWikiAuditLatency(selectedDetail?.latency_ms ?? selectedLog.latency_ms)}
                </p>
              </div>
              <div className="rounded-xl border border-gray-100 p-3">
                <p className="text-xs uppercase tracking-wide text-gray-400">Timestamp</p>
                <p className="mt-1 font-medium text-gray-900">
                  {formatWikiAuditCreatedAt(selectedDetail?.created_at ?? selectedLog.created_at)}
                </p>
              </div>
            </div>
            <div className="grid gap-2 sm:grid-cols-2">
              <div className="rounded-xl border border-gray-100 p-3">
                <p className="text-xs uppercase tracking-wide text-gray-400">Docs sources</p>
                <p className="mt-1 font-medium text-gray-900">{selectedDetail?.docs_source_count ?? 0}</p>
              </div>
              <div className="rounded-xl border border-gray-100 p-3">
                <p className="text-xs uppercase tracking-wide text-gray-400">Evidences</p>
                <p className="mt-1 font-medium text-gray-900">{selectedDetail?.evidence_count ?? 0}</p>
              </div>
            </div>
            <div className="rounded-xl border border-gray-100 p-3">
              <p className="text-xs uppercase tracking-wide text-gray-400">Attività correlate</p>
              <div className="mt-2 space-y-2">
                {relatedLogs.length > 0 ? relatedLogs.map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    className="flex w-full items-start justify-between rounded-xl bg-[#f7f8f5] px-3 py-2 text-left text-sm"
                    onClick={() => setSelectedLog(item)}
                  >
                    <span className="min-w-0">
                      <span className="block truncate font-medium text-[#1D4E35]">{item.tool_name}</span>
                      <span className="block truncate text-gray-500">{item.question_preview}</span>
                    </span>
                    <span className="ml-3 whitespace-nowrap text-xs text-gray-400">{formatWikiAuditCreatedAt(item.created_at)}</span>
                  </button>
                )) : <p className="text-sm text-gray-500">Nessun record correlato.</p>}
              </div>
            </div>
          </div>
        )}
      </aside>
      </section>

      {error ? (
        <article className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
          {error}
        </article>
      ) : null}

    </div>
  );
}
