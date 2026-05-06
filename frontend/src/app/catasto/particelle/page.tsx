"use client";

import { useEffect, useMemo, useState } from "react";
import type { ColumnDef } from "@tanstack/react-table";

import { CatastoPage } from "@/components/catasto/catasto-page";
import { ParticellaDetailDialog } from "@/components/catasto/anagrafica/ParticellaDetailDialog";
import { DataTable } from "@/components/table/data-table";
import { AlertBanner } from "@/components/ui/alert-banner";
import { EmptyState } from "@/components/ui/empty-state";
import { SearchIcon } from "@/components/ui/icons";
import { TableFilters } from "@/components/table/table-filters";
import { catastoListParticelle } from "@/lib/api/catasto";
import { getStoredAccessToken } from "@/lib/auth";
import type { CatAnagraficaMatch, CatParticella } from "@/types/catasto";

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

function formatHaFromMq(value: string | number): string {
  const mq = typeof value === "number" ? value : Number(value);
  const ha = (Number.isFinite(mq) ? mq : 0) / 10_000;
  return new Intl.NumberFormat("it-IT", { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(ha);
}

function parseComuneFilter(value: string): { comune?: number; codiceCatastale?: string; nomeComune?: string } {
  const trimmed = value.trim();
  if (!trimmed) return {};
  if (/^\d+$/.test(trimmed)) return { comune: Number(trimmed) };
  if (/^[A-Za-z]\d{3}$/.test(trimmed)) return { codiceCatastale: trimmed.toUpperCase() };
  return { nomeComune: trimmed };
}

function parseCfIntestatarioFilter(value: string): { cf?: string; search?: string } {
  const trimmed = value.trim();
  if (!trimmed) return {};
  if (/^[A-Z0-9]{16}$/i.test(trimmed)) return { cf: trimmed.toUpperCase() };
  if (/^\d{11}$/.test(trimmed)) return { cf: trimmed };
  return { search: trimmed };
}

export default function CatastoParticellePage() {
  const [selectedParticella, setSelectedParticella] = useState<CatParticella | null>(null);
  const [filters, setFilters] = useState<{
    comune: string;
    foglio: string;
    particella: string;
    distretto: string;
    cfIntestario: string;
    soloConAnagrafica: boolean;
    soloARuolo: boolean;
  }>({
    comune: "",
    foglio: "",
    particella: "",
    distretto: "",
    cfIntestario: "",
    soloConAnagrafica: true,
    soloARuolo: false,
  });
  const [items, setItems] = useState<CatParticella[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void applyFilters();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function applyFilters(nextFilters = filters): Promise<void> {
    const token = getStoredAccessToken();
    if (!token) return;

    const { comune, codiceCatastale, nomeComune } = parseComuneFilter(nextFilters.comune);
    const { cf, search } = parseCfIntestatarioFilter(nextFilters.cfIntestario);
    setBusy(true);
    try {
      const data = await catastoListParticelle(token, {
        comune,
        codiceCatastale,
        nomeComune,
        foglio: nextFilters.foglio || undefined,
        particella: nextFilters.particella || undefined,
        distretto: nextFilters.distretto || undefined,
        cf,
        search,
        soloConAnagrafica: nextFilters.soloConAnagrafica,
        soloARuolo: nextFilters.soloARuolo,
        limit: 200,
      });
      setItems(data);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Errore caricamento particelle");
    } finally {
      setBusy(false);
    }
  }

  const columns = useMemo<ColumnDef<CatParticella>[]>(
    () => [
      {
        header: "Comune",
        accessorKey: "nome_comune",
        cell: ({ row }) => (
          <div>
            <p className="text-sm font-medium text-gray-900">{row.original.nome_comune ?? row.original.cod_comune_capacitas}</p>
            <p className="text-xs text-gray-400">Codice Capacitas {row.original.cod_comune_capacitas}</p>
          </div>
        ),
      },
      {
        header: "Riferimento",
        id: "rif",
        cell: ({ row }) => (
          <span className="text-sm text-gray-700">
            Fg.{row.original.foglio} Part.{row.original.particella}
            {row.original.subalterno ? ` Sub.${row.original.subalterno}` : ""}
          </span>
        ),
      },
      {
        header: "Distretto",
        accessorKey: "num_distretto",
        cell: ({ row }) => <span className="text-sm text-gray-700">{row.original.num_distretto ?? "—"}</span>,
      },
      {
        header: "Sup. catastale (ha)",
        id: "supCatastale",
        cell: ({ row }) => (
          <span className="text-sm text-gray-700">
            {row.original.superficie_mq ? `${formatHaFromMq(row.original.superficie_mq)} ha` : "—"}
          </span>
        ),
      },
      {
        header: "Sup. grafica (ha)",
        id: "supGrafica",
        cell: ({ row }) => (
          <span className="text-sm text-gray-700">
            {row.original.superficie_grafica_mq ? `${formatHaFromMq(row.original.superficie_grafica_mq)} ha` : "—"}
          </span>
        ),
      },
      {
        header: "CF / P.IVA",
        id: "utenzaCf",
        cell: ({ row }) => (
          <span className={`text-sm ${row.original.ha_anagrafica ? "text-gray-700" : "font-medium text-[#9f1239]"}`}>
            {row.original.utenza_cf ?? (row.original.ha_anagrafica ? "—" : "Senza anagrafica")}
          </span>
        ),
      },
      {
        header: "Denominazione",
        id: "utenzaDenominazione",
        cell: ({ row }) => (
          row.original.ha_anagrafica ? (
            <span className="text-sm text-gray-700">{row.original.utenza_denominazione ?? "—"}</span>
          ) : (
            <div className="space-y-1">
              <span className="inline-flex rounded-full bg-[#fff1f2] px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-[#9f1239] ring-1 ring-[#fecdd3]">
                Senza anagrafica
              </span>
              <p className="text-xs text-[#7f1d1d]">Particella trovata, ma senza anagrafica collegata.</p>
            </div>
          )
        ),
      },
    ],
    [],
  );

  const emptyDescription = filters.soloARuolo
    ? "Non ci sono particelle collegate al ruolo per i filtri correnti. Se il risultato resta vuoto anche senza altri filtri, verifica che l'archivio Ruolo sia stato importato e collegato al Catasto."
    : filters.soloConAnagrafica
      ? "Non ci sono particelle con anagrafica per i filtri correnti. Disattiva il filtro se vuoi vedere anche le particelle senza anagrafica collegata."
      : "Non ci sono particelle che corrispondono ai filtri correnti.";

  return (
    <CatastoPage
      title="Particelle"
      description="Lista particelle del dominio Catasto con filtri principali."
      breadcrumb="Catasto / Particelle"
      requiredModule="catasto"
    >
      <div className="page-stack">
        {error ? (
          <AlertBanner variant="danger" title="Errore caricamento">
            {error}
          </AlertBanner>
        ) : null}

        <article className="panel-card">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-sm font-medium text-gray-900">Filtri</p>
              <p className="mt-1 text-sm text-gray-500">I filtri attuali sono applicati su particelle correnti (`is_current=true`).</p>
            </div>
          </div>

          <form
            className="mt-4"
            onSubmit={(e) => {
              e.preventDefault();
              void applyFilters();
            }}
          >
            <TableFilters>
              <label className="rounded-[22px] border border-[#d7e4da] bg-[radial-gradient(circle_at_top_left,_rgba(29,78,53,0.06),_transparent_40%),linear-gradient(135deg,#f8fbf9,#ffffff)] px-4 py-3 text-sm font-medium text-gray-700 shadow-sm transition hover:border-[#b7cbbd] hover:shadow">
                <span className="block text-[11px] font-semibold uppercase tracking-[0.16em] text-[#52715d]">Comune</span>
                <input
                  className="form-control mt-2 border-white/0 bg-white/80"
                  placeholder="Nome (es. Palmas Arborea), cod. Capacitas (es. 165) o Belfiore (es. G286)"
                  value={filters.comune}
                  onChange={(e) => setFilters((c) => ({ ...c, comune: e.target.value }))}
                />
              </label>
              <label className="rounded-[22px] border border-[#d7e4da] bg-[radial-gradient(circle_at_top_left,_rgba(29,78,53,0.06),_transparent_40%),linear-gradient(135deg,#f8fbf9,#ffffff)] px-4 py-3 text-sm font-medium text-gray-700 shadow-sm transition hover:border-[#b7cbbd] hover:shadow">
                <span className="block text-[11px] font-semibold uppercase tracking-[0.16em] text-[#52715d]">Foglio</span>
                <input
                  className="form-control mt-2 border-white/0 bg-white/80"
                  placeholder="Es. 5"
                  value={filters.foglio}
                  onChange={(e) => setFilters((c) => ({ ...c, foglio: e.target.value }))}
                />
              </label>
              <label className="rounded-[22px] border border-[#d7e4da] bg-[radial-gradient(circle_at_top_left,_rgba(29,78,53,0.06),_transparent_40%),linear-gradient(135deg,#f8fbf9,#ffffff)] px-4 py-3 text-sm font-medium text-gray-700 shadow-sm transition hover:border-[#b7cbbd] hover:shadow">
                <span className="block text-[11px] font-semibold uppercase tracking-[0.16em] text-[#52715d]">Particella</span>
                <input
                  className="form-control mt-2 border-white/0 bg-white/80"
                  placeholder="Es. 120"
                  value={filters.particella}
                  onChange={(e) => setFilters((c) => ({ ...c, particella: e.target.value }))}
                />
              </label>
              <label className="rounded-[22px] border border-[#d7e4da] bg-[radial-gradient(circle_at_top_left,_rgba(29,78,53,0.06),_transparent_40%),linear-gradient(135deg,#f8fbf9,#ffffff)] px-4 py-3 text-sm font-medium text-gray-700 shadow-sm transition hover:border-[#b7cbbd] hover:shadow">
                <span className="block text-[11px] font-semibold uppercase tracking-[0.16em] text-[#52715d]">Distretto</span>
                <input
                  className="form-control mt-2 border-white/0 bg-white/80"
                  placeholder="Es. 10"
                  value={filters.distretto}
                  onChange={(e) => setFilters((c) => ({ ...c, distretto: e.target.value }))}
                />
              </label>
              <label className="rounded-[22px] border border-[#d7e4da] bg-[radial-gradient(circle_at_top_left,_rgba(29,78,53,0.06),_transparent_40%),linear-gradient(135deg,#f8fbf9,#ffffff)] px-4 py-3 text-sm font-medium text-gray-700 shadow-sm transition hover:border-[#b7cbbd] hover:shadow">
                <span className="block text-[11px] font-semibold uppercase tracking-[0.16em] text-[#52715d]">Codice fiscale / Intestatario</span>
                <input
                  className="form-control mt-2 border-white/0 bg-white/80"
                  placeholder="CF/P.IVA (es. RSSMRA80A01H501T o 00588230953) o nome (es. Rossi)"
                  value={filters.cfIntestario}
                  onChange={(e) => setFilters((c) => ({ ...c, cfIntestario: e.target.value }))}
                />
              </label>
              <label className="group flex items-center justify-between gap-4 rounded-[22px] border border-[#d7e4da] bg-[radial-gradient(circle_at_top_left,_rgba(29,78,53,0.08),_transparent_46%),linear-gradient(135deg,#f7fbf8,#ffffff)] px-4 py-3 text-sm text-gray-700 shadow-sm transition hover:border-[#b7cbbd] hover:shadow">
                <div>
                  <div className="flex items-center gap-2">
                    <p className="font-medium text-gray-900">Solo particelle con anagrafica</p>
                    <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.14em] ${filters.soloConAnagrafica ? "bg-[#1D4E35] text-white" : "bg-white text-gray-500 ring-1 ring-gray-200"}`}>
                      {filters.soloConAnagrafica ? "Attivo" : "Off"}
                    </span>
                  </div>
                  <p className="mt-0.5 text-xs text-gray-500">All&apos;apertura mostra solo le particelle che hanno anagrafica. Se cerchi una particella specifica, la vedi comunque anche se manca l&apos;anagrafica.</p>
                </div>
                <input
                  aria-label="Visualizza solo particelle con anagrafica"
                  checked={filters.soloConAnagrafica}
                  className="peer sr-only"
                  type="checkbox"
                  onChange={(e) => {
                    const nextFilters = { ...filters, soloConAnagrafica: e.target.checked };
                    setFilters(nextFilters);
                    void applyFilters(nextFilters);
                  }}
                />
                <span className="relative inline-flex h-8 w-14 shrink-0 items-center rounded-full bg-gray-300 transition peer-checked:bg-[#1D4E35] peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-[#1D4E35]/25 group-hover:bg-gray-400/80 peer-checked:group-hover:bg-[#255c41]">
                  <span
                    className={`absolute left-1 flex h-6 w-6 items-center justify-center rounded-full bg-white shadow-sm transition-transform ${
                      filters.soloConAnagrafica ? "translate-x-6" : "translate-x-0"
                    }`}
                  >
                    <span className={`h-2 w-2 rounded-full ${filters.soloConAnagrafica ? "bg-[#1D4E35]" : "bg-gray-300"}`} />
                  </span>
                </span>
              </label>
              <label className="group flex items-center justify-between gap-4 rounded-[22px] border border-[#d7e4da] bg-[radial-gradient(circle_at_top_left,_rgba(29,78,53,0.08),_transparent_46%),linear-gradient(135deg,#f7fbf8,#ffffff)] px-4 py-3 text-sm text-gray-700 shadow-sm transition hover:border-[#b7cbbd] hover:shadow">
                <div>
                  <div className="flex items-center gap-2">
                    <p className="font-medium text-gray-900">Solo particelle a ruolo</p>
                    <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.14em] ${filters.soloARuolo ? "bg-[#1D4E35] text-white" : "bg-white text-gray-500 ring-1 ring-gray-200"}`}>
                      {filters.soloARuolo ? "Attivo" : "Off"}
                    </span>
                  </div>
                  <p className="mt-0.5 text-xs text-gray-500">Mostra solo le particelle collegate al ruolo consortile. Se per i filtri attivi non esistono righe nell&apos;anno piu recente, usa automaticamente l&apos;anno precedente.</p>
                </div>
                <input
                  aria-label="Visualizza solo particelle a ruolo"
                  checked={filters.soloARuolo}
                  className="peer sr-only"
                  type="checkbox"
                  onChange={(e) => {
                    const nextFilters = { ...filters, soloARuolo: e.target.checked };
                    setFilters(nextFilters);
                    void applyFilters(nextFilters);
                  }}
                />
                <span className="relative inline-flex h-8 w-14 shrink-0 items-center rounded-full bg-gray-300 transition peer-checked:bg-[#1D4E35] peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-[#1D4E35]/25 group-hover:bg-gray-400/80 peer-checked:group-hover:bg-[#255c41]">
                  <span
                    className={`absolute left-1 flex h-6 w-6 items-center justify-center rounded-full bg-white shadow-sm transition-transform ${
                      filters.soloARuolo ? "translate-x-6" : "translate-x-0"
                    }`}
                  >
                    <span className={`h-2 w-2 rounded-full ${filters.soloARuolo ? "bg-[#1D4E35]" : "bg-gray-300"}`} />
                  </span>
                </span>
              </label>
            </TableFilters>

            <div className="mt-4 flex flex-wrap items-center gap-3">
            <button className="btn-primary" type="submit" disabled={busy}>
              {busy ? "Ricerca…" : "Applica filtri"}
            </button>
            <button
              className="btn-secondary"
              type="button"
              disabled={busy}
              onClick={() => {
                const resetFilters = {
                  comune: "",
                  foglio: "",
                  particella: "",
                  distretto: "",
                  cfIntestario: "",
                  soloConAnagrafica: true,
                  soloARuolo: false,
                };
                setFilters(resetFilters);
                void applyFilters(resetFilters);
              }}
            >
              Reset
            </button>
            <p className="text-sm text-gray-500">{busy ? "Caricamento…" : `${items.length} righe (max 200)`}</p>
          </div>
          </form>
        </article>

        <article className="panel-card">
          {busy && items.length === 0 ? (
            <div className="rounded-xl border border-gray-100 bg-gray-50 p-4 text-sm text-gray-500">Caricamento…</div>
          ) : items.length === 0 ? (
            <EmptyState icon={SearchIcon} title="Nessuna particella" description={emptyDescription} />
          ) : (
            <DataTable data={items} columns={columns} initialPageSize={12} onRowClick={(row) => setSelectedParticella(row)} />
          )}
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
