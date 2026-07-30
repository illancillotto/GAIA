"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { CatastoPage } from "@/components/catasto/catasto-page";
import { EmptyState } from "@/components/ui/empty-state";
import { SearchIcon } from "@/components/ui/icons";
import {
  catastoGetDomandeIrrigueRuoloReconciliation,
  catastoGetDomandeIrrigueSummary,
  catastoListDomandeIrrigue,
} from "@/lib/api/catasto";
import { getStoredAccessToken } from "@/lib/auth";
import { formatDateTime } from "@/lib/presentation";
import type {
  CatDomandaIrrigua,
  CatDomandeIrrigueRuoloReconciliation,
  CatDomandeIrrigueSummary,
} from "@/types/catasto";

const PAGE_LIMIT = 50;

function parseYear(value: string): number | undefined {
  const parsed = Number(value);
  return Number.isInteger(parsed) && parsed > 1900 ? parsed : undefined;
}

function formatArea(value: string | null): string {
  if (!value) return "-";
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return value;
  return `${parsed.toLocaleString("it-IT", { maximumFractionDigits: 2 })} mq`;
}

function statusTone(status: string | null): string {
  const normalized = (status ?? "").toLowerCase();
  if (normalized.includes("apert") || normalized.includes("aggiornat")) return "bg-emerald-50 text-emerald-700 ring-emerald-200";
  if (normalized.includes("rettificat")) return "bg-amber-50 text-amber-700 ring-amber-200";
  if (normalized.includes("annull") || normalized.includes("chius")) return "bg-slate-50 text-slate-600 ring-slate-200";
  return "bg-sky-50 text-sky-700 ring-sky-200";
}

function issueLabel(issue: string | null): string {
  switch (issue) {
    case "coltura_mismatch":
      return "Coltura diversa";
    case "superficie_mismatch":
      return "Superficie diversa";
    case "domanda_non_trovata":
      return "Domanda assente";
    default:
      return "Allineata";
  }
}

