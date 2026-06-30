"use client";

import { useEffect, useMemo, useState } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { ParticellaDetailDialog } from "@/components/catasto/anagrafica/ParticellaDetailDialog";
import { CatastoPage } from "@/components/catasto/catasto-page";
import { DataTable } from "@/components/table/data-table";
import { AlertBanner } from "@/components/ui/alert-banner";
import { EmptyState } from "@/components/ui/empty-state";
import { MetricCard } from "@/components/ui/metric-card";
import { SearchIcon } from "@/components/ui/icons";
import { catastoGetIndiciOverview, catastoListParticelle } from "@/lib/api/catasto";
import { getStoredAccessToken } from "@/lib/auth";
import type {
  CatAnagraficaMatch,
  CatIndiceBreakdownSummary,
  CatIndiceColturaSummary,
  CatIndiceGroupSummary,
  CatIndiceOverview,
  CatParticella,
} from "@/types/catasto";

const INDEX_COLORS: Record<string, string> = {
  alta_pressione: "#14532d",
  bassa_pressione: "#1d4ed8",
  canaletta: "#ea580c",
  non_classificato: "#64748b",
};

type DrilldownFilters = {
  search: string;
  comune: string;
  distretto: string;
  foglio: string;
  particella: string;
  onlyWithAnagrafica: boolean;
};

const EMPTY_DRILLDOWN_FILTERS: DrilldownFilters = {
  search: "",
  comune: "",
  distretto: "",
  foglio: "",
  particella: "",
  onlyWithAnagrafica: false,
};

function particellaToMatch(p: CatParticella): CatAnagraficaMatch {
  return {
    particella_id: p.id,
    unit_id: null,
    comune_id: p.comune_id,
    comune: p.nome_comune,
    cod_comune_capacitas: p.cod_comune_capacitas,
    codice_catastale: p.codice_catastale,
    foglio: p.foglio,
    particella: p.particella,
    subalterno: p.subalterno,
    num_distretto: p.num_distretto,
    nome_distretto: p.nome_distretto,
    superficie_mq: p.superficie_mq,
    superficie_grafica_mq: p.superficie_grafica_mq,
    presente_in_catasto_consorzio: false,
    utenza_latest: null,
    cert_com: null,
    cert_pvc: null,
    cert_fra: null,
    cert_ccs: null,
    stato_ruolo: null,
    stato_cnc: null,
    intestatari: [],
    anomalie_count: 0,
    anomalie_top: [],
    note: null,
  };
}

function formatInteger(value: number): string {
  return new Intl.NumberFormat("it-IT").format(value);
}

function formatHa(value: string | number | null | undefined): string {
  const numeric = typeof value === "number" ? value : Number(value ?? 0);
  return new Intl.NumberFormat("it-IT", { minimumFractionDigits: 1, maximumFractionDigits: 1 }).format(numeric);
}

function formatHaFromMq(value: string | number | null | undefined): string {
  const numeric = typeof value === "number" ? value : Number(value ?? 0);
  return formatHa(numeric / 10_000);
}

function formatEuro(value: string | number | null | undefined): string {
  const numeric = typeof value === "number" ? value : Number(value ?? 0);
  return new Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR", maximumFractionDigits: 0 }).format(numeric);
}

function formatPercent(value: number | null): string {
  if (value == null || Number.isNaN(value)) {
    return "—";
  }
  return new Intl.NumberFormat("it-IT", { minimumFractionDigits: 1, maximumFractionDigits: 1 }).format(value) + "%";
}

