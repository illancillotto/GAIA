"use client";

import { useEffect, useState } from "react";

import { AlertBanner } from "@/components/ui/alert-banner";
import { MetricCard } from "@/components/ui/metric-card";
import {
  catastoGetMeterReading,
  catastoListDistretti,
  catastoListMeterReadingImports,
  catastoListMeterReadings,
} from "@/lib/api/catasto";
import { getStoredAccessToken } from "@/lib/auth";
import { cn } from "@/lib/cn";
import type { CatDistretto, CatMeterReading, CatMeterReadingListResponse } from "@/types/catasto";

import { MeterReadingDetailDrawer } from "./meter-reading-detail-drawer";

const QUICK_FILTERS = [
  { id: "all", label: "Tutte", description: "Registro completo" },
  { id: "warnings", label: "Con warning", description: "Da verificare" },
  { id: "interventi", label: "Interventi aperti", description: "Azioni operative" },
  { id: "excel", label: "Solo Excel", description: "Origine import" },
] as const;

type QuickFilterId = (typeof QUICK_FILTERS)[number]["id"];

const OPERATIONAL_FILTERS = [
  { id: "all", label: "Tutte" },
  { id: "unlinked", label: "Non collegati" },
  { id: "activities", label: "Attività operatore" },
  { id: "dismissed", label: "Punti dismessi" },
  { id: "lowBattery", label: "Batterie basse" },
] as const;

type OperationalFilterId = (typeof OPERATIONAL_FILTERS)[number]["id"];

const RECORD_TABS = [
  { id: "meter", label: "Letture contatore", description: "Solo letture reali di contatore" },
  { id: "other", label: "Attivita e censimenti", description: "Attivita operatore, punti dismessi e altro censimento" },
] as const;

type RecordTabId = (typeof RECORD_TABS)[number]["id"];

function formatRecordType(value: string | null, fallback: string | null): string {
  const normalized = value?.trim().toUpperCase();
  if (normalized === "CHIUSURA_IDRANTE") return "Chiusura idrante";
  if (normalized === "PREDISPOSIZIONE") return "Predisposizione";
  if (normalized === "CONT_NO_TES") return "Lettura contatore";
  if (normalized === "CONT_TESSER") return "Contatore tessera";
  if (normalized === "DIRAMATORE") return "Diramatore";
  if (normalized === "IDROVALVOLA") return "Idrovalvola";
  if (normalized === "SARACINESCA") return "Saracinesca";
  if (normalized === "DISMESSO") return "Dismesso";
  return value ?? fallback ?? "—";
}

function formatValidationStatus(value: string): string {
  if (value === "warning") return "Warning";
  if (value === "error") return "Errore";
  return "Valida";
}

function formatRecordKind(value: string | null): string {
  if (value === "meter_reading") return "Lettura";
  if (value === "operator_activity") return "Attività";
  if (value === "dismissed_point") return "Punto dismesso";
  return "—";
}

function formatOperationalState(value: string | null): string {
  if (value === "active") return "Attivo";
  if (value === "inactive") return "Inutilizzato";
  if (value === "dismissed_point") return "Dismesso";
  if (value === "activity") return "Attività";
  return "—";
}

function formatDecimal(value: string | null): string {
  if (!value) return "—";
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return value;
  return new Intl.NumberFormat("it-IT", { maximumFractionDigits: 0 }).format(numeric);
}

function countWarnings(item: CatMeterReading): number {
  return item.validation_messages.filter((message) => message.level === "warning").length;
}

function hasMessageCode(item: CatMeterReading, code: string): boolean {
  return item.validation_messages.some((message) => message.code === code);
}

