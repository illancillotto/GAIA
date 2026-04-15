"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import {
  OperazioniCollectionHero,
  OperazioniCollectionPanel,
  OperazioniHeroNotice,
  OperazioniMetricStrip,
  OperazioniToolbar,
} from "@/components/operazioni/collection-layout";
import { FuelCardsUnmatchedWizard } from "@/components/operazioni/fuel-cards-unmatched-wizard";
import { ImportFuelCardsModal } from "@/components/operazioni/import-fuel-cards-modal";
import { OperazioniModulePage } from "@/components/operazioni/operazioni-module-page";
import { EmptyState } from "@/components/ui/empty-state";
import { DocumentIcon, RefreshIcon } from "@/components/ui/icons";
import { MetricCard } from "@/components/ui/metric-card";
import { cn } from "@/lib/cn";
import { getFuelCards, getOperators } from "@/features/operazioni/api/client";

type FuelCardItem = {
  id: string;
  codice: string | null;
  driver: string | null;
  sigla: string | null;
  is_blocked: boolean;
  pan: string;
  card_number_emissione: string | null;
  expires_at: string | null;
  prodotti: string | null;
  cod: string | null;
  current_wc_operator_id: string | null;
};

type OperatorItem = {
  id: string;
  first_name: string | null;
  last_name: string | null;
  email: string | null;
  username: string | null;
  role: string | null;
  enabled: boolean;
};

function normalizeSearch(value: string): string {
  return value.trim();
}

function formatDate(value: string | null): string {
  if (!value) return "—";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleDateString("it-IT");
}

function statusTone(card: FuelCardItem): string {
  if (card.is_blocked) return "bg-rose-50 text-rose-700";
  if (!card.current_wc_operator_id) return "bg-amber-50 text-amber-700";
  return "bg-emerald-50 text-emerald-700";
}

function statusLabel(card: FuelCardItem): string {
  if (card.is_blocked) return "Bloccata";
  if (!card.current_wc_operator_id) return "Non assegnata";
  return "Assegnata";
}

function operatorLabel(operator: OperatorItem | undefined): string {
  if (!operator) return "—";
  const name = `${operator.last_name ?? ""} ${operator.first_name ?? ""}`.trim();
  return name || operator.email || operator.username || "Operatore";
}

function initialsForPan(pan: string): string {
  const normalized = pan.replaceAll(" ", "").trim();
  if (normalized.length <= 4) {
    return normalized.toUpperCase();
  }
  return `${normalized.slice(0, 2)}${normalized.slice(-2)}`.toUpperCase();
}

function cardVisualTone(card: FuelCardItem): string {
  if (card.is_blocked) return "from-rose-50 via-white to-white";
  if (!card.current_wc_operator_id) return "from-amber-50 via-white to-white";
  return "from-emerald-50 via-white to-white";
}

function compactMeta(card: FuelCardItem, operatorName: string | null): string {
  const parts = [
    card.codice ? `Codice ${card.codice}` : null,
    card.sigla,
    card.cod ? `COD ${card.cod}` : null,
    card.expires_at ? `Scadenza ${formatDate(card.expires_at)}` : null,
    operatorName ? `Match: ${operatorName}` : null,
  ].filter(Boolean) as string[];
  return parts.join(" · ") || "—";
}

