"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { EmptyState } from "@/components/ui/empty-state";
import { DocumentIcon, RefreshIcon, SearchIcon } from "@/components/ui/icons";
import { getStoredAccessToken } from "@/lib/auth";
import { listTributiRegisteredMails } from "@/lib/ruolo-api";
import type { RuoloTributiRegisteredMailListResponse, RuoloTributiRegisteredMailResponse } from "@/types/ruolo";

const PAGE_SIZE = 25;

const EMPTY_RESPONSE: RuoloTributiRegisteredMailListResponse = {
  items: [],
  total: 0,
  page: 1,
  page_size: PAGE_SIZE,
};

const MATCH_STATUS_LABELS: Record<string, string> = {
  matched: "Associata",
  unmatched: "Non associata",
  ambiguous: "Ambigua",
  error: "Errore",
};

const RECOVERY_STATUS_LABELS: Record<string, string> = {
  pending: "Da recuperare",
  recovered: "Recuperata",
  not_applicable: "Non applicabile",
};

function formatDate(value: string | null | undefined): string {
  if (!value) return "-";
  return new Intl.DateTimeFormat("it-IT", { dateStyle: "short" }).format(new Date(value));
}

function formatMoney(value: number | null | undefined): string {
  if (value == null) return "-";
  return new Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR" }).format(value);
}

function matchStatusLabel(value: string): string {
  return MATCH_STATUS_LABELS[value] ?? value;
}

function recoveryStatusLabel(value: string): string {
  return RECOVERY_STATUS_LABELS[value] ?? value;
}

function matchStatusClassName(value: string): string {
  if (value === "matched") return "border-emerald-200 bg-emerald-50 text-emerald-700";
  if (value === "ambiguous") return "border-amber-200 bg-amber-50 text-amber-800";
  if (value === "unmatched") return "border-red-200 bg-red-50 text-red-700";
  return "border-gray-200 bg-gray-100 text-gray-700";
}

function isAnomaly(item: RuoloTributiRegisteredMailResponse): boolean {
  return item.match_status !== "matched" || Boolean(item.anomaly_key);
}

type RegisteredMailsConsoleProps = {
  className?: string;
};