function RankingList({
  title,
  subtitle,
  items,
}: {
  title: string;
  subtitle: string;
  items: Array<{
    key: string;
    label: string;
    value: string;
    detail: string;
  }>;
}) {
  return (
    <div className="rounded-3xl border border-[#d7e4da] bg-white p-4 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-slate-900">{title}</p>
          <p className="text-xs text-slate-500">{subtitle}</p>
        </div>
        <span className="rounded-full border border-[#d7e4da] bg-[#f7fbf8] px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.12em] text-[#5f7d68]">
          Top {Math.min(items.length, 5)}
        </span>
      </div>

      <div className="mt-4 space-y-3">
        {items.length === 0 ? (
          <p className="rounded-2xl border border-dashed border-[#d7e4da] bg-[#f7fbf8] px-4 py-6 text-sm text-slate-500">Nessun dato disponibile.</p>
        ) : (
          items.slice(0, 5).map((item, index) => (
            <div key={item.key} className="flex items-center justify-between gap-4 rounded-2xl border border-[#eef4ef] bg-[#fbfdfb] px-4 py-3">
              <div className="min-w-0">
                <p className="text-sm font-semibold text-slate-900">
                  {index + 1}. {item.label}
                </p>
                <p className="truncate text-xs text-slate-500">{item.detail}</p>
              </div>
              <p className="shrink-0 text-sm font-semibold text-[#1d4e35]">{item.value}</p>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

export default function CatastoIndiciPage() {
  const [overview, setOverview] = useState<CatIndiceOverview | null>(null);
  const [selectedIndice, setSelectedIndice] = useState("alta_pressione");
  const [selectedColtura, setSelectedColtura] = useState("");
  const [draftFilters, setDraftFilters] = useState<DrilldownFilters>(EMPTY_DRILLDOWN_FILTERS);
  const [appliedFilters, setAppliedFilters] = useState<DrilldownFilters>(EMPTY_DRILLDOWN_FILTERS);
  const [particelle, setParticelle] = useState<CatParticella[]>([]);
  const [selectedParticella, setSelectedParticella] = useState<CatParticella | null>(null);
  const [isLoadingOverview, setIsLoadingOverview] = useState(true);
  const [isLoadingParticelle, setIsLoadingParticelle] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadOverview(): Promise<void> {
      const token = getStoredAccessToken();
      if (!token) return;
      setIsLoadingOverview(true);
      try {
        const data = await catastoGetIndiciOverview(token);
        setOverview(data);
        setSelectedIndice((current) =>
          data.items.some((item) => item.indice_key === current) ? current : data.items[0]?.indice_key ?? "alta_pressione",
        );
        setError(null);
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : "Errore caricamento indici");
      } finally {
        setIsLoadingOverview(false);
      }
    }
    void loadOverview();
  }, []);

  useEffect(() => {
    async function loadParticelle(): Promise<void> {
      const token = getStoredAccessToken();
      if (!token || !overview || !selectedIndice) return;
      setIsLoadingParticelle(true);
      try {
        const data = await catastoListParticelle(token, {
          indice: selectedIndice,
          coltura: selectedColtura || undefined,
          anno: overview.anno_riferimento ?? undefined,
          nomeComune: appliedFilters.comune || undefined,
          distretto: appliedFilters.distretto || undefined,
          foglio: appliedFilters.foglio || undefined,
          particella: appliedFilters.particella || undefined,
          search: appliedFilters.search || undefined,
          soloConAnagrafica: appliedFilters.onlyWithAnagrafica,
          soloARuolo: true,
          limit: 200,
        });
        setParticelle(data);
        setError(null);
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : "Errore caricamento particelle");
      } finally {
        setIsLoadingParticelle(false);
      }
    }
    void loadParticelle();
  }, [overview, selectedIndice, selectedColtura, appliedFilters]);

  const selectedGroup = useMemo<CatIndiceGroupSummary | null>(
    () => overview?.items.find((item) => item.indice_key === selectedIndice) ?? null,
    [overview, selectedIndice],
  );

  useEffect(() => {
    if (!selectedGroup) {
      return;
    }
    const validDistretti = new Set(selectedGroup.distretti.map((item) => item.num_distretto));
    if (appliedFilters.distretto && !validDistretti.has(appliedFilters.distretto)) {
      setAppliedFilters((current) => ({ ...current, distretto: "" }));
    }
    if (draftFilters.distretto && !validDistretti.has(draftFilters.distretto)) {
      setDraftFilters((current) => ({ ...current, distretto: "" }));
    }
  }, [selectedGroup, appliedFilters.distretto, draftFilters.distretto]);

  const chartData = useMemo(
    () =>
      (overview?.items ?? []).map((item) => ({
        key: item.indice_key,
        label: item.indice_label,
        particelle: item.particelle_count,
      })),
    [overview],
  );

  const cropChartData = useMemo(
    () =>
      (selectedGroup?.colture ?? []).slice(0, 8).map((item) => ({
        coltura: item.coltura,
        particelle: item.particelle_count,
      })),
    [selectedGroup],
  );

  const activeFilterCount = useMemo(
    () =>
      [
        appliedFilters.search,
        appliedFilters.comune,
        appliedFilters.distretto,
        appliedFilters.foglio,
        appliedFilters.particella,
        appliedFilters.onlyWithAnagrafica ? "1" : "",
      ].filter(Boolean).length,
    [appliedFilters],
  );

  const selectedDerivedStats = useMemo(() => {
    if (!selectedGroup || !selectedGroup.ruolo_metrics_reliable) {
      return {
        euroPerHa: null as number | null,
        haPerParticellaRuolo: null as number | null,
        anagraficaCoverage: null as number | null,
        roleToReferenceCoverage: null as number | null,
      };
    }

    const superficieIrrigata = Number(selectedGroup.superficie_irrigata_ha ?? 0);
    const importoStimato = Number(selectedGroup.importo_stimato ?? 0);
    const hectaresReference = Number(selectedGroup.hectares_reference_total ?? 0);
    const ruoloParticelle = selectedGroup.ruolo_particelle_count ?? 0;
    const particelleTotali = selectedGroup.particelle_count ?? 0;
    const particelleConAnagrafica = selectedGroup.particelle_con_anagrafica_count ?? 0;

    return {
      euroPerHa: superficieIrrigata > 0 ? importoStimato / superficieIrrigata : null,
      haPerParticellaRuolo: ruoloParticelle > 0 ? superficieIrrigata / ruoloParticelle : null,
      anagraficaCoverage: particelleTotali > 0 ? (particelleConAnagrafica / particelleTotali) * 100 : null,
      roleToReferenceCoverage: hectaresReference > 0 ? (superficieIrrigata / hectaresReference) * 100 : null,
    };
  }, [selectedGroup]);

  const topComuni = useMemo(
    () =>
      (selectedGroup?.comuni ?? []).map((item: CatIndiceBreakdownSummary) => ({
        key: item.key,
        label: item.label,
        value: selectedGroup?.ruolo_metrics_reliable ? formatEuro(item.importo_stimato) : "Dato non affidabile",
        detail: selectedGroup?.ruolo_metrics_reliable
          ? `${formatInteger(item.ruolo_particelle_count)} a ruolo · ${formatHa(item.superficie_irrigata_ha)} ha`
          : `${formatInteger(item.ruolo_particelle_count)} a ruolo · superficie ruolo non affidabile`,
      })),
    [selectedGroup],
  );

  const topDistretti = useMemo(
    () =>
      (selectedGroup?.distretti_analytics ?? []).map((item: CatIndiceBreakdownSummary) => ({
        key: item.key,
        label: item.label,
        value: selectedGroup?.ruolo_metrics_reliable ? formatEuro(item.importo_stimato) : "Dato non affidabile",
        detail: selectedGroup?.ruolo_metrics_reliable
          ? `${formatInteger(item.ruolo_particelle_count)} a ruolo · ${formatHa(item.superficie_irrigata_ha)} ha`
          : `${formatInteger(item.ruolo_particelle_count)} a ruolo · superficie ruolo non affidabile`,
      })),
    [selectedGroup],
  );

  const topColtureByImporto = useMemo(
    () =>
      [...(selectedGroup?.colture ?? [])]
        .sort((left: CatIndiceColturaSummary, right: CatIndiceColturaSummary) => Number(right.importo_stimato) - Number(left.importo_stimato))
        .map((item: CatIndiceColturaSummary) => ({
          key: item.coltura,
          label: item.coltura,
          value: selectedGroup?.ruolo_metrics_reliable ? formatEuro(item.importo_stimato) : "Dato non affidabile",
          detail: selectedGroup?.ruolo_metrics_reliable
            ? `${formatInteger(item.particelle_count)} particelle · ${formatHa(item.superficie_irrigata_ha)} ha`
            : `${formatInteger(item.particelle_count)} particelle · superficie ruolo non affidabile`,
        })),
    [selectedGroup],
  );

  const qualityCards = useMemo(() => {
    if (!selectedGroup) {
      return [];
    }

    const missingRole = selectedGroup.particelle_senza_ruolo_count ?? 0;
    const missingAnagrafica = selectedGroup.particelle_senza_anagrafica_count ?? 0;
    const total = selectedGroup.particelle_count ?? 0;

    return [
      {
        label: "Senza anagrafica",
        value: formatInteger(missingAnagrafica),
        sub: total > 0 ? `${formatPercent((missingAnagrafica / total) * 100)} del perimetro selezionato` : "—",
      },
      {
        label: "Senza ruolo",
        value: formatInteger(missingRole),
        sub: total > 0 ? `${formatPercent((missingRole / total) * 100)} del perimetro selezionato` : "—",
      },
      {
        label: "Con anagrafica + ruolo",
        value: formatInteger(Math.max((selectedGroup.particelle_con_anagrafica_count ?? 0) + (selectedGroup.ruolo_particelle_count ?? 0) - total, 0)),
        sub: "Intersezione utile per azioni operative e recupero dati",
      },
      {
        label: "Copertura ruolo",
        value: total > 0 ? formatPercent(((selectedGroup.ruolo_particelle_count ?? 0) / total) * 100) : "—",
        sub: `${formatInteger(selectedGroup.ruolo_particelle_count ?? 0)} particelle con ultima riga ruolo valida`,
      },
    ];
  }, [selectedGroup]);

  const columns = useMemo<ColumnDef<CatParticella>[]>(
    () => [
      {
        header: "Comune",
        accessorKey: "nome_comune",
        cell: ({ row }) => (
          <div>
            <p className="text-sm font-medium text-slate-900">{row.original.nome_comune ?? row.original.cod_comune_capacitas}</p>
            <p className="text-xs text-slate-500">
              Distretto {row.original.num_distretto ?? "—"} · {row.original.indice_label ?? "—"}
            </p>
          </div>
        ),
      },
      {
        header: "Riferimento",
        id: "rif",
        cell: ({ row }) => (
          <span className="text-sm text-slate-700">
            Fg.{row.original.foglio} Part.{row.original.particella}
            {row.original.subalterno ? ` Sub.${row.original.subalterno}` : ""}
          </span>
        ),
      },
      {
        header: "Coltura",
        id: "coltura",
        cell: ({ row }) => (
          <div>
            <p className="text-sm text-slate-800">{row.original.indice_irriguo_coltura ?? "—"}</p>
            <p className="text-xs text-slate-500">{row.original.indice_irriguo_gruppo_coltura ?? "Gruppo non dedotto"}</p>
          </div>
        ),
      },
      {
        header: "Sup. catastale",
        id: "sup",
        cell: ({ row }) => <span className="text-sm text-slate-700">{formatHaFromMq(row.original.superficie_mq)} ha</span>,
      },
      {
        header: "CF / P.IVA",
        id: "cf",
        cell: ({ row }) => <span className="text-sm text-slate-700">{row.original.utenza_cf ?? "—"}</span>,
      },
      {
        header: "Denominazione",
        id: "den",
        cell: ({ row }) => <span className="text-sm text-slate-700">{row.original.utenza_denominazione ?? "—"}</span>,
      },
      {
        header: "Dettaglio",
        id: "detail",
        enableSorting: false,
        cell: ({ row }) => (
          <button
            type="button"
            className="rounded-full border border-[#d7e4da] bg-[#f7fbf8] px-3 py-1 text-xs font-semibold text-[#1d4e35] transition hover:border-[#1d4e35] hover:bg-[#edf6f0]"
            onClick={(event) => {
              event.stopPropagation();
              setSelectedParticella(row.original);
            }}
          >
            Apri dettaglio
          </button>
        ),
      },
    ],
    [],
  );

  return (
    <CatastoPage
      title="Indici"
      description="Classificazione distretti per indice irriguo, colture prevalenti e drill-down sulle particelle a ruolo."
      breadcrumb="Catasto / Indici"
      requiredModule="catasto"
    >
      <div className="page-stack">
        {error ? <AlertBanner variant="danger" title="Errore caricamento">{error}</AlertBanner> : null}

        <section className="grid gap-4 md:grid-cols-4">
          <MetricCard label="Anno ruolo" value={overview?.anno_riferimento ?? "—"} sub="Anno di riferimento per colture e importi" />
          <MetricCard label="Indici attivi" value={overview?.items.length ?? 0} sub="Classi operative disponibili" />
          <MetricCard label="Distretti coperti" value={overview?.total_distretti ?? 0} sub="Distretti classificati dal quadro indici" />
          <MetricCard label="Particelle correnti" value={overview?.total_particelle ?? 0} sub="Particelle aggregate sui distretti classificati" />
        </section>

        <section className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
          <article className="panel-card">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#5f7d68]">Quadro indici</p>
            <h2 className="mt-1 text-2xl font-semibold tracking-tight text-slate-950">Distribuzione particelle per indice operativo</h2>
            <p className="mt-2 text-sm text-slate-500">La vista unisce classificazione distretti, superfici e colture ruolo per offrire un ingresso analitico dedicato.</p>

            <div className="mt-6 grid gap-3 md:grid-cols-3">
              {(overview?.items ?? []).map((item) => (
                <button
                  key={item.indice_key}
                  type="button"
                  className={
                    selectedIndice === item.indice_key
                      ? "rounded-3xl border border-[#1d4e35] bg-[#1d4e35] p-4 text-left text-white shadow-lg"
                      : "rounded-3xl border border-[#d7e4da] bg-white p-4 text-left text-slate-800 shadow-sm transition hover:border-[#1d4e35]"
                  }
                  onClick={() => setSelectedIndice(item.indice_key)}
                >
                  <p className="text-xs font-semibold uppercase tracking-[0.16em] opacity-80">{item.indice_label}</p>
                  <p className="mt-3 text-2xl font-semibold">{formatInteger(item.particelle_count)}</p>
                  <p className="mt-1 text-sm opacity-80">{item.distretti_count} distretti</p>
                </button>
              ))}
            </div>

            <div className="mt-6 h-[320px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} margin={{ top: 8, right: 12, left: 4, bottom: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="label" tickLine={false} axisLine={false} />
                  <YAxis tickLine={false} axisLine={false} />
                  <Tooltip formatter={(value) => [formatInteger(Number(value)), "Particelle"]} />
                  <Bar dataKey="particelle" radius={[12, 12, 0, 0]}>
                    {chartData.map((entry) => (
                      <Cell key={entry.key} fill={INDEX_COLORS[entry.key] ?? INDEX_COLORS.non_classificato} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </article>

          <article className="panel-card">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#5f7d68]">Dettaglio selezione</p>
            <h2 className="mt-1 text-2xl font-semibold tracking-tight text-slate-950">{selectedGroup?.indice_label ?? "Indice"}</h2>
            <p className="mt-2 text-sm text-slate-500">Riepilogo del blocco selezionato con superfici irrigate, importi stimati e colture più presenti.</p>
            {selectedGroup && !selectedGroup.ruolo_metrics_reliable ? (
              <AlertBanner variant="warning" title="Dati ruolo non affidabili">
                {selectedGroup.ruolo_metrics_warning ?? "Le superfici irrigate e gli importi ruolo di questo indice sono temporaneamente sospesi per incoerenze nel dataset sorgente."}
              </AlertBanner>
            ) : null}

            <div className="mt-5 grid gap-3 md:grid-cols-2">
              <MetricCard label="Particelle" value={selectedGroup?.particelle_count ?? 0} sub="Particelle correnti nell'indice" />
              <MetricCard
                label="Sup. irrigata"
                value={selectedGroup?.ruolo_metrics_reliable ? `${formatHa(selectedGroup?.superficie_irrigata_ha)} ha` : "Dato non affidabile"}
                sub={selectedGroup?.ruolo_metrics_reliable ? "Somma dalle righe ruolo collegate" : "Valore sospeso: dataset ruolo 2025 incoerente"}
              />
              <MetricCard
                label="Importo stimato"
                value={selectedGroup?.ruolo_metrics_reliable ? formatEuro(selectedGroup?.importo_stimato) : "Dato non affidabile"}
                sub={selectedGroup?.ruolo_metrics_reliable ? "Preview indice irriguo" : "Dipende dalla sup. irrigata ruolo non affidabile"}
              />
              <MetricCard label="Ha riferimento" value={selectedGroup?.hectares_reference_total ? `${formatHa(selectedGroup.hectares_reference_total)} ha` : "—"} sub="Valore dal quadro distretti fornito" />
            </div>

            <div className="mt-3 grid gap-3 md:grid-cols-2">
              <MetricCard
                label="EUR / ha medio"
                value={selectedGroup?.ruolo_metrics_reliable && selectedDerivedStats.euroPerHa != null ? formatEuro(selectedDerivedStats.euroPerHa) : "—"}
                sub={selectedGroup?.ruolo_metrics_reliable ? "Importo stimato medio per ettaro irrigato" : "Non calcolabile su dataset ruolo non affidabile"}
              />
              <MetricCard
                label="Ha / particella"
                value={selectedGroup?.ruolo_metrics_reliable && selectedDerivedStats.haPerParticellaRuolo != null ? `${formatHa(selectedDerivedStats.haPerParticellaRuolo)} ha` : "—"}
                sub={
                  selectedGroup?.ruolo_metrics_reliable
                    ? `Media sulle ${formatInteger(selectedGroup?.ruolo_particelle_count ?? 0)} particelle con ruolo`
                    : `Dato sospeso su ${formatInteger(selectedGroup?.ruolo_metrics_invalid_count ?? 0)} righe incoerenti`
                }
              />
              <MetricCard
                label="Copertura anagrafica"
                value={formatPercent(selectedDerivedStats.anagraficaCoverage)}
                sub={`${formatInteger(selectedGroup?.particelle_con_anagrafica_count ?? 0)} particelle con anagrafica collegata`}
              />
              <MetricCard
                label="Ha ruolo / riferimento"
                value={selectedGroup?.ruolo_metrics_reliable ? formatPercent(selectedDerivedStats.roleToReferenceCoverage) : "—"}
                sub={selectedGroup?.ruolo_metrics_reliable ? "Rapporto tra ettari irrigati e quadro di riferimento distretti" : "Non calcolabile su dataset ruolo non affidabile"}
              />
            </div>

            <div className="mt-6 rounded-3xl border border-[#d7e4da] bg-[#f7fbf8] p-4">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="text-sm font-semibold text-slate-900">Colture prevalenti</p>
                  <p className="text-xs text-slate-500">Top colture dell&apos;ultima annualita ruolo disponibile per questo indice.</p>
                </div>
                <select className="form-control w-auto min-w-[220px] bg-white" value={selectedColtura} onChange={(event) => setSelectedColtura(event.target.value)}>
                  <option value="">Tutte le colture</option>
                  {(selectedGroup?.colture ?? []).map((item) => (
                    <option key={item.coltura} value={item.coltura}>
                      {item.coltura}
                    </option>
                  ))}
                </select>
              </div>
              <div className="mt-4 h-[240px]">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={cropChartData} layout="vertical" margin={{ top: 8, right: 8, left: 12, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                    <XAxis type="number" tickLine={false} axisLine={false} />
                    <YAxis dataKey="coltura" type="category" tickLine={false} axisLine={false} width={120} />
                    <Tooltip formatter={(value) => [formatInteger(Number(value)), "Particelle"]} />
                    <Bar dataKey="particelle" fill={INDEX_COLORS[selectedIndice] ?? INDEX_COLORS.non_classificato} radius={[0, 12, 12, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="mt-6 rounded-3xl border border-[#d7e4da] bg-[#f7fbf8] p-4">
              <div>
                <p className="text-sm font-semibold text-slate-900">Approfondimenti operativi</p>
                <p className="text-xs text-slate-500">Ranking economici e segnali di qualita dati per decidere dove intervenire prima.</p>
              </div>

              <div className="mt-4 grid gap-3 md:grid-cols-2">
                {qualityCards.map((item) => (
                  <MetricCard key={item.label} label={item.label} value={item.value} sub={item.sub} />
                ))}
              </div>

              <div className="mt-4 grid gap-4 xl:grid-cols-3">
                <RankingList title="Top comuni" subtitle="Ordinati per importo stimato" items={topComuni} />
                <RankingList title="Top distretti" subtitle="Distretti dell'indice per peso economico" items={topDistretti} />
                <RankingList title="Top colture" subtitle="Colture ordinate per importo stimato" items={topColtureByImporto} />
              </div>
            </div>
          </article>
        </section>

        <article className="panel-card">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#5f7d68]">Drill-down particelle</p>
              <h2 className="mt-1 text-2xl font-semibold tracking-tight text-slate-950">Particelle a ruolo filtrate per indice e coltura</h2>
              <p className="mt-2 text-sm text-slate-500">La tabella isola le particelle del blocco selezionato e apre la stessa modal di dettaglio usata nella sezione Catasto / Particelle.</p>
            </div>
            <div className="rounded-2xl border border-[#d7e4da] bg-[#f7fbf8] px-4 py-3 text-sm text-slate-600">
              {isLoadingParticelle ? "Caricamento particelle..." : `${formatInteger(particelle.length)} righe mostrate (max 200)`}
            </div>
          </div>

          <div className="mt-6 rounded-3xl border border-[#d7e4da] bg-[#f7fbf8] p-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p className="text-sm font-semibold text-slate-900">Filtri drill-down</p>
                <p className="text-xs text-slate-500">Raffina l&apos;elenco per comune, distretto, riferimento catastale o anagrafica collegata.</p>
              </div>
              <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
                {activeFilterCount > 0 ? <span className="rounded-full border border-[#d7e4da] bg-white px-3 py-1 font-medium">{activeFilterCount} filtri attivi</span> : null}
                <button
                  type="button"
                  className="rounded-full border border-[#d7e4da] bg-white px-3 py-1 font-semibold text-slate-700 transition hover:border-[#1d4e35] hover:text-[#1d4e35]"
                  onClick={() => setAppliedFilters(draftFilters)}
                >
                  Applica filtri
                </button>
                <button
                  type="button"
                  className="rounded-full border border-[#d7e4da] bg-white px-3 py-1 font-semibold text-slate-700 transition hover:border-[#1d4e35] hover:text-[#1d4e35]"
                  onClick={() => {
                    setDraftFilters(EMPTY_DRILLDOWN_FILTERS);
                    setAppliedFilters(EMPTY_DRILLDOWN_FILTERS);
                  }}
                >
                  Reset
                </button>
              </div>
            </div>

            <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-5">
              <label className="block">
                <span className="mb-1 block text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-500">Ricerca CF / intestatario</span>
                <input
                  className="form-control h-11 w-full rounded-2xl bg-white"
                  value={draftFilters.search}
                  onChange={(event) => setDraftFilters((current) => ({ ...current, search: event.target.value }))}
                  placeholder="CF, P.IVA, denominazione"
                />
              </label>

              <label className="block">
                <span className="mb-1 block text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-500">Comune</span>
                <input
                  className="form-control h-11 w-full rounded-2xl bg-white"
                  value={draftFilters.comune}
                  onChange={(event) => setDraftFilters((current) => ({ ...current, comune: event.target.value }))}
                  placeholder="Es. Arborea"
                />
              </label>

              <label className="block">
                <span className="mb-1 block text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-500">Distretto</span>
                <select
                  className="form-control h-11 w-full rounded-2xl bg-white"
                  value={draftFilters.distretto}
                  onChange={(event) => setDraftFilters((current) => ({ ...current, distretto: event.target.value }))}
                >
                  <option value="">Tutti i distretti</option>
                  {(selectedGroup?.distretti ?? []).map((item) => (
                    <option key={item.distretto_id} value={item.num_distretto}>
                      {item.num_distretto} · {item.nome_distretto}
                    </option>
                  ))}
                </select>
              </label>

              <label className="block">
                <span className="mb-1 block text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-500">Foglio</span>
                <input
                  className="form-control h-11 w-full rounded-2xl bg-white"
                  value={draftFilters.foglio}
                  onChange={(event) => setDraftFilters((current) => ({ ...current, foglio: event.target.value }))}
                  placeholder="Es. 12"
                />
              </label>

              <label className="block">
                <span className="mb-1 block text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-500">Particella</span>
                <input
                  className="form-control h-11 w-full rounded-2xl bg-white"
                  value={draftFilters.particella}
                  onChange={(event) => setDraftFilters((current) => ({ ...current, particella: event.target.value }))}
                  placeholder="Es. 345"
                />
              </label>
            </div>

            <label className="mt-3 flex items-center gap-2 text-sm text-slate-700">
              <input
                type="checkbox"
                className="h-4 w-4 rounded border-[#c7d7cb] text-[#1d4e35] focus:ring-[#1d4e35]"
                checked={draftFilters.onlyWithAnagrafica}
                onChange={(event) => setDraftFilters((current) => ({ ...current, onlyWithAnagrafica: event.target.checked }))}
              />
              Mostra solo particelle con anagrafica collegata
            </label>
          </div>

          <div className="mt-6">
            {isLoadingOverview || isLoadingParticelle ? (
              <div className="rounded-2xl border border-gray-100 bg-gray-50 px-4 py-5 text-sm text-gray-500">Caricamento workspace indici...</div>
            ) : particelle.length === 0 ? (
              <EmptyState icon={SearchIcon} title="Nessuna particella trovata" description="Non risultano particelle a ruolo per l'indice e la coltura selezionati." />
            ) : (
              <DataTable data={particelle} columns={columns} initialPageSize={12} onRowClick={(row) => setSelectedParticella(row)} />
            )}
          </div>
        </article>
      </div>

      <ParticellaDetailDialog
        open={selectedParticella !== null}
        match={selectedParticella ? particellaToMatch(selectedParticella) : null}
        onClose={() => setSelectedParticella(null)}
      />
    </CatastoPage>
  );
}
