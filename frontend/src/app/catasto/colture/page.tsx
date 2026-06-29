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
import { catastoGetColtureOverview, catastoListParticelle } from "@/lib/api/catasto";
import { getStoredAccessToken } from "@/lib/auth";
import type { CatAnagraficaMatch, CatColturaBreakdownItem, CatColturaOverview, CatColturaSummary, CatParticella } from "@/types/catasto";

const QUALITY_STYLES: Record<string, string> = {
  misto: "border-[#1d4e35] bg-[#1d4e35] text-white",
  reale: "border-[#1d4ed8] bg-[#eff6ff] text-[#1d4ed8]",
  stimato: "border-[#b45309] bg-[#fff7ed] text-[#b45309]",
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

function formatInteger(value: number | null | undefined): string {
  return new Intl.NumberFormat("it-IT").format(value ?? 0);
}

function formatDecimal(value: string | number | null | undefined, digits = 1): string {
  const numeric = typeof value === "number" ? value : Number(value ?? 0);
  return new Intl.NumberFormat("it-IT", { minimumFractionDigits: digits, maximumFractionDigits: digits }).format(numeric);
}

function formatEuro(value: string | number | null | undefined): string {
  const numeric = typeof value === "number" ? value : Number(value ?? 0);
  return new Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR", maximumFractionDigits: 2 }).format(numeric);
}

function formatMaybe(value: string | null | undefined, suffix: string, digits = 1): string {
  if (value == null) return "—";
  return `${formatDecimal(value, digits)} ${suffix}`;
}

function topBreakdowns(items: CatColturaBreakdownItem[]): CatColturaBreakdownItem[] {
  return items.slice(0, 8);
}

export default function CatastoColturePage() {
  const [overview, setOverview] = useState<CatColturaOverview | null>(null);
  const [selectedAnno, setSelectedAnno] = useState<number | null>(null);
  const [selectedColtura, setSelectedColtura] = useState<string>("");
  const [groupFilter, setGroupFilter] = useState("");
  const [qualityFilter, setQualityFilter] = useState("");
  const [search, setSearch] = useState("");
  const [particelle, setParticelle] = useState<CatParticella[]>([]);
  const [selectedParticella, setSelectedParticella] = useState<CatParticella | null>(null);
  const [loadingOverview, setLoadingOverview] = useState(true);
  const [loadingParticelle, setLoadingParticelle] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadOverview(): Promise<void> {
      const token = getStoredAccessToken();
      if (!token) return;
      setLoadingOverview(true);
      try {
        const data = await catastoGetColtureOverview(token, selectedAnno ?? undefined);
        setOverview(data);
        setSelectedAnno(data.anno_riferimento ?? null);
        setSelectedColtura((current) => (data.items.some((item) => item.coltura === current) ? current : data.items[0]?.coltura ?? ""));
        setError(null);
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : "Errore caricamento colture");
      } finally {
        setLoadingOverview(false);
      }
    }
    void loadOverview();
  }, [selectedAnno]);

  const filteredItems = useMemo(() => {
    const items = overview?.items ?? [];
    return items.filter((item) => {
      if (groupFilter && item.gruppo_coltura !== groupFilter) return false;
      if (qualityFilter && item.quality_badge !== qualityFilter) return false;
      if (search) {
        const haystack = `${item.coltura} ${item.gruppo_coltura ?? ""}`.toLowerCase();
        if (!haystack.includes(search.toLowerCase())) return false;
      }
      return true;
    });
  }, [groupFilter, overview, qualityFilter, search]);

  useEffect(() => {
    if (!filteredItems.some((item) => item.coltura === selectedColtura)) {
      setSelectedColtura(filteredItems[0]?.coltura ?? "");
    }
  }, [filteredItems, selectedColtura]);

  useEffect(() => {
    async function loadParticelle(): Promise<void> {
      const token = getStoredAccessToken();
      if (!token || !selectedColtura || selectedAnno == null) return;
      setLoadingParticelle(true);
      try {
        const data = await catastoListParticelle(token, {
          coltura: selectedColtura,
          anno: selectedAnno,
          soloARuolo: true,
          limit: 200,
        });
        setParticelle(data);
        setError(null);
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : "Errore caricamento particelle");
      } finally {
        setLoadingParticelle(false);
      }
    }
    void loadParticelle();
  }, [selectedAnno, selectedColtura]);

  const selectedItem = useMemo<CatColturaSummary | null>(
    () => filteredItems.find((item) => item.coltura === selectedColtura) ?? null,
    [filteredItems, selectedColtura],
  );

  const overviewChartData = useMemo(
    () =>
      filteredItems.slice(0, 10).map((item) => ({
        coltura: item.coltura,
        importo: Number(item.importo_totale ?? 0),
        consumo: Number(item.consumo_reale_mc ?? 0),
      })),
    [filteredItems],
  );

  const yearSeriesData = useMemo(
    () =>
      (selectedItem?.years ?? [])
        .slice()
        .reverse()
        .map((item) => ({
          anno: String(item.anno),
          importo: Number(item.importo_totale ?? 0),
          consumo: Number(item.consumo_reale_mc ?? 0),
        })),
    [selectedItem],
  );

  const breakdownColumns = useMemo<ColumnDef<CatColturaBreakdownItem>[]>(
    () => [
      { header: "Voce", accessorKey: "label" },
      { header: "Particelle ruolo", accessorKey: "role_particelle_count" },
      { header: "Letture", accessorKey: "meter_readings_count" },
      { header: "Sup. irrigata", id: "sup", cell: ({ row }) => `${formatDecimal(row.original.superficie_irrigata_ha)} ha` },
      { header: "Importo", id: "imp", cell: ({ row }) => formatEuro(row.original.importo_totale) },
      { header: "Consumo", id: "cons", cell: ({ row }) => `${formatDecimal(row.original.consumo_reale_mc)} mc` },
      { header: "€/mc", id: "ratio", cell: ({ row }) => (row.original.euro_per_mc ? formatEuro(row.original.euro_per_mc) : "—") },
    ],
    [],
  );

  const particelleColumns = useMemo<ColumnDef<CatParticella>[]>(
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
        header: "Coltura ruolo",
        id: "coltura",
        cell: ({ row }) => (
          <div>
            <p className="text-sm text-slate-800">{row.original.indice_irriguo_coltura ?? "—"}</p>
            <p className="text-xs text-slate-500">{row.original.indice_irriguo_gruppo_coltura ?? "Gruppo non dedotto"}</p>
          </div>
        ),
      },
      { header: "CF / P.IVA", id: "cf", cell: ({ row }) => <span className="text-sm text-slate-700">{row.original.utenza_cf ?? "—"}</span> },
      { header: "Denominazione", id: "den", cell: ({ row }) => <span className="text-sm text-slate-700">{row.original.utenza_denominazione ?? "—"}</span> },
    ],
    [],
  );

  return (
    <CatastoPage
      title="Colture"
      description="Vista completa per coltura con incroci ruolo, consumi idrici e rapporti costo/consumo."
      breadcrumb="Catasto / Colture"
      requiredModule="catasto"
    >
      <div className="page-stack">
        {error ? <AlertBanner variant="danger" title="Errore caricamento">{error}</AlertBanner> : null}

        <section className="grid gap-4 md:grid-cols-5">
          <MetricCard label="Anno riferimento" value={overview?.anno_riferimento ?? "—"} sub="Annualita attiva per i totali della vista" />
          <MetricCard label="Colture attive" value={overview?.total_colture ?? 0} sub="Colture con dati ruolo o consumo nel perimetro" />
          <MetricCard label="Particelle ruolo" value={overview?.total_role_particelle ?? 0} sub="Particelle con coltura e superficie irrigata" />
          <MetricCard label="Importo ruolo" value={formatEuro(overview?.total_importo_totale)} sub="Somma importi reali o stimati nel perimetro" />
          <MetricCard label="Consumo reale" value={formatMaybe(overview?.total_consumo_reale_mc, "mc")} sub="Somma letture contatori con consumo effettivo" />
        </section>

        <section className="panel-card">
          <div className="grid gap-4 lg:grid-cols-[180px_220px_220px_1fr]">
            <label>
              <span className="mb-2 block text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Anno</span>
              <select
                className="form-control"
                value={selectedAnno ?? ""}
                onChange={(event) => setSelectedAnno(event.target.value ? Number(event.target.value) : null)}
              >
                {(overview?.available_years ?? []).map((year) => (
                  <option key={year} value={year}>
                    {year}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <span className="mb-2 block text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Gruppo coltura</span>
              <select className="form-control" value={groupFilter} onChange={(event) => setGroupFilter(event.target.value)}>
                <option value="">Tutti i gruppi</option>
                {(overview?.available_groups ?? []).map((item) => (
                  <option key={item} value={item}>
                    {item}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <span className="mb-2 block text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Qualita dato</span>
              <select className="form-control" value={qualityFilter} onChange={(event) => setQualityFilter(event.target.value)}>
                <option value="">Tutte</option>
                <option value="misto">Misto</option>
                <option value="reale">Reale</option>
                <option value="stimato">Stimato</option>
              </select>
            </label>
            <label>
              <span className="mb-2 block text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Ricerca</span>
              <input className="form-control" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Es. mais, medica, ortive" />
            </label>
          </div>
        </section>

        <section className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
          <article className="panel-card">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#5f7d68]">Matrice colture</p>
            <h2 className="mt-1 text-2xl font-semibold tracking-tight text-slate-950">Ruolo, consumi e rapporto costo/consumo</h2>
            <p className="mt-2 text-sm text-slate-500">Seleziona una coltura per aprire gli incroci per distretto, indice, comune e serie storica annuale.</p>
            <div className="mt-6 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
              {filteredItems.map((item) => (
                <button
                  key={item.coltura}
                  type="button"
                  onClick={() => setSelectedColtura(item.coltura)}
                  className={
                    selectedColtura === item.coltura
                      ? "rounded-3xl border border-[#1d4e35] bg-[#1d4e35] p-4 text-left text-white shadow-lg"
                      : "rounded-3xl border border-[#d7e4da] bg-white p-4 text-left text-slate-800 shadow-sm transition hover:border-[#1d4e35]"
                  }
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-lg font-semibold">{item.coltura}</p>
                      <p className="mt-1 text-xs opacity-80">{item.gruppo_coltura ?? "Gruppo non dedotto"}</p>
                    </div>
                    <span className={`rounded-full border px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.16em] ${QUALITY_STYLES[item.quality_badge] ?? QUALITY_STYLES.stimato}`}>
                      {item.quality_badge}
                    </span>
                  </div>
                  <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
                    <div>
                      <p className="opacity-70">Importo</p>
                      <p className="mt-1 font-semibold">{formatEuro(item.importo_totale)}</p>
                    </div>
                    <div>
                      <p className="opacity-70">Consumo</p>
                      <p className="mt-1 font-semibold">{formatMaybe(item.consumo_reale_mc, "mc")}</p>
                    </div>
                    <div>
                      <p className="opacity-70">Sup. irrigata</p>
                      <p className="mt-1 font-semibold">{formatMaybe(item.superficie_irrigata_ha, "ha")}</p>
                    </div>
                    <div>
                      <p className="opacity-70">€/mc</p>
                      <p className="mt-1 font-semibold">{item.euro_per_mc ? formatEuro(item.euro_per_mc) : "—"}</p>
                    </div>
                  </div>
                </button>
              ))}
            </div>
            <div className="mt-6 h-[320px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={overviewChartData} margin={{ top: 8, right: 12, left: 0, bottom: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="coltura" tickLine={false} axisLine={false} />
                  <YAxis tickLine={false} axisLine={false} />
                  <Tooltip formatter={(value, name) => [name === "importo" ? formatEuro(Number(value)) : `${formatDecimal(Number(value))} mc`, name === "importo" ? "Importo ruolo" : "Consumo reale"]} />
                  <Bar dataKey="importo" radius={[12, 12, 0, 0]}>
                    {overviewChartData.map((entry) => (
                      <Cell key={`${entry.coltura}-importo`} fill="#1d4e35" />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </article>

          <article className="panel-card">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#5f7d68]">Dettaglio coltura</p>
            <h2 className="mt-1 text-2xl font-semibold tracking-tight text-slate-950">{selectedItem?.coltura ?? "Seleziona una coltura"}</h2>
            <p className="mt-2 text-sm text-slate-500">Sintesi operativa per calcolo ruolo, consumi e copertura dati reali disponibili.</p>

            <div className="mt-5 grid gap-3 md:grid-cols-2">
              <MetricCard label="Particelle ruolo" value={selectedItem?.role_particelle_count ?? 0} sub="Particelle collegate alla coltura nell'anno" />
              <MetricCard label="Letture contatori" value={selectedItem?.meter_readings_count ?? 0} sub="Letture con coltura e consumo effettivo" />
              <MetricCard label="Importo" value={formatEuro(selectedItem?.importo_totale)} sub="Peso economico della coltura nel ruolo" />
              <MetricCard label="Consumo" value={formatMaybe(selectedItem?.consumo_reale_mc, "mc")} sub="Consumo idrico reale associato alle letture" />
              <MetricCard label="mc/ha" value={selectedItem?.mc_per_ha ? formatDecimal(selectedItem.mc_per_ha, 2) : "—"} sub="Rapporto consumo su superficie irrigata" />
              <MetricCard label="€/mc" value={selectedItem?.euro_per_mc ? formatEuro(selectedItem.euro_per_mc) : "—"} sub="Rapporto costo/consumo dell'aggregato" />
            </div>

            <div className="mt-6 h-[240px] rounded-3xl border border-[#d7e4da] bg-[#f7fbf8] p-4">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={yearSeriesData} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="anno" tickLine={false} axisLine={false} />
                  <YAxis tickLine={false} axisLine={false} />
                  <Tooltip formatter={(value, name) => [name === "importo" ? formatEuro(Number(value)) : `${formatDecimal(Number(value))} mc`, name === "importo" ? "Importo" : "Consumo"]} />
                  <Bar dataKey="consumo" fill="#1d4ed8" radius={[12, 12, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </article>
        </section>

        <section className="grid gap-6 xl:grid-cols-3">
          <article className="panel-card">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#5f7d68]">Incrocio distretto</p>
            {selectedItem ? <DataTable data={topBreakdowns(selectedItem.distretti)} columns={breakdownColumns} initialPageSize={8} /> : <EmptyState icon={SearchIcon} title="Nessun dettaglio" description="Seleziona una coltura per vedere il breakdown per distretto." />}
          </article>
          <article className="panel-card">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#5f7d68]">Incrocio indice</p>
            {selectedItem ? <DataTable data={topBreakdowns(selectedItem.indici)} columns={breakdownColumns} initialPageSize={8} /> : <EmptyState icon={SearchIcon} title="Nessun dettaglio" description="Seleziona una coltura per vedere il breakdown per indice." />}
          </article>
          <article className="panel-card">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#5f7d68]">Incrocio comune</p>
            {selectedItem ? <DataTable data={topBreakdowns(selectedItem.comuni)} columns={breakdownColumns} initialPageSize={8} /> : <EmptyState icon={SearchIcon} title="Nessun dettaglio" description="Seleziona una coltura per vedere il breakdown per comune." />}
          </article>
        </section>

        <article className="panel-card">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#5f7d68]">Particelle a ruolo</p>
              <h2 className="mt-1 text-2xl font-semibold tracking-tight text-slate-950">Drill-down catastale per coltura selezionata</h2>
              <p className="mt-2 text-sm text-slate-500">L&apos;elenco particelle usa la coltura dell&apos;ultima riga ruolo disponibile per l&apos;anno selezionato.</p>
            </div>
            <div className="rounded-2xl border border-[#d7e4da] bg-[#f7fbf8] px-4 py-3 text-sm text-slate-600">
              {loadingParticelle ? "Caricamento particelle..." : `${formatInteger(particelle.length)} righe mostrate (max 200)`}
            </div>
          </div>
          <div className="mt-6">
            {loadingOverview || loadingParticelle ? (
              <div className="rounded-2xl border border-gray-100 bg-gray-50 px-4 py-5 text-sm text-gray-500">Caricamento workspace colture...</div>
            ) : particelle.length === 0 ? (
              <EmptyState icon={SearchIcon} title="Nessuna particella trovata" description="Non risultano particelle a ruolo per la coltura e l'anno selezionati." />
            ) : (
              <DataTable data={particelle} columns={particelleColumns} initialPageSize={12} onRowClick={(row) => setSelectedParticella(row)} />
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
