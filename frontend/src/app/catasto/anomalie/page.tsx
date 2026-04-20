"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import type { ColumnDef } from "@tanstack/react-table";

import { ProtectedPage } from "@/components/app/protected-page";
import { CatastoPhase1Nav } from "@/components/catasto/phase1-nav";
import { AnomaliaStatusBadge } from "@/components/catasto/AnomaliaStatusBadge";
import { AnomaliaStatusPill } from "@/components/catasto/AnomaliaStatusPill";
import { DataTable } from "@/components/table/data-table";
import { TableFilters } from "@/components/table/table-filters";
import { AlertBanner } from "@/components/ui/alert-banner";
import { EmptyState } from "@/components/ui/empty-state";
import { SearchIcon } from "@/components/ui/icons";
import { catastoListAnomalie, catastoUpdateAnomalia } from "@/lib/api/catasto";
import { getStoredAccessToken } from "@/lib/auth";
import type { CatAnomalia } from "@/types/catasto";

function currentYear(): number {
  return new Date().getFullYear();
}

export default function CatastoAnomaliePage() {
  const [filters, setFilters] = useState<{ tipo: string; severita: string; status: string; anno: string }>({
    tipo: "",
    severita: "",
    status: "aperta",
    anno: String(currentYear()),
  });
  const [items, setItems] = useState<CatAnomalia[]>([]);
  const [total, setTotal] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (): Promise<void> => {
    const token = getStoredAccessToken();
    if (!token) return;

    setBusy(true);
    try {
      const data = await catastoListAnomalie(token, {
        tipo: filters.tipo || undefined,
        severita: filters.severita || undefined,
        status: filters.status || undefined,
        anno: filters.anno ? Number(filters.anno) : undefined,
        page: 1,
        pageSize: 200,
      });
      setItems(data.items);
      setTotal(data.total);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Errore caricamento anomalie");
    } finally {
      setBusy(false);
    }
  }, [filters.anno, filters.severita, filters.status, filters.tipo]);

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const columns = useMemo<ColumnDef<CatAnomalia>[]>(
    () => [
      {
        header: "Severità",
        accessorKey: "severita",
        cell: ({ row }) => <AnomaliaStatusBadge severita={row.original.severita} />,
      },
      {
        header: "Tipo",
        accessorKey: "tipo",
        cell: ({ row }) => <span className="text-sm font-medium text-gray-900">{row.original.tipo}</span>,
      },
      {
        header: "Stato",
        accessorKey: "status",
        cell: ({ row }) => <AnomaliaStatusPill status={row.original.status} />,
      },
      {
        header: "Descrizione",
        accessorKey: "descrizione",
        cell: ({ row }) => <span className="text-sm text-gray-600">{row.original.descrizione ?? "—"}</span>,
      },
      {
        header: "Anno",
        accessorKey: "anno_campagna",
        cell: ({ row }) => <span className="text-sm text-gray-600">{row.original.anno_campagna ?? "—"}</span>,
      },
      {
        header: "Dettagli",
        id: "details",
        cell: ({ row }) => (
          <span className="text-xs text-gray-400">
            {row.original.particella_id ? "Particella" : "—"}{row.original.utenza_id ? " · Utenza" : ""}
          </span>
        ),
      },
      {
        header: "Azioni",
        id: "actions",
        cell: ({ row }) => (
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              className="btn-secondary !px-2 !py-1 text-xs"
              disabled={busy}
              onClick={async () => {
                const token = getStoredAccessToken();
                if (!token) return;
                await catastoUpdateAnomalia(token, row.original.id, { status: "chiusa" });
                await load();
              }}
            >
              Chiudi
            </button>
            <button
              type="button"
              className="btn-secondary !px-2 !py-1 text-xs"
              disabled={busy}
              onClick={async () => {
                const token = getStoredAccessToken();
                if (!token) return;
                await catastoUpdateAnomalia(token, row.original.id, { status: "ignora" });
                await load();
              }}
            >
              Ignora
            </button>
            <button
              type="button"
              className="btn-secondary !px-2 !py-1 text-xs"
              disabled={busy}
              onClick={async () => {
                const token = getStoredAccessToken();
                if (!token) return;
                await catastoUpdateAnomalia(token, row.original.id, { status: "aperta" });
                await load();
              }}
            >
              Riapri
            </button>
          </div>
        ),
      },
    ],
    [busy, load],
  );

  return (
    <ProtectedPage
      title="Anomalie"
      description="Lista anomalie (Fase 1) con filtri principali."
      breadcrumb="Catasto / Anomalie"
      requiredModule="catasto"
    >
      <div className="page-stack">
        <CatastoPhase1Nav />

        {error ? (
          <AlertBanner variant="danger" title="Errore caricamento">
            {error}
          </AlertBanner>
        ) : null}

        <article className="panel-card">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-sm font-medium text-gray-900">Filtri</p>
              <p className="mt-1 text-sm text-gray-500">I risultati sono limitati a max 200 righe (UI). Usa `tipo` per restringere.</p>
            </div>
            <Link className="text-sm font-medium text-[#1D4E35] underline underline-offset-2" href="/catasto/import">
              Import & report
            </Link>
          </div>

          <div className="mt-4">
            <TableFilters>
              <label className="text-sm font-medium text-gray-700">
                Tipo
                <input className="form-control mt-1" value={filters.tipo} onChange={(e) => setFilters((c) => ({ ...c, tipo: e.target.value }))} placeholder="Es. VAL-02-cf_invalido" />
              </label>
              <label className="text-sm font-medium text-gray-700">
                Severità
                <select className="form-control mt-1" value={filters.severita} onChange={(e) => setFilters((c) => ({ ...c, severita: e.target.value }))}>
                  <option value="">Tutte</option>
                  <option value="error">Error</option>
                  <option value="warning">Warning</option>
                  <option value="info">Info</option>
                </select>
              </label>
              <label className="text-sm font-medium text-gray-700">
                Stato
                <select className="form-control mt-1" value={filters.status} onChange={(e) => setFilters((c) => ({ ...c, status: e.target.value }))}>
                  <option value="">Tutti</option>
                  <option value="aperta">Aperta</option>
                  <option value="chiusa">Chiusa</option>
                  <option value="ignora">Ignorata</option>
                </select>
              </label>
              <label className="text-sm font-medium text-gray-700">
                Anno
                <input className="form-control mt-1" inputMode="numeric" value={filters.anno} onChange={(e) => setFilters((c) => ({ ...c, anno: e.target.value }))} />
              </label>
            </TableFilters>
          </div>

          <div className="mt-4 flex flex-wrap items-center gap-3">
            <button className="btn-primary" type="button" disabled={busy} onClick={() => void load()}>
              {busy ? "Caricamento…" : "Applica filtri"}
            </button>
            <button
              className="btn-secondary"
              type="button"
              disabled={busy}
              onClick={() => {
                setFilters({ tipo: "", severita: "", status: "aperta", anno: String(currentYear()) });
                void load();
              }}
            >
              Reset
            </button>
            <p className="text-sm text-gray-500">{busy ? "…" : `${items.length} righe (totale backend: ${total})`}</p>
          </div>
        </article>

        <article className="panel-card">
          {busy && items.length === 0 ? (
            <div className="rounded-xl border border-gray-100 bg-gray-50 p-4 text-sm text-gray-500">Caricamento…</div>
          ) : items.length === 0 ? (
            <EmptyState icon={SearchIcon} title="Nessuna anomalia" description="Non ci sono anomalie che corrispondono ai filtri correnti." />
          ) : (
            <DataTable data={items} columns={columns} initialPageSize={12} />
          )}
        </article>

      </div>
    </ProtectedPage>
  );
}