export default function CatastoDomandeIrriguePage() {
  const [anno, setAnno] = useState("2026");
  const [search, setSearch] = useState("");
  const [stato, setStato] = useState("");
  const [summary, setSummary] = useState<CatDomandeIrrigueSummary | null>(null);
  const [items, setItems] = useState<CatDomandaIrrigua[]>([]);
  const [total, setTotal] = useState(0);
  const [reconciliation, setReconciliation] = useState<CatDomandeIrrigueRuoloReconciliation | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    const token = getStoredAccessToken();
    if (!token) {
      setError("Sessione non disponibile. Effettua nuovamente l'accesso.");
      return;
    }
    const parsedAnno = parseYear(anno);
    setBusy(true);
    setError(null);
    try {
      const [summaryPayload, listPayload, reconciliationPayload] = await Promise.all([
        catastoGetDomandeIrrigueSummary(token, { anno: parsedAnno }),
        catastoListDomandeIrrigue(token, {
          anno: parsedAnno,
          stato: stato.trim() || undefined,
          search: search.trim() || undefined,
          limit: PAGE_LIMIT,
          offset: 0,
        }),
        catastoGetDomandeIrrigueRuoloReconciliation(token, { anno: parsedAnno, limit: 25 }),
      ]);
      setSummary(summaryPayload);
      setItems(listPayload.items);
      setTotal(listPayload.total);
      setReconciliation(reconciliationPayload);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Errore caricamento domande irrigue.");
    } finally {
      setBusy(false);
    }
  }, [anno, search, stato]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <CatastoPage
      title="Domande irrigue"
      description="Consultazione delle domande irrigue importate da Capacitas e confronto con particelle a ruolo."
      breadcrumb="Catasto / Domande irrigue"
      requiredModule="catasto"
    >
      <div className="space-y-6">
        <section className="overflow-hidden rounded-[2rem] border border-emerald-100 bg-gradient-to-br from-[#F7FBF2] via-white to-[#EAF4F0] p-6 shadow-sm">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <p className="section-title text-emerald-700">Registro Capacitas</p>
              <h1 className="mt-2 text-3xl font-semibold tracking-tight text-slate-950">Domande irrigue importate</h1>
              <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
                La chiave operativa resta sempre CCO, COM, PVC, FRA e CCS. Il ruolo viene usato solo come controllo di
                riconciliazione, non come sorgente del lifecycle domanda.
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Link className="btn-secondary bg-white" href="/elaborazioni/capacitas">
                Apri job Capacitas
              </Link>
              <button className="btn-primary" disabled={busy} onClick={() => void load()} type="button">
                {busy ? "Aggiorno..." : "Aggiorna"}
              </button>
            </div>
          </div>

          <div className="mt-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-6">
            <KpiCard label="Domande" value={summary?.total_domande ?? 0} />
            <KpiCard label="Righe particella" value={summary?.total_particelle ?? 0} />
            <KpiCard label="Utenze linkate" value={summary?.linked_utenze ?? 0} />
            <KpiCard label="Particelle linkate" value={summary?.linked_particelle ?? 0} />
            <KpiCard label="Occupazioni" value={summary?.linked_occupancies ?? 0} />
            <KpiCard label="Anomalie aperte" value={summary?.open_anomalies ?? 0} tone="warning" />
          </div>
        </section>

        <section className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="grid gap-3 md:grid-cols-[160px_180px_1fr_auto] md:items-end">
            <label className="text-sm font-medium text-slate-700">
              Anno
              <input className="mt-1 w-full rounded-2xl border border-slate-200 px-3 py-2 text-sm" value={anno} onChange={(event) => setAnno(event.target.value)} />
            </label>
            <label className="text-sm font-medium text-slate-700">
              Stato
              <input className="mt-1 w-full rounded-2xl border border-slate-200 px-3 py-2 text-sm" placeholder="Aperta, Rettificata..." value={stato} onChange={(event) => setStato(event.target.value)} />
            </label>
            <label className="text-sm font-medium text-slate-700">
              Cerca
              <input className="mt-1 w-full rounded-2xl border border-slate-200 px-3 py-2 text-sm" placeholder="Domanda, CCO, comune o intestatario" value={search} onChange={(event) => setSearch(event.target.value)} />
            </label>
            <button className="btn-primary" disabled={busy} onClick={() => void load()} type="button">
              Filtra
            </button>
          </div>
          {error ? <p className="mt-3 rounded-2xl bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</p> : null}
        </section>

        <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_420px]">
          <section className="rounded-3xl border border-slate-200 bg-white shadow-sm">
            <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4">
              <div>
                <h2 className="text-lg font-semibold text-slate-950">Ultime domande</h2>
                <p className="text-sm text-slate-500">{total.toLocaleString("it-IT")} risultati, prime {PAGE_LIMIT} righe</p>
              </div>
            </div>
            {items.length === 0 ? (
              <div className="p-8">
                <EmptyState icon={SearchIcon} title="Nessuna domanda trovata" description="Modifica i filtri o avvia un job Capacitas domande irrigue." />
              </div>
            ) : (
              <div className="divide-y divide-slate-100">
                {items.map((item) => (
                  <article className="px-5 py-4" key={item.id}>
                    <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                      <div>
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="text-base font-semibold text-slate-950">Domanda {item.domanda_numero ?? "-"}</span>
                          <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ring-inset ${statusTone(item.stato)}`}>
                            {item.stato ?? "Stato ND"}
                          </span>
                          <span className="rounded-full bg-slate-50 px-2.5 py-1 text-xs font-medium text-slate-600 ring-1 ring-slate-200">
                            {item.anno}
                          </span>
                        </div>
                        <p className="mt-1 text-sm text-slate-600">{item.source_denominazione ?? item.comune ?? "Intestatario non disponibile"}</p>
                        <p className="mt-1 text-xs text-slate-400">
                          CCO {item.cco ?? "-"} - COM {item.com ?? "-"} - PVC {item.pvc ?? "-"} - FRA {item.fra ?? "-"} - CCS {item.ccs ?? "-"}
                        </p>
                      </div>
                      <div className="text-left text-sm lg:text-right">
                        <p className="font-medium text-slate-900">{formatArea(item.tot_sup_irr_mq)} irrigati</p>
                        <p className="text-slate-500">{formatDateTime(item.data_ins)}</p>
                      </div>
                    </div>
                    <div className="mt-3 flex flex-wrap gap-2">
                      {item.particelle.slice(0, 4).map((part) => (
                        <span className="rounded-2xl bg-slate-50 px-3 py-1.5 text-xs text-slate-600" key={part.id}>
                          Fg {part.foglio ?? "-"} / Part {part.particella ?? "-"} - {part.coltura ?? "Coltura ND"} - {formatArea(part.sup_irr_mq)}
                        </span>
                      ))}
                      {item.particelle.length > 4 ? (
                        <span className="rounded-2xl bg-slate-100 px-3 py-1.5 text-xs text-slate-500">
                          +{item.particelle.length - 4} righe
                        </span>
                      ) : null}
                    </div>
                  </article>
                ))}
              </div>
            )}
          </section>

          <aside className="space-y-6">
            <section className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
              <h2 className="text-lg font-semibold text-slate-950">Riconciliazione ruolo</h2>
              <div className="mt-4 grid grid-cols-2 gap-3">
                <KpiCard compact label="Righe ruolo" value={reconciliation?.total_ruolo_rows ?? 0} />
                <KpiCard compact label="Allineate" value={reconciliation?.matched_rows ?? 0} />
                <KpiCard compact label="Assenti" value={reconciliation?.missing_rows ?? 0} tone="warning" />
                <KpiCard compact label="Mismatch" value={(reconciliation?.crop_mismatch_rows ?? 0) + (reconciliation?.surface_mismatch_rows ?? 0)} tone="warning" />
              </div>
              <div className="mt-4 space-y-2">
                {(reconciliation?.items ?? []).slice(0, 8).map((item) => (
                  <div className="rounded-2xl border border-slate-100 bg-slate-50 px-3 py-2" key={item.ruolo_particella_id}>
                    <div className="flex items-center justify-between gap-3">
                      <span className="text-sm font-medium text-slate-800">Domanda {item.domanda_irrigua ?? "-"}</span>
                      <span className={item.issue ? "text-xs font-semibold text-amber-700" : "text-xs font-semibold text-emerald-700"}>
                        {issueLabel(item.issue)}
                      </span>
                    </div>
                    <p className="mt-1 text-xs text-slate-500">
                      Fg {item.foglio} / Part {item.particella} - ruolo {item.coltura_ruolo ?? "ND"} - Capacitas {item.coltura_domanda ?? "ND"}
                    </p>
                  </div>
                ))}
              </div>
            </section>

            <section className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
              <h2 className="text-lg font-semibold text-slate-950">Distribuzione</h2>
              <div className="mt-4 space-y-3">
                {(summary?.by_stato ?? []).slice(0, 6).map((bucket) => (
                  <div key={bucket.key}>
                    <div className="flex justify-between text-sm">
                      <span className="text-slate-600">{bucket.key}</span>
                      <span className="font-medium text-slate-900">{bucket.count.toLocaleString("it-IT")}</span>
                    </div>
                    <div className="mt-1 h-2 overflow-hidden rounded-full bg-slate-100">
                      <div
                        className="h-full rounded-full bg-emerald-500"
                        style={{ width: `${summary && summary.total_domande > 0 ? Math.max(5, (bucket.count / summary.total_domande) * 100) : 0}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </section>
          </aside>
        </div>
      </div>
    </CatastoPage>
  );
}

function KpiCard({
  label,
  value,
  tone = "default",
  compact = false,
}: {
  label: string;
  value: number;
  tone?: "default" | "warning";
  compact?: boolean;
}) {
  const toneClass = tone === "warning" ? "border-amber-100 bg-amber-50 text-amber-800" : "border-white/70 bg-white/80 text-slate-900";
  return (
    <div className={`rounded-3xl border ${toneClass} ${compact ? "p-3" : "p-4"} shadow-sm`}>
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</p>
      <p className={`${compact ? "text-xl" : "text-2xl"} mt-1 font-semibold`}>{value.toLocaleString("it-IT")}</p>
    </div>
  );
}