export function RegisteredMailsConsole({ className = "" }: RegisteredMailsConsoleProps) {
  const [response, setResponse] = useState<RuoloTributiRegisteredMailListResponse>(EMPTY_RESPONSE);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [matchStatus, setMatchStatus] = useState("");
  const [recoveryStatus, setRecoveryStatus] = useState("");
  const [anomaliesOnly, setAnomaliesOnly] = useState(true);
  const [page, setPage] = useState(1);

  async function loadData(nextPage = page): Promise<void> {
    const token = getStoredAccessToken();
    if (!token) return;
    setLoading(true);
    try {
      const trimmedQuery = query.trim();
      const data = await listTributiRegisteredMails(token, {
        q: trimmedQuery.length >= 3 ? trimmedQuery : undefined,
        match_status: matchStatus || undefined,
        recovery_status: recoveryStatus || undefined,
        anomalies_only: anomaliesOnly,
        page: nextPage,
        page_size: PAGE_SIZE,
      });
      setResponse(data);
      setError(null);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Errore caricamento raccomandate Poste Online");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    const handle = window.setTimeout(() => {
      setPage(1);
      void loadData(1);
    }, 350);
    return () => window.clearTimeout(handle);
  }, [query, matchStatus, recoveryStatus, anomaliesOnly]);

  const anomalyCount = response.items.filter(isAnomaly).length;
  const matchedCount = response.items.filter((item) => item.match_status === "matched").length;
  const canGoBack = page > 1;
  const canGoForward = page * response.page_size < response.total;

  function goToPage(nextPage: number): void {
    setPage(nextPage);
    void loadData(nextPage);
  }

  return (
    <section id="raccomandate-poste" className={`scroll-mt-6 rounded-[28px] border border-[#d8dfd3] bg-white shadow-panel ${className}`}>
      <div className="border-b border-[#edf1eb] px-6 py-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="inline-flex items-center gap-2 rounded-full bg-[#e8f2ec] px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.2em] text-[#1D4E35]">
              <DocumentIcon className="h-3.5 w-3.5" />
              Raccomandate Poste Online
            </p>
            <p className="mt-3 text-lg font-semibold text-gray-900">Matching e anomalie da archivio invii.</p>
            <p className="mt-1 max-w-3xl text-sm leading-6 text-gray-500">
              Poste non fornisce l&apos;ID avviso GAIA: qui controlliamo associazioni automatiche, casi ambigui e raccomandate non collegate.
            </p>
          </div>
          <button className="btn-secondary" onClick={() => void loadData(page)} type="button">
            <RefreshIcon className="mr-2 h-4 w-4" />
            Aggiorna raccomandate
          </button>
        </div>
      </div>

      <div className="space-y-5 p-6">
        <div className="grid gap-3 xl:grid-cols-[minmax(0,1.3fr),180px,180px,auto]">
          <label className="flex items-center gap-3 rounded-xl border border-gray-200 bg-white px-4 py-3 shadow-sm">
            <SearchIcon className="h-5 w-5 text-gray-400" />
            <input
              className="w-full border-0 bg-transparent text-sm outline-none"
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Destinatario, tracking, indirizzo, shipment id..."
              type="search"
              value={query}
            />
          </label>
          <select
            className="rounded-xl border border-gray-200 bg-white px-4 py-3 text-sm shadow-sm outline-none"
            onChange={(event) => setMatchStatus(event.target.value)}
            value={matchStatus}
          >
            <option value="">Tutti i match</option>
            <option value="matched">Associati</option>
            <option value="unmatched">Non associati</option>
            <option value="ambiguous">Ambigui</option>
          </select>
          <select
            className="rounded-xl border border-gray-200 bg-white px-4 py-3 text-sm shadow-sm outline-none"
            onChange={(event) => setRecoveryStatus(event.target.value)}
            value={recoveryStatus}
          >
            <option value="">Tutti recuperi</option>
            <option value="pending">Da recuperare</option>
            <option value="recovered">Recuperati</option>
            <option value="not_applicable">Non applicabili</option>
          </select>
          <label className="flex items-center gap-2 rounded-xl border border-[#e3e9e0] bg-[#fbfcfb] px-4 py-3 text-sm text-gray-700">
            <input checked={anomaliesOnly} onChange={(event) => setAnomaliesOnly(event.target.checked)} type="checkbox" />
            Solo anomalie
          </label>
        </div>

        <div className="grid gap-3 md:grid-cols-3">
          <div className="rounded-2xl border border-[#e2e9df] bg-[#fbfcfb] p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-500">Risultati</p>
            <p className="mt-1 text-2xl font-semibold text-gray-900">{response.total}</p>
          </div>
          <div className="rounded-2xl border border-emerald-100 bg-emerald-50 p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">Associati nella pagina</p>
            <p className="mt-1 text-2xl font-semibold text-emerald-800">{matchedCount}</p>
          </div>
          <div className="rounded-2xl border border-amber-100 bg-amber-50 p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-amber-700">Anomalie nella pagina</p>
            <p className="mt-1 text-2xl font-semibold text-amber-800">{anomalyCount}</p>
          </div>
        </div>

        {error ? (
          <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>
        ) : loading ? (
          <p className="text-sm text-gray-400">Caricamento raccomandate...</p>
        ) : response.items.length === 0 ? (
          <EmptyState icon={DocumentIcon} title="Nessuna raccomandata trovata" description="Modifica filtri o disattiva Solo anomalie." />
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 text-sm">
              <thead className="bg-gray-50 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
                <tr>
                  <th className="px-4 py-3">Destinatario</th>
                  <th className="px-4 py-3">Spedizione</th>
                  <th className="px-4 py-3">Matching</th>
                  <th className="px-4 py-3">Recupero</th>
                  <th className="px-4 py-3">Avviso</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {response.items.map((item) => (
                  <tr key={item.id} className={isAnomaly(item) ? "bg-amber-50/35" : undefined}>
                    <td className="max-w-[320px] px-4 py-3">
                      <p className="font-medium text-gray-900">{item.recipient_name ?? item.shipment_name ?? "Destinatario non letto"}</p>
                      <p className="mt-1 line-clamp-2 text-xs leading-5 text-gray-500">
                        {item.recipient_address ?? "-"} {item.recipient_city ? `· ${item.recipient_city}` : ""}
                      </p>
                    </td>
                    <td className="px-4 py-3 text-gray-600">
                      <p>{formatDate(item.sent_at)}</p>
                      <p className="mt-1 text-xs text-gray-500">Tracking {item.tracking_number ?? "-"}</p>
                      <p className="mt-1 text-xs text-gray-500">Invio {item.source_shipment_id}</p>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`rounded-full border px-2.5 py-1 text-xs font-semibold ${matchStatusClassName(item.match_status)}`}>
                        {matchStatusLabel(item.match_status)}
                      </span>
                      <p className="mt-2 text-xs leading-5 text-gray-500">
                        Score {item.match_score ?? "-"} · {item.match_reason ?? item.anomaly_key ?? "nessuna nota"}
                      </p>
                    </td>
                    <td className="px-4 py-3 text-gray-600">
                      <p>{recoveryStatusLabel(item.recovery_status)}</p>
                      <p className="mt-1 text-xs text-gray-500">{formatMoney(item.price_amount)}</p>
                    </td>
                    <td className="px-4 py-3">
                      {item.avviso_id ? (
                        <Link className="font-semibold text-[#1D4E35] hover:underline" href={`/ruolo/tributi?avviso=${item.avviso_id}`}>
                          Apri avviso
                        </Link>
                      ) : (
                        <span className="text-sm text-gray-400">Non associato</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-[#edf1eb] pt-4">
          <p className="text-xs text-gray-500">
            Pagina {response.page} · {response.items.length} elementi mostrati su {response.total}
          </p>
          <div className="flex gap-2">
            <button className="btn-secondary" disabled={!canGoBack || loading} onClick={() => goToPage(page - 1)} type="button">
              Raccomandate precedente
            </button>
            <button className="btn-secondary" disabled={!canGoForward || loading} onClick={() => goToPage(page + 1)} type="button">
              Raccomandate successiva
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}
