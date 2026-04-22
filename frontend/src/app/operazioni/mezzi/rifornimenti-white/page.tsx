"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import {
  OperazioniCollectionHero,
  OperazioniCollectionPanel,
  OperazioniHeroNotice,
  OperazioniMetricStrip,
  OperazioniToolbar,
} from "@/components/operazioni/collection-layout";
import { OperazioniModulePage } from "@/components/operazioni/operazioni-module-page";
import { EmptyState } from "@/components/ui/empty-state";
import { DocumentIcon, RefreshIcon, TruckIcon } from "@/components/ui/icons";
import { MetricCard } from "@/components/ui/metric-card";
import { getWhiteRefuelEvents } from "@/features/operazioni/api/client";

type WhiteRefuelEventItem = {
  id: string;
  wc_id: number;
  vehicle_id: string | null;
  wc_operator_id: string | null;
  matched_fuel_log_id: string | null;
  matched_fuel_card_id: string | null;
  vehicle_code: string | null;
  operator_name: string | null;
  fueled_at: string;
  odometer_km: string | null;
  source_issue: string | null;
  matched_at: string | null;
  wc_synced_at: string | null;
  created_at: string;
  updated_at: string;
  vehicle_display_name: string | null;
  operator_display_name: string | null;
  fuel_card_code: string | null;
};

