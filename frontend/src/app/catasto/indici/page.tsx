"use client";

import { useEffect, useMemo, useState } from "react";
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { CatastoPage } from "@/components/catasto/catasto-page";
import { DistrettiIndiciTable } from "@/components/catasto/indici/distretti-table";
import { RuoloReconciliationCard } from "@/components/catasto/indici/ruolo-reconciliation-card";
import { AlertBanner } from "@/components/ui/alert-banner";
import { MetricCard } from "@/components/ui/metric-card";
import { catastoGetIndiciOverview } from "@/lib/api/catasto";
import { getStoredAccessToken } from "@/lib/auth";
import type {
  CatIndiceBreakdownSummary,
  CatIndiceColturaSummary,
  CatIndiceGroupSummary,
  CatIndiceOverview,
} from "@/types/catasto";

const INDEX_COLORS: Record<string, string> = {
  alta_pressione: "#14532d",
  bassa_pressione: "#1d4ed8",
  canaletta: "#ea580c",
  non_classificato: "#64748b",
};

function formatInteger(value: number): string {
  return new Intl.NumberFormat("it-IT").format(value);
}

function formatHa(value: string | number): string {
  const numeric = typeof value === "number" ? value : Number(value);
  return new Intl.NumberFormat("it-IT", { minimumFractionDigits: 1, maximumFractionDigits: 1 }).format(numeric);
}

