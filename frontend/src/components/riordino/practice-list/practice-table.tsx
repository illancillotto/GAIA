"use client";

import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import type { ColumnDef } from "@tanstack/react-table";

import { DataTable } from "@/components/table/data-table";
import { RiordinoStatusBadge } from "@/components/riordino/shared/status-badge";
import { listRiordinoPractices } from "@/lib/riordino-api";
import type { RiordinoPractice } from "@/types/riordino";

type PracticeRow = RiordinoPractice;

export function RiordinoPracticeTable({ token }: { token: string }) {
  const router = useRouter();
  const [items, setItems] = useState<RiordinoPractice[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      try {
        const response = await listRiordinoPractices(token, { per_page: "100" });
        setItems(response.items);
        setLoadError(null);
      } catch (error) {
        setLoadError(error instanceof Error ? error.message : "Errore nel caricamento pratiche");
      }
    }

    void loadData();
  }, [token]);

  const columns = useMemo<ColumnDef<PracticeRow>[]>(
    () => [
      {
        header: "Codice",
        accessorKey: "code",
        cell: ({ row }) => <span className="font-medium text-[#1D4E35]">{row.original.code}</span>,
      },
      {
        header: "Titolo",
        accessorKey: "title",
      },
      {
        header: "Comune",
        accessorKey: "municipality",
      },
      {
        header: "Maglia/Lotto",
        cell: ({ row }) => <span>{row.original.grid_code} / {row.original.lot_code}</span>,
      },
      {
        header: "Fase",
        accessorKey: "current_phase",
        cell: ({ row }) => <RiordinoStatusBadge value={row.original.current_phase} />,
      },
      {
        header: "Stato",
        accessorKey: "status",
        cell: ({ row }) => <RiordinoStatusBadge value={row.original.status} />,
      },
    ],
    [],
  );

  return (
    <article className="panel-card">
      <div className="mb-4">
        <p className="section-title">Pratiche riordino</p>
        <p className="section-copy">Elenco delle pratiche disponibili nel modulo.</p>
      </div>
      {loadError ? <p className="mb-4 text-sm text-red-600">{loadError}</p> : null}
      <DataTable
        data={items}
        columns={columns}
        onRowClick={(row) => router.push(`/riordino/pratiche/${row.id}`)}
        emptyTitle="Nessuna pratica"
        emptyDescription="Non risultano pratiche di riordino disponibili."
      />
    </article>
  );
}