function formatDateTime(value: string | null): string {
  if (!value) return "—";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString("it-IT", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatOdometer(value: string | null): string {
  if (!value) return "—";
  const parsed = Number(value);
  if (Number.isNaN(parsed)) return value;
  return `${parsed.toLocaleString("it-IT")} km`;
}

function statusLabel(item: WhiteRefuelEventItem): string {
  return item.matched_fuel_log_id ? "Riconciliato" : "Da riconciliare";
}

function statusTone(item: WhiteRefuelEventItem): string {
  return item.matched_fuel_log_id
    ? "bg-emerald-50 text-emerald-700"
    : "bg-amber-50 text-amber-700";
}

function eventTitle(item: WhiteRefuelEventItem): string {
  const vehicle = item.vehicle_display_name || item.vehicle_code || "Mezzo non risolto";
  const operator = item.operator_display_name || item.operator_name || "Operatore non risolto";
  return `${vehicle} · ${operator}`;
}

function hasOdometerAnomaly(item: WhiteRefuelEventItem): boolean {
  return Boolean(item.source_issue && item.source_issue.includes("ANOMALIA_KM"));
}

function renderEventMeta(item: WhiteRefuelEventItem): React.ReactNode {
  const anomaly = hasOdometerAnomaly(item);
  const odometerText =
    anomaly && (item.odometer_km === "0" || item.odometer_km === "0.000") ? "0000 km" : formatOdometer(item.odometer_km);

  const parts: Array<React.ReactNode> = [
    <span key="wc">{`White #${item.wc_id}`}</span>,
    <span key="dt">{formatDateTime(item.fueled_at)}</span>,
    <span key="odo" title={anomaly ? item.source_issue ?? undefined : undefined} className={anomaly ? "underline decoration-dotted underline-offset-2" : undefined}>
      {odometerText}
    </span>,
    item.fuel_card_code ? <span key="card">{`Carta ${item.fuel_card_code}`}</span> : null,
  ].filter(Boolean);

  return parts.map((part, idx) => (
    <span key={idx}>
      {idx > 0 ? " · " : null}
      {part}
    </span>
  ));
}

function WhiteRefuelEventCard({ item }: { item: WhiteRefuelEventItem }) {
  return (
    <div className="rounded-[24px] border border-[#e6ebe5] bg-[linear-gradient(180deg,_#ffffff,_#fbfcfa)] px-4 py-4 shadow-panel">
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className="inline-flex rounded-full border border-[#d5e2d8] bg-[#edf5f0] px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-[#1D4E35]">
              WhiteCompany
            </span>
            <span className={`inline-flex rounded-full px-2.5 py-1 text-[11px] font-semibold ${statusTone(item)}`}>
              {statusLabel(item)}
            </span>
          </div>
          <p className="mt-3 text-sm font-semibold text-gray-900">{eventTitle(item)}</p>
          <p className="mt-1 text-xs leading-5 text-gray-500">{renderEventMeta(item)}</p>
        </div>
        <div className="rounded-2xl border border-[#e4e8e2] bg-white px-3 py-2 text-right">
          <p className="text-[11px] uppercase tracking-[0.18em] text-gray-500">Sync White</p>
          <p className="mt-1 text-sm font-semibold text-gray-900">{formatDateTime(item.wc_synced_at)}</p>
        </div>
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-3">
        <div className="rounded-2xl border border-[#e4e8e2] bg-white px-3 py-3">
          <p className="text-[11px] uppercase tracking-[0.18em] text-gray-500">Operatore White</p>
          <p className="mt-1 text-sm font-medium text-gray-900">{item.operator_display_name || item.operator_name || "—"}</p>
        </div>
        <div className="rounded-2xl border border-[#e4e8e2] bg-white px-3 py-3">
          <p className="text-[11px] uppercase tracking-[0.18em] text-gray-500">Carta matchata</p>
          <p className="mt-1 text-sm font-medium text-gray-900">{item.fuel_card_code || "Da Excel transazioni flotte"}</p>
        </div>
        <div className="rounded-2xl border border-[#e4e8e2] bg-white px-3 py-3">
          <p className="text-[11px] uppercase tracking-[0.18em] text-gray-500">Fuel log GAIA</p>
          <p className="mt-1 text-sm font-medium text-gray-900">{item.matched_fuel_log_id ? `Creato ${formatDateTime(item.matched_at)}` : "Non ancora creato"}</p>
        </div>
      </div>

      {item.source_issue ? (
        <div className="mt-4 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
          {item.source_issue}
        </div>
      ) : null}
    </div>
  );
}

function WhiteRefuelsContent() {
  const [items, setItems] = useState<WhiteRefuelEventItem[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [matchedFilter, setMatchedFilter] = useState("false");

  const loadData = useCallback(async () => {
    setIsLoading(true);
    try {
      const params: Record<string, string> = { page_size: "50", matched: matchedFilter };
      if (search.trim()) {
        params.search = search.trim();
      }
      const data = await getWhiteRefuelEvents(params);
      setItems(data.items ?? []);
      setTotal(data.total ?? 0);
      setLoadError(null);
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : "Errore nel caricamento eventi White");
    } finally {
      setIsLoading(false);
    }
  }, [matchedFilter, search]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  const metrics = useMemo(() => {
    const matched = items.filter((item) => Boolean(item.matched_fuel_log_id)).length;
    const unmatched = items.length - matched;
    const withCard = items.filter((item) => Boolean(item.fuel_card_code)).length;
    const withIssue = items.filter((item) => Boolean(item.source_issue)).length;
    return { matched, unmatched, withCard, withIssue };
  }, [items]);

  return (
    <div className="page-stack">
      <OperazioniCollectionHero
        eyebrow="WhiteCompany refuels"
        icon={<DocumentIcon className="h-3.5 w-3.5" />}
        title="Eventi rifornimento WhiteCompany per verificare cosa è già riconciliato con l’import Excel Q8."
        description="La vista mostra gli eventi operativi recuperati dal registro rifornimenti White, compresi quelli che non hanno ancora generato un fuel log GAIA. Il match finale passa da carta carburante, cronologia assegnazioni e transazioni flotte."
      >
        {loadError ? (
          <OperazioniHeroNotice title="Caricamento non riuscito" description={loadError} tone="danger" />
        ) : (
          <OperazioniHeroNotice
            title="Filtro corrente"
            description={
              matchedFilter === "true"
                ? "Stai guardando solo gli eventi già riconciliati con un fuel log GAIA."
                : "Stai guardando gli eventi ancora da riconciliare con l’import Excel delle transazioni flotte."
            }
          />
        )}
        <div className="rounded-2xl border border-white/80 bg-white/75 px-4 py-3">
          <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-gray-500">Azioni</p>
          <div className="mt-3 flex flex-wrap gap-3">
            <button className="btn-secondary inline-flex items-center gap-2" type="button" onClick={() => void loadData()}>
              <RefreshIcon className="h-4 w-4" />
              Aggiorna elenco
            </button>
            <Link href="/operazioni/mezzi" className="btn-secondary">
              Torna ai mezzi
            </Link>
          </div>
        </div>
      </OperazioniCollectionHero>

      <OperazioniMetricStrip>
        <MetricCard label="Eventi mostrati" value={total} sub="Dataset filtrato corrente" />
        <MetricCard label="Da riconciliare" value={metrics.unmatched} sub="Senza fuel log GAIA" variant="warning" />
        <MetricCard label="Con carta risolta" value={metrics.withCard} sub="Match via fuel_card.codice" variant="info" />
        <MetricCard label="Con note provider" value={metrics.withIssue} sub="Dettagli economici assenti da White" />
      </OperazioniMetricStrip>

      <OperazioniCollectionPanel
        title="Registro eventi WhiteCompany"
        description="Ricerca per mezzo, operatore o id White. Il filtro stato separa gli eventi ancora da processare da quelli già riconciliati."
        count={items.length}
      >
        <OperazioniToolbar
          search={search}
          onSearchChange={setSearch}
          searchPlaceholder="Cerca per mezzo, operatore o id White"
          filterValue={matchedFilter}
          onFilterChange={setMatchedFilter}
          filterOptions={[
            { value: "false", label: "Da riconciliare" },
            { value: "true", label: "Già riconciliati" },
          ]}
        />

        <div className="mt-4">
          {isLoading ? (
            <p className="text-sm text-gray-500">Caricamento eventi White in corso.</p>
          ) : items.length === 0 ? (
            <EmptyState
              icon={TruckIcon}
              title="Nessun evento trovato"
              description="Non risultano eventi WhiteCompany con i filtri correnti."
            />
          ) : (
            <div className="space-y-3">
              {items.map((item) => (
                <WhiteRefuelEventCard key={item.id} item={item} />
              ))}
            </div>
          )}
        </div>
      </OperazioniCollectionPanel>
    </div>
  );
}

export default function WhiteRefuelsPage() {
  return (
    <OperazioniModulePage
      title="Eventi rifornimenti White"
      description="Staging operativo degli eventi rifornimento WhiteCompany da riconciliare con le transazioni flotte."
      breadcrumb="Mezzi"
    >
      {() => <WhiteRefuelsContent />}
    </OperazioniModulePage>
  );
}