export function MeterReadingsTable({ subjectId }: { subjectId?: string }) {
  const [data, setData] = useState<CatMeterReadingListResponse | null>(null);
  const [distretti, setDistretti] = useState<CatDistretto[]>([]);
  const [anno, setAnno] = useState("");
  const [annoOptions, setAnnoOptions] = useState<number[]>([]);
  const [distrettoId, setDistrettoId] = useState("");
  const [puntoConsegna, setPuntoConsegna] = useState("");
  const [matricola, setMatricola] = useState("");
  const [codiceFiscale, setCodiceFiscale] = useState("");
  const [quickFilter, setQuickFilter] = useState<QuickFilterId>("all");
  const [operationalFilter, setOperationalFilter] = useState<OperationalFilterId>("all");
  const [recordTab, setRecordTab] = useState<RecordTabId>("meter");
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [isInitializing, setIsInitializing] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [detail, setDetail] = useState<CatMeterReading | null>(null);

  useEffect(() => {
    async function initializeFilters() {
      const token = getStoredAccessToken();
      if (!token) return;

      try {
        setIsInitializing(true);
        setError(null);

        const currentYear = new Date().getFullYear();
        const [imports, currentYearResult, distrettiResult] = await Promise.all([
          catastoListMeterReadingImports(token),
          catastoListMeterReadings(token, { anno: currentYear, pageSize: 1 }),
          catastoListDistretti(token),
        ]);

        const importedYears = Array.from(new Set(imports.map((item) => item.anno))).sort((left, right) => right - left);
        const selectedYear = currentYearResult.total > 0 ? currentYear : importedYears[0] ?? currentYear;
        const nextOptions = importedYears.includes(selectedYear)
          ? importedYears
          : [selectedYear, ...importedYears].sort((left, right) => right - left);

        setAnnoOptions(nextOptions);
        setAnno(String(selectedYear));
        setDistretti(distrettiResult);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Inizializzazione filtri fallita");
        const fallbackYear = new Date().getFullYear();
        setAnnoOptions([fallbackYear]);
        setAnno(String(fallbackYear));
      } finally {
        setIsInitializing(false);
      }
    }

    void initializeFilters();
  }, []);

  useEffect(() => {
    setPage(1);
  }, [anno, distrettoId, puntoConsegna, matricola, codiceFiscale, quickFilter, recordTab, subjectId]);

  useEffect(() => {
    if (!anno) return;

    async function loadReadings() {
      const token = getStoredAccessToken();
      if (!token) return;

      try {
        setLoading(true);
        setError(null);
        const result = await catastoListMeterReadings(token, {
          anno: Number(anno),
          distrettoId: distrettoId || undefined,
          puntoConsegna: puntoConsegna || undefined,
          matricola: matricola || undefined,
          codiceFiscale: codiceFiscale || undefined,
          subjectId: subjectId || undefined,
          hasWarnings: quickFilter === "warnings",
          interventoDaEseguire: quickFilter === "interventi",
          source: quickFilter === "excel" ? "excel" : undefined,
          page,
          pageSize: subjectId ? 200 : 100,
        });
        setData(result);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Caricamento letture fallito");
      } finally {
        setLoading(false);
      }
    }

    void loadReadings();
  }, [anno, distrettoId, puntoConsegna, matricola, codiceFiscale, quickFilter, page, subjectId]);

  async function refreshReadings() {
    if (!anno) return;
    const token = getStoredAccessToken();
    if (!token) return;
    const result = await catastoListMeterReadings(token, {
      anno: Number(anno),
      distrettoId: distrettoId || undefined,
      puntoConsegna: puntoConsegna || undefined,
      matricola: matricola || undefined,
      codiceFiscale: codiceFiscale || undefined,
      subjectId: subjectId || undefined,
      hasWarnings: quickFilter === "warnings",
      interventoDaEseguire: quickFilter === "interventi",
      source: quickFilter === "excel" ? "excel" : undefined,
      page,
      pageSize: subjectId ? 200 : 100,
    });
    setData(result);
  }

  async function openDetail(id: string) {
    const token = getStoredAccessToken();
    if (!token) return;
    try {
      setDetail(await catastoGetMeterReading(token, id));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Dettaglio lettura non disponibile");
    }
  }

  function resetFilters() {
    setDistrettoId("");
    setPuntoConsegna("");
    setMatricola("");
    setCodiceFiscale("");
    setQuickFilter("all");
    setOperationalFilter("all");
    setRecordTab("meter");
  }

  const items = data?.items ?? [];
  const tabItems = items.filter((item) => {
    if (recordTab === "meter" && item.record_kind !== "meter_reading") return false;
    if (recordTab === "other" && item.record_kind === "meter_reading") return false;
    return true;
  });
  const filteredItems = tabItems.filter((item) => {
    if (operationalFilter === "unlinked") return !item.subject_id;
    if (operationalFilter === "activities") return item.record_kind === "operator_activity";
    if (operationalFilter === "dismissed") return item.record_kind === "dismissed_point";
    if (operationalFilter === "lowBattery") return hasMessageCode(item, "BATTERIA_BASSA");
    return true;
  });
  const sortedItems = [...filteredItems].sort((left, right) => {
    const leftRank = left.record_kind === "meter_reading" ? 0 : 1;
    const rightRank = right.record_kind === "meter_reading" ? 0 : 1;
    if (leftRank !== rightRank) return leftRank - rightRank;
    return left.punto_consegna.localeCompare(right.punto_consegna, "it");
  });
  const linkedCount = filteredItems.filter((item) => Boolean(item.subject_id)).length;
  const warningCount = filteredItems.filter((item) => item.validation_status === "warning").length;
  const meterCount = filteredItems.filter((item) => item.record_kind === "meter_reading").length;
  const activityCount = filteredItems.filter((item) => item.record_kind === "operator_activity").length;
  const dismissedCount = filteredItems.filter((item) => item.record_kind === "dismissed_point").length;
  const totalMeterCount = items.filter((item) => item.record_kind === "meter_reading").length;
  const totalOtherCount = items.filter((item) => item.record_kind !== "meter_reading").length;
  const operationalCounts = {
    unlinked: tabItems.filter((item) => !item.subject_id).length,
    activities: tabItems.filter((item) => item.record_kind === "operator_activity").length,
    dismissed: tabItems.filter((item) => item.record_kind === "dismissed_point").length,
    lowBattery: tabItems.filter((item) => hasMessageCode(item, "BATTERIA_BASSA")).length,
  };
  const totalPages = data ? Math.max(1, Math.ceil(data.total / Math.max(data.page_size, 1))) : 1;
  const hasActiveFilters = Boolean(
    distrettoId ||
      puntoConsegna.trim() ||
      matricola.trim() ||
      codiceFiscale.trim() ||
      quickFilter !== "all" ||
      operationalFilter !== "all" ||
      recordTab !== "meter",
  );
  const tabOperationalFilters =
    recordTab === "meter"
      ? OPERATIONAL_FILTERS.filter((filter) => filter.id === "all" || filter.id === "unlinked" || filter.id === "lowBattery")
      : OPERATIONAL_FILTERS.filter((filter) => filter.id === "all" || filter.id === "unlinked" || filter.id === "activities" || filter.id === "dismissed");
  const tabTitle = recordTab === "meter" ? "Registro letture contatori" : "Registro attivita e censimenti";
  const tabDescription =
    recordTab === "meter"
      ? "Vista dedicata alle letture vere, con consumo, matricola e anomalie del contatore."
      : "Vista dedicata a predisposizioni, diramatori, punti dismessi e altre righe non assimilabili a una lettura contatore.";
  const tableLastColumnTitle = recordTab === "meter" ? "Lettura" : "Contesto operativo";

  return (
    <div className="space-y-5">
      {!subjectId ? (
        <section className="rounded-[2rem] border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="section-title">Console operativa letture</p>
              <p className="section-copy">
                Ricerca veloce con separazione netta tra letture contatore e resto del censimento.
              </p>
            </div>
            {hasActiveFilters ? (
              <button className="btn-secondary" onClick={resetFilters} type="button">
                Pulisci filtri
              </button>
            ) : null}
          </div>

          <div className="mt-5 space-y-3">
            <div className="rounded-[1.5rem] border border-slate-200 bg-slate-50/70 p-4">
              <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                <label className="block text-sm font-medium text-slate-700">
                  Anno
                  <select
                    className="form-control mt-1"
                    value={anno}
                    onChange={(event) => setAnno(event.target.value)}
                    disabled={isInitializing}
                  >
                    {annoOptions.map((option) => (
                      <option key={option} value={option}>
                        {option}
                      </option>
                    ))}
                  </select>
                </label>

                <label className="block text-sm font-medium text-slate-700">
                  Distretto
                  <select className="form-control mt-1" value={distrettoId} onChange={(event) => setDistrettoId(event.target.value)}>
                    <option value="">Tutti i distretti</option>
                    {distretti.map((distretto) => (
                      <option key={distretto.id} value={distretto.id}>
                        {distretto.num_distretto} · {distretto.nome_distretto}
                      </option>
                    ))}
                  </select>
                </label>

                <label className="block text-sm font-medium text-slate-700">
                  Punto consegna
                  <input
                    className="form-control mt-1"
                    placeholder="Es. C_A-18_1"
                    value={puntoConsegna}
                    onChange={(event) => setPuntoConsegna(event.target.value)}
                  />
                </label>

                <label className="block text-sm font-medium text-slate-700">
                  Matricola
                  <input
                    className="form-control mt-1"
                    placeholder="Es. 570"
                    value={matricola}
                    onChange={(event) => setMatricola(event.target.value)}
                  />
                </label>
              </div>

              <div className="mt-3 grid gap-3 md:grid-cols-[minmax(0,1fr)_260px]">
                <label className="block text-sm font-medium text-slate-700">
                  Codice fiscale / soggetto
                  <input
                    className="form-control mt-1"
                    placeholder="CF o frammento da cercare"
                    value={codiceFiscale}
                    onChange={(event) => setCodiceFiscale(event.target.value)}
                  />
                </label>

                <div className="rounded-[1.25rem] border border-slate-200 bg-white px-4 py-3">
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Filtro rapido attivo</p>
                  <p className="mt-2 text-sm font-semibold text-slate-900">
                    {QUICK_FILTERS.find((filter) => filter.id === quickFilter)?.label ?? "Tutte"}
                  </p>
                  <p className="mt-1 text-xs text-slate-500">
                    {QUICK_FILTERS.find((filter) => filter.id === quickFilter)?.description ?? "Registro completo"}
                  </p>
                </div>
              </div>
            </div>

            <div className="rounded-[1.5rem] border border-emerald-100 bg-[#f5faf7] p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">Filtri rapidi</p>
              <div className="mt-3 grid gap-2 md:grid-cols-2 xl:grid-cols-4">
                {QUICK_FILTERS.map((filter) => (
                  <button
                    key={filter.id}
                    type="button"
                    onClick={() => setQuickFilter(filter.id)}
                    className={cn(
                      "rounded-2xl border px-4 py-3 text-left transition",
                      quickFilter === filter.id
                        ? "border-emerald-300 bg-white shadow-sm"
                        : "border-emerald-100 bg-transparent hover:border-emerald-200 hover:bg-white/80",
                    )}
                  >
                    <p className="text-sm font-semibold text-slate-900">{filter.label}</p>
                    <p className="mt-1 text-xs text-slate-600">{filter.description}</p>
                  </button>
                ))}
              </div>
            </div>
          </div>
        </section>
      ) : null}

      {error ? (
        <AlertBanner variant="danger" title="Errore caricamento">
          {error}
        </AlertBanner>
      ) : null}

      <section className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          label={subjectId ? "Righe soggetto" : recordTab === "meter" ? "Letture in vista" : "Righe operative"}
          value={loading || isInitializing ? "…" : filteredItems.length}
          sub={subjectId ? "Filtro sul soggetto corrente" : `Pagina ${data?.page ?? page} di ${totalPages} · ${data?.total ?? 0} server`}
          variant="default"
        />
        <MetricCard
          label="Con warning"
          value={loading ? "…" : warningCount}
          sub="Nella pagina corrente"
          variant="warning"
        />
        <MetricCard
          label={recordTab === "meter" ? "Soggetti collegati" : "Non collegati"}
          value={loading ? "…" : recordTab === "meter" ? linkedCount : filteredItems.length - linkedCount}
          sub={recordTab === "meter" ? "Link anagrafico presente" : "Da classificare o agganciare"}
          variant={recordTab === "meter" ? "success" : "warning"}
        />
        <MetricCard
          label={recordTab === "meter" ? "Letture / Batterie basse" : "Attivita / Dismessi"}
          value={loading ? "…" : recordTab === "meter" ? `${meterCount} / ${operationalCounts.lowBattery}` : `${activityCount} / ${dismissedCount}`}
          sub={recordTab === "meter" ? "Volume operativo pagina corrente" : "Ripartizione pagina corrente"}
          variant="info"
        />
      </section>

      <div className="overflow-hidden rounded-[2rem] border border-slate-200 bg-white shadow-sm">
        <div className="border-b border-slate-200 px-5 py-4">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="section-title">{subjectId ? "Letture collegate al soggetto" : tabTitle}</p>
              <p className="section-copy">
                {isInitializing || loading ? "Caricamento in corso…" : tabDescription}
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              {hasActiveFilters ? (
                <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-700">Filtri attivi</span>
              ) : null}
              {quickFilter !== "all" ? (
                <span className="rounded-full bg-emerald-100 px-3 py-1 text-xs font-medium text-emerald-800">
                  {QUICK_FILTERS.find((filter) => filter.id === quickFilter)?.label}
                </span>
              ) : null}
            </div>
          </div>
          {!subjectId ? (
            <div className="mt-4 grid gap-2 lg:grid-cols-3">
              {RECORD_TABS.map((tab) => {
                const count = tab.id === "meter" ? totalMeterCount : totalOtherCount;
                return (
                  <button
                    key={tab.id}
                    type="button"
                    onClick={() => {
                      setRecordTab(tab.id);
                      setOperationalFilter("all");
                    }}
                    className={cn(
                      "rounded-2xl border px-4 py-3 text-left transition",
                      recordTab === tab.id
                        ? tab.id === "meter"
                          ? "border-emerald-300 bg-emerald-50"
                          : "border-amber-300 bg-amber-50"
                        : "border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50",
                    )}
                  >
                    <p className="text-sm font-semibold text-slate-900">{tab.label}</p>
                    <p className="mt-1 text-xs text-slate-500">{tab.description}</p>
                    <p className="mt-2 text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">{count} righe in pagina</p>
                  </button>
                );
              })}
            </div>
          ) : null}
          {!subjectId ? (
            <div className="mt-4 flex flex-wrap gap-2">
              {tabOperationalFilters.map((filter) => {
                const count =
                  filter.id === "all"
                    ? tabItems.length
                    : operationalCounts[filter.id as Exclude<OperationalFilterId, "all">];
                return (
                  <button
                    key={filter.id}
                    type="button"
                    onClick={() => setOperationalFilter(filter.id)}
                    className={cn(
                      "rounded-full border px-3 py-1.5 text-xs font-semibold transition",
                      operationalFilter === filter.id
                        ? "border-slate-900 bg-slate-900 text-white"
                        : "border-slate-200 bg-white text-slate-700 hover:border-slate-300 hover:bg-slate-50",
                    )}
                  >
                    {filter.label} · {count}
                  </button>
                );
              })}
            </div>
          ) : null}
        </div>

        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="sticky top-0 z-10 bg-slate-50 text-left text-slate-600">
              <tr>
                <th className="px-4 py-3 font-medium">Punto / contatore</th>
                <th className="px-4 py-3 font-medium">Soggetto</th>
                <th className="px-4 py-3 font-medium">Classe</th>
                <th className="px-4 py-3 font-medium">Consumo</th>
                <th className="px-4 py-3 font-medium">Stato</th>
                <th className="px-4 py-3 font-medium">{tableLastColumnTitle}</th>
              </tr>
            </thead>
            <tbody>
              {sortedItems.map((item) => {
                const warningBadgeCount = countWarnings(item);
                const isMeterReading = item.record_kind === "meter_reading";
                return (
                  <tr
                    key={item.id}
                    className={cn(
                      "cursor-pointer border-t align-top transition hover:bg-slate-50",
                      isMeterReading ? "border-slate-100" : "border-amber-100 bg-amber-50/35",
                    )}
                    onClick={() => void openDetail(item.id)}
                  >
                    <td className="px-4 py-3">
                      <div className="min-w-[220px]">
                        <div className="flex flex-wrap items-center gap-2">
                          <p className="font-semibold text-slate-950">{item.punto_consegna}</p>
                          <span
                            className={cn(
                              "rounded-full px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.14em]",
                              isMeterReading ? "bg-emerald-100 text-emerald-800" : "bg-amber-100 text-amber-800",
                            )}
                          >
                            {isMeterReading ? "Contatore" : "Censimento"}
                          </span>
                        </div>
                        <div className="mt-1 flex flex-wrap gap-2 text-xs text-slate-500">
                          <span>Anno {item.anno}</span>
                          <span>•</span>
                          <span>Matr. {item.matricola ?? "—"}</span>
                          {item.sigillo ? (
                            <>
                              <span>•</span>
                              <span>Sigillo {item.sigillo}</span>
                            </>
                          ) : null}
                        </div>
                        {item.tipologia_idrante ? <p className="mt-2 text-xs text-slate-500">{item.tipologia_idrante}</p> : null}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="min-w-[220px]">
                        <p className="font-medium text-slate-900">{item.subject_display_name ?? "Non collegato"}</p>
                        <p className="mt-1 text-xs text-slate-500">{item.codice_fiscale_normalizzato ?? item.codice_fiscale ?? "CF assente"}</p>
                        {item.dui ? <p className="mt-2 text-xs text-slate-500">DUI {item.dui}</p> : null}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex min-w-[190px] flex-wrap gap-2">
                        <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-700">
                          {formatRecordKind(item.record_kind)}
                        </span>
                        <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-700">
                          {formatRecordType(item.record_type, item.tipologia_idrante)}
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="min-w-[120px]">
                        {isMeterReading ? (
                          <>
                            <p className="font-semibold text-slate-900">{formatDecimal(item.consumo_mc)}</p>
                            <p className="mt-1 text-xs text-slate-500">
                              {formatDecimal(item.lettura_iniziale)} → {formatDecimal(item.lettura_finale)}
                            </p>
                          </>
                        ) : (
                          <>
                            <p className="font-semibold text-amber-900">Non applicabile</p>
                            <p className="mt-1 text-xs text-amber-700">Riga non riferita a lettura contatore</p>
                          </>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex min-w-[160px] flex-wrap gap-2">
                        <span
                          className={cn(
                            "rounded-full px-2.5 py-1 text-xs font-semibold",
                            item.validation_status === "warning"
                              ? "bg-amber-100 text-amber-800"
                              : item.validation_status === "error"
                                ? "bg-rose-100 text-rose-800"
                                : "bg-emerald-100 text-emerald-800",
                          )}
                        >
                          {formatValidationStatus(item.validation_status)}
                        </span>
                        <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-700">
                          {formatOperationalState(item.operational_state)}
                        </span>
                        {warningBadgeCount > 0 ? (
                          <span className="rounded-full bg-amber-50 px-2.5 py-1 text-xs font-semibold text-amber-700">
                            {warningBadgeCount} warning
                          </span>
                        ) : null}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="min-w-[170px]">
                        <p className="text-sm font-medium text-slate-900">{item.data_lettura ?? "Data non disponibile"}</p>
                        <p className="mt-1 text-xs text-slate-500">{item.operatore_lettura ?? "Operatore non indicato"}</p>
                        {item.intervento_da_eseguire ? (
                          <p className="mt-2 rounded-xl bg-amber-50 px-2 py-1 text-xs text-amber-800">
                            Intervento: {item.intervento_da_eseguire}
                          </p>
                        ) : null}
                      </div>
                    </td>
                  </tr>
                );
              })}

              {!loading && filteredItems.length === 0 ? (
                <tr>
                  <td className="px-4 py-8 text-center text-slate-500" colSpan={6}>
                    Nessuna lettura trovata con i filtri correnti.
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>

        {!subjectId && data ? (
          <div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-200 px-5 py-4">
            <p className="text-sm text-slate-500">
              Pagina {data.page} di {totalPages} · {data.total} righe totali
            </p>
            <div className="flex gap-2">
              <button className="btn-secondary" disabled={page <= 1 || loading} onClick={() => setPage((current) => Math.max(1, current - 1))} type="button">
                Precedente
              </button>
              <button
                className="btn-secondary"
                disabled={loading || page >= totalPages}
                onClick={() => setPage((current) => Math.min(totalPages, current + 1))}
                type="button"
              >
                Successiva
              </button>
            </div>
          </div>
        ) : null}
      </div>

      <MeterReadingDetailDrawer
        reading={detail}
        onClose={() => setDetail(null)}
        onUpdated={(reading) => {
          setDetail(reading);
          void refreshReadings();
        }}
      />
    </div>
  );
}
