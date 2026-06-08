"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";

import { UtenzeModulePage } from "@/components/utenze/utenze-module-page";
import { EmptyState } from "@/components/ui/empty-state";
import { AlertTriangleIcon, CheckIcon, FolderIcon, RefreshIcon, SearchIcon } from "@/components/ui/icons";
import { getUtenzeVisureRoutingAnomalies, resolveUtenzeVisureRoutingAnomaly } from "@/lib/api";
import { formatDateTime } from "@/lib/presentation";
import type { UtenzeVisuraRoutingAnomaly, UtenzeVisuraRoutingAnomalyListResponse } from "@/types/api";

const PAGE_SIZE = 25;

function reasonLabel(reason: string): string {
  switch (reason) {
    case "invalid_filename":
      return "Nome file non valido";
    case "subject_not_found":
      return "Soggetto non trovato";
    case "subject_profile_missing":
      return "Profilo soggetto incompleto";
    case "subject_path_unresolved":
      return "Percorso NAS non risolto";
    default:
      return reason;
  }
}

function detailsText(details: UtenzeVisuraRoutingAnomaly["details_json"]): string {
  if (!details) return "Nessun dettaglio aggiuntivo.";
  if (Array.isArray(details)) return details.map((item) => String(item)).join(" · ");
  return Object.entries(details)
    .map(([key, value]) => `${key}: ${value === null ? "—" : String(value)}`)
    .join(" · ");
}