function formatEuro(value: string | number): string {
  const numeric = typeof value === "number" ? value : Number(value);
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
  const [isLoadingOverview, setIsLoadingOverview] = useState(true);
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

  const selectedGroup = useMemo<CatIndiceGroupSummary | null>(
    () => overview?.items.find((item) => item.indice_key === selectedIndice) ?? null,
    [overview, selectedIndice],
  );

  const distrettiCoverage = useMemo(() => {
    const items = overview?.items ?? [];
    const classificati = items
      .filter((item) => item.indice_key !== "non_classificato")
      .reduce((sum, item) => sum + item.distretti_count, 0);
    const fuoriQuadro = items.find((item) => item.indice_key === "non_classificato")?.distretti_count ?? 0;
    return { classificati, fuoriQuadro };
  }, [overview]);

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

  const selectedDerivedStats = useMemo(() => {
    if (!selectedGroup || !selectedGroup.ruolo_metrics_reliable) {
      return {
        euroPerHa: null as number | null,
        haPerParticellaRuolo: null as number | null,
        anagraficaCoverage: null as number | null,
        roleToReferenceCoverage: null as number | null,
      };
    }

    const superficieIrrigata = Number(selectedGroup.superficie_irrigata_ha);
    const importoRuolo = Number(selectedGroup.importo_ruolo);
    const hectaresReference = Number(selectedGroup.hectares_reference_total ?? 0);
    const ruoloParticelle = selectedGroup.ruolo_particelle_count;
    const particelleTotali = selectedGroup.particelle_count;
    const particelleConAnagrafica = selectedGroup.particelle_con_anagrafica_count;

    return {
      euroPerHa: superficieIrrigata > 0 && importoRuolo > 0 ? importoRuolo / superficieIrrigata : null,
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
        value: selectedGroup?.ruolo_metrics_reliable ? formatEuro(item.importo_ruolo) : "Dato non affidabile",
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
        value: selectedGroup?.ruolo_metrics_reliable ? formatEuro(item.importo_ruolo) : "Dato non affidabile",
        detail: selectedGroup?.ruolo_metrics_reliable
          ? `${formatInteger(item.ruolo_particelle_count)} a ruolo · ${formatHa(item.superficie_irrigata_ha)} ha`
          : `${formatInteger(item.ruolo_particelle_count)} a ruolo · superficie ruolo non affidabile`,
      })),
    [selectedGroup],
  );

  const topColtureByImporto = useMemo(
    () =>
      [...(selectedGroup?.colture ?? [])]
        .sort((left: CatIndiceColturaSummary, right: CatIndiceColturaSummary) => Number(right.importo_ruolo) - Number(left.importo_ruolo))
        .map((item: CatIndiceColturaSummary) => ({
          key: item.coltura,
          label: item.coltura,
          value: selectedGroup?.ruolo_metrics_reliable ? formatEuro(item.importo_ruolo) : "Dato non affidabile",
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

    const missingRole = selectedGroup.particelle_senza_ruolo_count;
    const missingAnagrafica = selectedGroup.particelle_senza_anagrafica_count;
    const total = selectedGroup.particelle_count;

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
        value: formatInteger(Math.max(selectedGroup.particelle_con_anagrafica_count + selectedGroup.ruolo_particelle_count - total, 0)),
        sub: "Intersezione utile per azioni operative e recupero dati",
      },
      {
        label: "Copertura ruolo",
        value: total > 0 ? formatPercent((selectedGroup.ruolo_particelle_count / total) * 100) : "—",
        sub: `${formatInteger(selectedGroup.ruolo_particelle_count)} particelle con ultima riga ruolo valida`,
      },
    ];
  }, [selectedGroup]);

  return (
    <CatastoPage
      title="Indici"
      description="Classificazione distretti per indice irriguo, colture prevalenti e quadro completo dei distretti con superfici e importi ruolo."
      breadcrumb="Catasto / Indici"
      requiredModule="catasto"
    >
      <div className="page-stack">
        {error ? <AlertBanner variant="danger" title="Errore caricamento">{error}</AlertBanner> : null}

        <section className="grid gap-4 md:grid-cols-4">
          <MetricCard label="Anno ruolo" value={overview?.anno_riferimento ?? "—"} sub="Anno di riferimento per colture e importi" />
          <MetricCard label="Indici attivi" value={overview?.items.length ?? 0} sub="Classi operative disponibili" />
          <MetricCard
            label="Distretti coperti"
            value={distrettiCoverage.classificati}
            sub={
              distrettiCoverage.fuoriQuadro > 0
                ? `Distretti del quadro indici · +${formatInteger(distrettiCoverage.fuoriQuadro)} raggruppamenti fuori quadro (FD, adduttori, legacy)`
                : "Distretti classificati dal quadro indici"
            }
          />
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
            <p className="mt-2 text-sm text-slate-500">Riepilogo del blocco selezionato con superfici irrigate, importi ruolo e indicatori derivati.</p>
            {selectedGroup && !selectedGroup.ruolo_metrics_reliable ? (
              <AlertBanner variant="warning" title="Dati ruolo non affidabili">
                {selectedGroup.ruolo_metrics_warning ?? "Le superfici irrigate e gli importi ruolo di questo indice sono temporaneamente sospesi per incoerenze nel dataset sorgente."}
              </AlertBanner>
            ) : null}
            {selectedGroup?.indice_key === "non_classificato" ? (
              <AlertBanner variant="info" title="Cosa contiene questo blocco">
                Particelle fuori dal quadro dei 37 distretti irrigui: aree FD (fuori distretto: servite dai sistemi irrigui ma non incluse in un
                distretto, tributo non dovuto formalmente), canali adduttori e codici legacy. Le particelle a ruolo presenti qui sono casi da
                verificare: potrebbero richiedere riclassificazione del distretto o correzione del dato sorgente.
              </AlertBanner>
            ) : null}

            <div className="mt-5 grid gap-3 md:grid-cols-2">
              <MetricCard label="Particelle" value={selectedGroup?.particelle_count ?? 0} sub="Particelle correnti nell'indice" />
              <MetricCard
                label="Sup. irrigata"
                value={selectedGroup?.ruolo_metrics_reliable ? `${formatHa(selectedGroup.superficie_irrigata_ha)} ha` : "Dato non affidabile"}
                sub={selectedGroup?.ruolo_metrics_reliable ? "Somma dalle righe ruolo collegate" : "Valore sospeso: dataset ruolo 2025 incoerente"}
              />
              <MetricCard
                label="Importo ruolo"
                value={selectedGroup?.ruolo_metrics_reliable ? formatEuro(selectedGroup.importo_ruolo) : "Dato non affidabile"}
                sub={
                  selectedGroup?.ruolo_metrics_reliable
                    ? `Manut. ${formatEuro(selectedGroup.importo_ruolo_manutenzione)} · Irrig. ${formatEuro(selectedGroup.importo_ruolo_irrigazione)} · Ist. ${formatEuro(selectedGroup.importo_ruolo_istituzionale)}`
                    : "Dipende dalle righe ruolo non affidabili"
                }
              />
              <MetricCard label="Ha riferimento" value={selectedGroup?.hectares_reference_total ? `${formatHa(selectedGroup.hectares_reference_total)} ha` : "—"} sub="Valore dal quadro distretti fornito" />
            </div>

            <div className="mt-3 grid gap-3 md:grid-cols-2">
              <MetricCard
                label="EUR / ha medio"
                value={selectedGroup?.ruolo_metrics_reliable && selectedDerivedStats.euroPerHa != null ? formatEuro(selectedDerivedStats.euroPerHa) : "—"}
                sub={selectedGroup?.ruolo_metrics_reliable ? "Importo ruolo medio per ettaro irrigato" : "Non calcolabile su dataset ruolo non affidabile"}
              />
              <MetricCard
                label="Ha / particella"
                value={selectedGroup?.ruolo_metrics_reliable && selectedDerivedStats.haPerParticellaRuolo != null ? `${formatHa(selectedDerivedStats.haPerParticellaRuolo)} ha` : "—"}
                sub={
                  selectedGroup?.ruolo_metrics_reliable
                    ? `Media sulle ${formatInteger(selectedGroup.ruolo_particelle_count)} particelle con ruolo`
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
          </article>
        </section>

        <section className="grid gap-6 xl:grid-cols-2">
          <article className="panel-card">
            <div>
              <p className="text-sm font-semibold text-slate-900">Colture prevalenti</p>
              <p className="text-xs text-slate-500">Top colture dell&apos;ultima annualita ruolo disponibile per l&apos;indice selezionato.</p>
            </div>
            <div className="mt-4 h-[300px]">
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
          </article>

          <article className="panel-card">
            <div>
              <p className="text-sm font-semibold text-slate-900">Approfondimenti operativi</p>
              <p className="text-xs text-slate-500">Ranking economici e segnali di qualita dati per decidere dove intervenire prima.</p>
            </div>

            <div className="mt-4 grid gap-3 md:grid-cols-2">
              {qualityCards.map((item) => (
                <MetricCard key={item.label} label={item.label} value={item.value} sub={item.sub} />
              ))}
            </div>

            <div className="mt-4 grid gap-4 md:grid-cols-3">
              <RankingList title="Top comuni" subtitle="Ordinati per importo ruolo" items={topComuni} />
              <RankingList title="Top distretti" subtitle="Distretti dell'indice per peso economico" items={topDistretti} />
              <RankingList title="Top colture" subtitle="Colture ordinate per importo ruolo" items={topColtureByImporto} />
            </div>
          </article>
        </section>

        <RuoloReconciliationCard reconciliation={overview?.ruolo_reconciliation} anno={overview?.anno_riferimento} />

        <DistrettiIndiciTable overview={overview} isLoading={isLoadingOverview} />
      </div>
    </CatastoPage>
  );
}
