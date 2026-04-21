"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import type { ColumnDef } from "@tanstack/react-table";

import { CatastoPage } from "@/components/catasto/catasto-page";
import { DataTable } from "@/components/table/data-table";
import { AlertBanner } from "@/components/ui/alert-banner";
import { EmptyState } from "@/components/ui/empty-state";
import { SearchIcon } from "@/components/ui/icons";
import { TableFilters } from "@/components/table/table-filters";
import { catastoListParticelle } from "@/lib/api/catasto";
import { getStoredAccessToken } from "@/lib/auth";
import type { CatParticella } from "@/types/catasto";

function formatHaFromMq(value: string | number): string {
  const mq = typeof value === "number" ? value : Number(value);
  const ha = (Number.isFinite(mq) ? mq : 0) / 10_000;
  return new Intl.NumberFormat("it-IT", { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(ha);
}

export default function CatastoParticellePage() {
  const router = useRouter();
  const [filters, setFilters] = useState<{ comune: string; foglio: string; particella: string; distretto: string }>({
    comune: "",
    foglio: "",
    particella: "",
    distretto: "",
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

    setBusy(true);
    try {
      const data = await catastoListParticelle(token, {
        comune: filters.comune ? Number(filters.comune) : undefined,
        foglio: filters.foglio || undefined,
        particella: filters.particella || undefined,
        distretto: filters.distretto || undefined,
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
        header: "Sup. (ha)",
        id: "sup",
        cell: ({ row }) => (
          <span className="text-sm text-gray-700">
            {row.original.superficie_mq ? `${formatHaFromMq(row.original.superficie_mq)} ha` : "—"}
          </span>
        ),
      },
    ],
    [],
  );

  return (
    <CatastoPage
      title="Particelle"
      description="Lista particelle (Fase 1) con filtri principali."
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

          <div className="mt-4">
            <TableFilters>
              <label className="text-sm font-medium text-gray-700">
                Comune (cod. Capacitas)
                <input
                  className="form-control mt-1"
                  inputMode="numeric"
                  placeholder="Es. 165"
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
            </TableFilters>
          </div>

          <div className="mt-4 flex flex-wrap items-center gap-3">
            <button className="btn-primary" type="button" disabled={busy} onClick={() => void applyFilters()}>
              {busy ? "Ricerca…" : "Applica filtri"}
            </button>
            <button
              className="btn-secondary"
              type="button"
              disabled={busy}
              onClick={() => {
                setFilters({ comune: "", foglio: "", particella: "", distretto: "" });
                void applyFilters();
              }}
            >
              Reset
            </button>
            <p className="text-sm text-gray-500">{busy ? "Caricamento…" : `${items.length} righe (max 200)`}</p>
          </div>
        </article>

        <article className="panel-card">
          {busy && items.length === 0 ? (
            <div className="rounded-xl border border-gray-100 bg-gray-50 p-4 text-sm text-gray-500">Caricamento…</div>
          ) : items.length === 0 ? (
            <EmptyState icon={SearchIcon} title="Nessuna particella" description="Non ci sono particelle che corrispondono ai filtri correnti." />
          ) : (
            <DataTable data={items} columns={columns} initialPageSize={12} onRowClick={(row) => router.push(`/catasto/particelle/${row.id}`)} />
          )}
        </article>
      </div>
    </CatastoPage>
  );
}