function AnomaliesContent({ token, isAdmin }: { token: string; isAdmin: boolean }) {
  const [items, setItems] = useState<UtenzeVisuraRoutingAnomaly[]>([]);
  const [summary, setSummary] = useState<UtenzeVisuraRoutingAnomalyListResponse | null>(null);
  const [resolvedFilter, setResolvedFilter] = useState<"open" | "resolved" | "all">("open");
  const [search, setSearch] = useState("");
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [resolvingId, setResolvingId] = useState<string | null>(null);

  const resolvedParam = useMemo(() => {
    if (resolvedFilter === "all") return undefined;
    return resolvedFilter === "resolved";
  }, [resolvedFilter]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await getUtenzeVisureRoutingAnomalies(token, {
        resolved: resolvedParam,
        search: query || undefined,
        page,
        pageSize: PAGE_SIZE,
      });
      setItems(response.items);
      setSummary(response);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Errore caricamento anomalie visure");
    } finally {
      setLoading(false);
    }
  }, [page, query, resolvedParam, token]);

  useEffect(() => {
    if (!isAdmin) return;
    void load();
  }, [isAdmin, load]);

  async function handleResolve(anomalyId: string) {
    setResolvingId(anomalyId);
    setError(null);
    try {
      await resolveUtenzeVisureRoutingAnomaly(token, anomalyId);
      await load();
    } catch (resolveError) {
      setError(resolveError instanceof Error ? resolveError.message : "Errore risoluzione anomalia");
    } finally {
      setResolvingId(null);
    }
  }

  const pageCount = Math.max(1, Math.ceil((summary?.total ?? 0) / PAGE_SIZE));

  if (!isAdmin) {
    return (
      <EmptyState
        icon={AlertTriangleIcon}
        title="Accesso riservato"
        description="Le anomalie di routing visure possono essere consultate e risolte solo da amministratori."
      />
    );
  }

  return (
    <div className="space-y-6">
      <section className="grid gap-4 md:grid-cols-4">
        <article className="rounded-[24px] border border-[#d9dfd6] bg-white p-5 shadow-panel">
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-[#4F6F52]">Totale</p>
          <p className="mt-3 text-3xl font-semibold text-slate-900">{summary?.total ?? "—"}</p>
          <p className="mt-2 text-sm text-slate-500">Risultati del filtro corrente</p>
        </article>
        <article className="rounded-[24px] border border-[#d9dfd6] bg-white p-5 shadow-panel">
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-[#4F6F52]">Aperte</p>
          <p className="mt-3 text-3xl font-semibold text-amber-700">{summary?.unresolved ?? "—"}</p>
          <p className="mt-2 text-sm text-slate-500">Da gestire lato admin</p>
        </article>
        <article className="rounded-[24px] border border-[#d9dfd6] bg-white p-5 shadow-panel">
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-[#4F6F52]">Risolte</p>
          <p className="mt-3 text-3xl font-semibold text-emerald-700">{summary?.resolved ?? "—"}</p>
          <p className="mt-2 text-sm text-slate-500">Chiuse manualmente o dal job</p>
        </article>
        <article className="rounded-[24px] border border-[#d9dfd6] bg-white p-5 shadow-panel">
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-[#4F6F52]">Regola file</p>
          <p className="mt-3 text-lg font-semibold text-slate-900">Solo PDF / Excel</p>
          <p className="mt-2 text-sm text-slate-500">`.dat` e altre estensioni vengono ignorate</p>
        </article>
      </section>

      <section className="rounded-[28px] border border-[#d9dfd6] bg-white p-6 shadow-panel">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="section-title">Anomalie routing visure</p>
            <p className="section-copy">
              File rimasti nella cartella pubblica perché il job non riesce a collegarli a un soggetto o a costruire il path corretto.
            </p>
          </div>
          <div className="flex flex-col gap-3 sm:flex-row">
            <label className="flex min-w-[220px] items-center gap-2 rounded-2xl border border-[#d9dfd6] bg-[#f8faf8] px-3 py-2 text-sm text-slate-600">
              <SearchIcon className="h-4 w-4 text-slate-400" />
              <input
                className="w-full bg-transparent outline-none"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter") {
                    setPage(1);
                    setQuery(search.trim());
                  }
                }}
                placeholder="Cerca per file, CF/PIVA, path"
              />
            </label>
            <select
              className="rounded-2xl border border-[#d9dfd6] bg-white px-3 py-2 text-sm text-slate-700"
              value={resolvedFilter}
              onChange={(event) => {
                setResolvedFilter(event.target.value as "open" | "resolved" | "all");
                setPage(1);
              }}
            >
              <option value="open">Solo aperte</option>
              <option value="resolved">Solo risolte</option>
              <option value="all">Tutte</option>
            </select>
            <button className="btn-secondary" type="button" onClick={() => void load()} disabled={loading}>
              <RefreshIcon className="h-4 w-4" />
              <span>{loading ? "Aggiorno..." : "Aggiorna"}</span>
            </button>
          </div>
        </div>

        {error ? (
          <div className="mt-4 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</div>
        ) : null}

        {loading ? (
          <div className="mt-6 rounded-2xl border border-dashed border-[#d9dfd6] bg-[#f8faf8] px-4 py-8 text-sm text-slate-500">
            Caricamento anomalie in corso...
          </div>
        ) : items.length === 0 ? (
          <div className="mt-6">
            <EmptyState
              icon={CheckIcon}
              title="Nessuna anomalia"
              description="Il routing delle visure non ha trovato anomalie compatibili con il filtro attivo."
            />
          </div>
        ) : (
          <div className="mt-6 space-y-4">
            {items.map((item) => (
              <article key={item.id} className="rounded-[24px] border border-[#d9dfd6] bg-[#fcfdfc] p-5">
                <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
                  <div className="min-w-0 space-y-3">
                    <div className="flex flex-wrap items-center gap-2">
                      <span
                        className={`rounded-full px-2.5 py-1 text-xs font-semibold ${
                          item.resolved_at ? "bg-emerald-100 text-emerald-800" : "bg-amber-100 text-amber-800"
                        }`}
                      >
                        {item.resolved_at ? "Risolta" : "Aperta"}
                      </span>
                      <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700">{reasonLabel(item.reason)}</span>
                      {item.identifier ? (
                        <span className="rounded-full bg-[#EAF3E8] px-2.5 py-1 text-xs font-medium text-[#1D4E35]">
                          {item.identifier_kind === "company" ? "P.IVA/CF azienda" : "CF"} {item.identifier}
                        </span>
                      ) : null}
                    </div>
                    <div>
                      <p className="text-sm font-semibold text-slate-900">{item.filename}</p>
                      <p className="mt-1 break-all text-sm text-slate-500">{item.source_path}</p>
                    </div>
                    <p className="text-sm text-slate-600">{detailsText(item.details_json)}</p>
                    <div className="flex flex-wrap gap-4 text-xs text-slate-500">
                      <span>Occorrenze: {item.occurrences}</span>
                      <span>Creata: {formatDateTime(item.created_at)}</span>
                      <span>Aggiornata: {formatDateTime(item.updated_at)}</span>
                      <span>Risolta: {item.resolved_at ? formatDateTime(item.resolved_at) : "No"}</span>
                    </div>
                  </div>
                  <div className="flex shrink-0 flex-wrap gap-2">
                    <Link className="btn-secondary" href="/utenze/import">
                      <FolderIcon className="h-4 w-4" />
                      <span>Import utenze</span>
                    </Link>
                    {!item.resolved_at ? (
                      <button
                        className="btn-primary"
                        type="button"
                        disabled={resolvingId === item.id}
                        onClick={() => void handleResolve(item.id)}
                      >
                        <CheckIcon className="h-4 w-4" />
                        <span>{resolvingId === item.id ? "Risolvo..." : "Segna risolta"}</span>
                      </button>
                    ) : null}
                  </div>
                </div>
              </article>
            ))}
          </div>
        )}

        <div className="mt-6 flex items-center justify-between border-t border-[#e6ece4] pt-4">
          <p className="text-sm text-slate-500">
            Pagina {page} di {pageCount}
          </p>
          <div className="flex gap-2">
            <button className="btn-secondary" type="button" disabled={page <= 1} onClick={() => setPage((current) => current - 1)}>
              Precedente
            </button>
            <button
              className="btn-secondary"
              type="button"
              disabled={page >= pageCount}
              onClick={() => setPage((current) => current + 1)}
            >
              Successiva
            </button>
          </div>
        </div>
      </section>
    </div>
  );
}

export default function UtenzeVisureRoutingAnomaliesPage() {
  return (
    <UtenzeModulePage
      title="Anomalie visure"
      description="Controllo amministrativo sui file visure rimasti fuori dalla cartella utente corretta."
      breadcrumb="Utenze / Anomalie visure"
    >
      {({ token, currentUser }) => (
        <AnomaliesContent token={token} isAdmin={currentUser.role === "admin" || currentUser.role === "super_admin"} />
      )}
    </UtenzeModulePage>
  );
}
