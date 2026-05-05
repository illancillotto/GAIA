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

function parseCfIntestarioFilter(value: string): { cf?: string; intestatario?: string } {
  const trimmed = value.trim();
  if (!trimmed) return {};
  if (/^[A-Z0-9]{16}$/i.test(trimmed)) return { cf: trimmed.toUpperCase() };
  return { intestatario: trimmed };
}

function parseComuneFilter(value: string): { comune?: number; codiceCatastale?: string; nomeComune?: string } {
  const trimmed = value.trim();
  if (!trimmed) return {};
  if (/^\d+$/.test(trimmed)) return { comune: Number(trimmed) };
  if (/^[A-Za-z]\d{3}$/.test(trimmed)) return { codiceCatastale: trimmed.toUpperCase() };
  return { nomeComune: trimmed };
}

export default function CatastoParticellePage() {
  const [selectedParticella, setSelectedParticella] = useState<CatParticella | null>(null);
  const [filters, setFilters] = useState<{ comune: string; foglio: string; particella: string; distretto: string; cfIntestario: string }>({
    comune: "",
    foglio: "",
    particella: "",
    distretto: "",
    cfIntestario: "",
  });
  const [items, setItems] = useState<CatParticella[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void applyFilters();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function applyFilters(): Promise<void> {
    const token = getStoredAccessToken();
    if (!token) return;

    const { comune, codiceCatastale, nomeComune } = parseComuneFilter(filters.comune);
    setBusy(true);
    try {
      const data = await catastoListParticelle(token, {
        comune,
        codiceCatastale,
        nomeComune,
        foglio: filters.foglio || undefined,
        particella: filters.particella || undefined,
        distretto: filters.distretto || undefined,
        ...parseCfIntestarioFilter(filters.cfIntestario),
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
          <span className="text-sm text-gray-700">{row.original.utenza_cf ?? "—"}</span>
        ),
      },
      {
        header: "Denominazione",
        id: "utenzaDenominazione",
        cell: ({ row }) => (
          <span className="text-sm text-gray-700">{row.original.utenza_denominazione ?? "—"}</span>
        ),
      },
    ],
    [],
  );

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
              <label className="text-sm font-medium text-gray-700">
                Comune
                <input
                  className="form-control mt-1"
                  placeholder="Nome (es. Palmas Arborea), cod. Capacitas (es. 165) o Belfiore (es. G286)"
                  value={filters.comune}
                  onChange={(e) => setFilters((c) => ({ ...c, comune: e.target.value }))}
                />
              </label>
              <label className="text-sm font-medium text-gray-700">
                Foglio
                <input
                  className="form-control mt-1"
                  placeholder="Es. 5"
                  value={filters.foglio}
                  onChange={(e) => setFilters((c) => ({ ...c, foglio: e.target.value }))}
                />
              </label>
              <label className="text-sm font-medium text-gray-700">
                Particella
                <input
                  className="form-control mt-1"
                  placeholder="Es. 120"
                  value={filters.particella}
                  onChange={(e) => setFilters((c) => ({ ...c, particella: e.target.value }))}
                />
              </label>
              <label className="text-sm font-medium text-gray-700">
                Distretto
                <input
                  className="form-control mt-1"
                  placeholder="Es. 10"
                  value={filters.distretto}
                  onChange={(e) => setFilters((c) => ({ ...c, distretto: e.target.value }))}
                />
              </label>
              <label className="text-sm font-medium text-gray-700">
                Codice fiscale / Intestatario
                <input
                  className="form-control mt-1"
                  placeholder="CF (es. RSSMRA80A01H501T) o nome (es. Rossi)"
                  value={filters.cfIntestario}
                  onChange={(e) => setFilters((c) => ({ ...c, cfIntestario: e.target.value }))}
                />
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
                setFilters({ comune: "", foglio: "", particella: "", distretto: "", cfIntestario: "" });
                void applyFilters();
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
            <EmptyState icon={SearchIcon} title="Nessuna particella" description="Non ci sono particelle che corrispondono ai filtri correnti." />
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