function DesktopFuelCard({
  card,
  operatorName,
}: {
  card: FuelCardItem;
  operatorName: string | null;
}) {
  return (
    <div className="group overflow-hidden rounded-[28px] border border-[#e6ebe5] bg-white shadow-panel transition hover:-translate-y-1 hover:border-[#c9d6cd] hover:shadow-lg">
      <div className={cn("relative h-40 overflow-hidden bg-gradient-to-br", cardVisualTone(card))}>
        <div className="absolute inset-x-0 top-0 flex items-center justify-between p-4">
          <div className="flex h-14 w-14 items-center justify-center rounded-[20px] border border-white/80 bg-white/90 text-sm font-semibold text-[#1D4E35] shadow-sm">
            {initialsForPan(card.pan)}
          </div>
          <span className={cn("rounded-full px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em]", statusTone(card))}>
            {statusLabel(card)}
          </span>
        </div>
        <div className="absolute inset-x-0 bottom-0 h-20 bg-gradient-to-t from-black/5 to-transparent" />
      </div>

      <div className="px-5 pb-5 pt-4">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="truncate text-[1.05rem] font-semibold uppercase tracking-tight text-gray-900">PAN {card.pan}</p>
            <p className="mt-1 text-sm text-gray-600">{compactMeta(card, operatorName)}</p>
          </div>
          <span className="text-lg text-gray-300 transition group-hover:text-[#1D4E35]">⋮</span>
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-2">
          <span className="inline-flex rounded-full border border-[#e2e6e1] bg-[#f6f7f4] px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-[#5d695f]">
            {card.driver ? `Driver: ${card.driver}` : "Driver non indicato"}
          </span>
          {card.is_blocked ? (
            <span className="inline-flex rounded-full border border-rose-200 bg-rose-50 px-3 py-1 text-xs font-semibold text-rose-700">
              Bloccata
            </span>
          ) : null}
        </div>

        <div className="mt-5 border-t border-dashed border-[#edf1eb] pt-4">
          <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-[#667267]">Dettagli</p>
          <div className="mt-3 grid gap-2 text-sm text-gray-600">
            <p>
              <span className="font-medium text-gray-900">Prodotti:</span> {card.prodotti || "—"}
            </p>
            <p>
              <span className="font-medium text-gray-900">N. Carta/Emissione:</span> {card.card_number_emissione || "—"}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

function MobileFuelCard({
  card,
  operatorName,
}: {
  card: FuelCardItem;
  operatorName: string | null;
}) {
  return (
    <div className="flex items-center gap-3 rounded-[22px] border border-[#e6ebe5] bg-[linear-gradient(180deg,_#ffffff,_#fbfcfa)] px-3 py-3 shadow-panel transition active:scale-[0.995]">
      <div className={cn("relative flex h-[60px] w-[60px] shrink-0 items-center justify-center overflow-hidden rounded-2xl bg-gradient-to-br text-xs font-semibold text-[#1D4E35]", cardVisualTone(card))}>
        <span className="absolute inset-0 bg-white/25" />
        <span className="relative">{initialsForPan(card.pan)}</span>
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="truncate text-[11px] font-semibold uppercase tracking-[0.18em] text-[#667267]">{card.codice ? `Codice ${card.codice}` : "Carta carburante"}</p>
            <p className="truncate text-[1rem] font-semibold leading-tight text-gray-900">PAN {card.pan}</p>
          </div>
          <span className={cn("shrink-0 rounded-full px-2.5 py-1 text-[11px] font-semibold", statusTone(card))}>
            {statusLabel(card)}
          </span>
        </div>
        <p className="mt-1 text-xs text-gray-600">{compactMeta(card, operatorName)}</p>
        <div className="mt-3 flex items-center justify-between gap-3">
          <p className="truncate text-xs text-gray-500">{card.driver ? `Driver: ${card.driver}` : "Driver non indicato"}</p>
          <div className="flex h-7 w-7 items-center justify-center rounded-full bg-[#f6f7f4] text-gray-500">→</div>
        </div>
      </div>
    </div>
  );
}

function CarteCarburanteContent() {
  const [cards, setCards] = useState<FuelCardItem[]>([]);
  const [total, setTotal] = useState(0);
  const [operators, setOperators] = useState<OperatorItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [search, setSearch] = useState("");
  const [blockedFilter, setBlockedFilter] = useState("");
  const [assignedFilter, setAssignedFilter] = useState("");
  const [operatorFilter, setOperatorFilter] = useState("");
  const [isImportModalOpen, setIsImportModalOpen] = useState(false);
  const [isUnmatchedWizardOpen, setIsUnmatchedWizardOpen] = useState(false);

  const operatorById = useMemo(() => {
    const map = new Map<string, OperatorItem>();
    operators.forEach((op) => map.set(op.id, op));
    return map;
  }, [operators]);

  const loadData = useCallback(async () => {
    try {
      const params: Record<string, string> = { page_size: "50" };
      const normalized = normalizeSearch(search);
      if (normalized) params.search = normalized;
      if (blockedFilter) params.blocked = blockedFilter;
      if (assignedFilter) params.assigned = assignedFilter;

      const [cardsPayload, operatorsPayload] = await Promise.all([
        getFuelCards(params),
        getOperators({ page_size: "100" }),
      ]);

      const fetchedCards = (cardsPayload.items ?? []) as FuelCardItem[];
      setCards(
        operatorFilter
          ? fetchedCards.filter((card) => card.current_wc_operator_id === operatorFilter)
          : fetchedCards,
      );
      setTotal((cardsPayload.total ?? fetchedCards.length) as number);
      setOperators((operatorsPayload.items ?? []) as OperatorItem[]);
      setLoadError(null);
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : "Errore nel caricamento carte carburante");
    } finally {
      setIsLoading(false);
    }
  }, [assignedFilter, blockedFilter, operatorFilter, search]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  const metrics = useMemo(() => {
    const blocked = cards.filter((c) => c.is_blocked).length;
    const assigned = cards.filter((c) => Boolean(c.current_wc_operator_id)).length;
    const unassigned = cards.length - assigned;
    return { blocked, assigned, unassigned };
  }, [cards]);

  const operatorOptions = useMemo(() => {
    const sorted = [...operators].sort((a, b) => operatorLabel(a).localeCompare(operatorLabel(b), "it"));
    return [
      { value: "", label: "Tutti gli operatori" },
      ...sorted.map((op) => ({ value: op.id, label: operatorLabel(op) })),
    ];
  }, [operators]);

  return (
    <div className="page-stack">
      <OperazioniCollectionHero
        eyebrow="Carburante e assegnazioni"
        icon={<DocumentIcon className="h-3.5 w-3.5" />}
        title="Carte carburante: anagrafica PAN, stato blocco e passaggi tra operatori tracciati nel tempo."
        description="Import Excel per popolare le carte e registrare automaticamente i cambi driver. La pagina evidenzia carte bloccate, non assegnate e in scadenza."
      >
        {loadError ? (
          <OperazioniHeroNotice title="Caricamento non riuscito" description={loadError} tone="danger" />
        ) : (
          <OperazioniHeroNotice
            title="Sintesi"
            description={`${metrics.assigned} assegnate, ${metrics.unassigned} non assegnate, ${metrics.blocked} bloccate.`}
          />
        )}
        <div className="rounded-2xl border border-white/80 bg-white/75 px-4 py-3">
          <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-gray-500">Azioni</p>
          <div className="mt-3 flex flex-wrap gap-2">
            <button className="btn-primary" type="button" onClick={() => setIsImportModalOpen(true)}>
              Importa Excel carte
            </button>
            <button className="btn-secondary" type="button" onClick={() => setIsUnmatchedWizardOpen(true)}>
              Wizard driver non matchati
            </button>
            <button className="btn-secondary" type="button" onClick={() => void loadData()}>
              <RefreshIcon className="h-4 w-4" />
              Aggiorna
            </button>
          </div>
        </div>
      </OperazioniCollectionHero>

      <OperazioniMetricStrip>
        <MetricCard label="Carte" value={total} sub="totali" />
        <MetricCard label="Assegnate" value={metrics.assigned} sub="con driver matchato" variant="success" />
        <MetricCard label="Non assegnate" value={metrics.unassigned} sub="driver non matchato o vuoto" variant="warning" />
        <MetricCard label="Bloccate" value={metrics.blocked} sub="non utilizzabili" variant="danger" />
      </OperazioniMetricStrip>

      <OperazioniCollectionPanel
        title="Registro carte"
        description="Ricerca per PAN, codice, sigla, COD o driver. Filtra per blocco e assegnazione; opzionale filtro per operatore."
        count={cards.length}
      >
        <OperazioniToolbar
          search={search}
          onSearchChange={setSearch}
          searchPlaceholder="Cerca per PAN, codice, sigla, COD o driver"
          filterValue={blockedFilter}
          onFilterChange={setBlockedFilter}
          filterOptions={[
            { value: "", label: "Tutte (blocco)" },
            { value: "true", label: "Solo bloccate" },
            { value: "false", label: "Solo non bloccate" },
          ]}
        />

        <div className="mt-3 grid gap-3 md:grid-cols-2">
          <label className="block">
            <span className="label-caption">Assegnazione</span>
            <select className="form-control mt-2" value={assignedFilter} onChange={(e) => setAssignedFilter(e.target.value)}>
              <option value="">Tutte</option>
              <option value="true">Solo assegnate</option>
              <option value="false">Solo non assegnate</option>
            </select>
          </label>
          <label className="block">
            <span className="label-caption">Operatore (match WC)</span>
            <select className="form-control mt-2" value={operatorFilter} onChange={(e) => setOperatorFilter(e.target.value)}>
              {operatorOptions.map((opt) => (
                <option key={opt.value || "__all"} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </label>
        </div>

        <div className="mt-4">
          {isLoading ? (
            <p className="text-sm text-gray-500">Caricamento carte in corso.</p>
          ) : cards.length === 0 ? (
            <EmptyState
              icon={DocumentIcon}
              title="Nessuna carta trovata"
              description="Non risultano carte con i filtri correnti. Usa l'import Excel per popolare il registro."
            />
          ) : (
            <>
              <div className="hidden gap-5 lg:grid xl:grid-cols-3">
                {cards.map((card) => {
                  const op = card.current_wc_operator_id ? operatorById.get(card.current_wc_operator_id) : undefined;
                  const opName = op ? operatorLabel(op) : null;
                  return <DesktopFuelCard key={card.id} card={card} operatorName={opName} />;
                })}
              </div>
              <div className="space-y-3 lg:hidden">
                {cards.map((card) => {
                  const op = card.current_wc_operator_id ? operatorById.get(card.current_wc_operator_id) : undefined;
                  const opName = op ? operatorLabel(op) : null;
                  return <MobileFuelCard key={card.id} card={card} operatorName={opName} />;
                })}
              </div>
            </>
          )}
        </div>
      </OperazioniCollectionPanel>

      <ImportFuelCardsModal
        open={isImportModalOpen}
        onClose={(didImport) => {
          setIsImportModalOpen(false);
          if (didImport) {
            setIsLoading(true);
            void loadData();
          }
        }}
      />

      <FuelCardsUnmatchedWizard
        open={isUnmatchedWizardOpen}
        operators={operators}
        onClose={(didUpdate) => {
          setIsUnmatchedWizardOpen(false);
          if (didUpdate) {
            setIsLoading(true);
            void loadData();
          }
        }}
      />
    </div>
  );
}

export default function CarteCarburantePage() {
  return (
    <OperazioniModulePage
      title="Carte carburante"
      description="Registro carte carburante, stato blocco, assegnazioni e storico passaggi tramite import Excel."
      breadcrumb="Lista"
    >
      {() => <CarteCarburanteContent />}
    </OperazioniModulePage>
  );
}

