"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { UtenzeModulePage } from "@/components/utenze/utenze-module-page";
import { EmptyState } from "@/components/ui/empty-state";
import { CheckIcon, RefreshIcon, SearchIcon, UserIcon } from "@/components/ui/icons";
import { bulkApproveUtenzeBonificaStaging, getUtenzeBonificaStaging } from "@/lib/api";
import { formatDateTime } from "@/lib/presentation";
import type { BonificaUserStaging } from "@/types/api";

const PAGE_SIZE = 25;

function displayName(item: BonificaUserStaging): string {
  const parts = [item.last_name, item.first_name].filter(Boolean);
  if (parts.length > 0) return parts.join(" ");
  return item.business_name ?? item.username ?? item.email ?? String(item.wc_id);
}

export default function UtenzeBonificaStagingPage() {
  return (
    <UtenzeModulePage
      title="Staging consorziati"
      description="Elenco consorziati importati da WhiteCompany in staging, con import esplicito verso Utenze."
      breadcrumb="Utenze / Staging consorziati"
    >
      {({ token }) => <BonificaStagingWorkspace token={token} />}
    </UtenzeModulePage>
  );
}

function BonificaStagingWorkspace({ token }: { token: string }) {
  const [page, setPage] = useState(1);
  const [items, setItems] = useState<BonificaUserStaging[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [approving, setApproving] = useState(false);

  const totalPages = useMemo(() => Math.max(1, Math.ceil(total / PAGE_SIZE)), [total]);

  async function load(): Promise<void> {
    setLoading(true);
    try {
      const response = await getUtenzeBonificaStaging(token, { page, page_size: PAGE_SIZE });
      setItems(response.items);
      setTotal(response.total);
      setError(null);
      setSelectedIds([]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Errore caricamento staging consorziati");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page]);

  function toggleRow(id: string): void {
    setSelectedIds((current) => (current.includes(id) ? current.filter((value) => value !== id) : [...current, id]));
  }

  function toggleAll(): void {
    setSelectedIds((current) => (current.length === items.length ? [] : items.map((item) => item.id)));
  }

  async function handleBulkApprove(): Promise<void> {
    if (selectedIds.length === 0) return;
    setApproving(true);
    try {
      await bulkApproveUtenzeBonificaStaging(token, selectedIds);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Errore approvazione multipla");
    } finally {
      setApproving(false);
    }
  }

  return (
    <section className="page-body">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-sm text-gray-600">
          <UserIcon className="h-4 w-4 text-[#1D4E35]" />
          {total} record
        </div>
        <div className="flex flex-wrap gap-2">
          <button className="btn-secondary" type="button" onClick={() => void load()} disabled={loading}>
            <RefreshIcon className="mr-2 inline h-4 w-4" />
            Aggiorna
          </button>
          <button
            className="btn-primary"
            type="button"
            onClick={() => void handleBulkApprove()}
            disabled={approving || selectedIds.length === 0}
          >
            <CheckIcon className="mr-2 inline h-4 w-4" />
            {approving ? "Import in corso..." : `Importa in anagrafica (${selectedIds.length})`}
          </button>
        </div>
      </div>

      {error ? (
        <div className="mb-4 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">{error}</div>
      ) : null}

      {loading ? (
        <div className="rounded-2xl border border-gray-100 bg-white p-5 text-sm text-gray-500">Caricamento staging...</div>
      ) : items.length === 0 ? (
        <EmptyState icon={SearchIcon} title="Nessun consorziato in staging" description="Avvia una sync WhiteCompany (consorziati) per popolare lo staging." />
      ) : (
        <div className="overflow-x-auto rounded-2xl border border-gray-100 bg-white">
          <table className="data-table">
            <thead>
              <tr>
                <th>
                  <input
                    type="checkbox"
                    className="h-4 w-4 accent-[#1D4E35]"
                    checked={selectedIds.length === items.length}
                    onChange={toggleAll}
                  />
                </th>
                <th>Nome</th>
                <th>CF/PIVA</th>
                <th>Email</th>
                <th>Stato</th>
                <th>Match</th>
                <th>Sync</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id}>
                  <td>
                    <input
                      type="checkbox"
                      className="h-4 w-4 accent-[#1D4E35]"
                      checked={selectedIds.includes(item.id)}
                      onChange={() => toggleRow(item.id)}
                    />
                  </td>
                  <td className="min-w-[16rem]">
                    <Link className="font-medium text-[#1D4E35] hover:text-[#143726]" href={`/utenze/bonifica-staging/${item.id}`}>
                      {displayName(item)}
                    </Link>
                    <div className="mt-1 text-xs text-gray-400">wc_id: {item.wc_id}</div>
                  </td>
                  <td className="text-sm text-gray-600">{item.tax ?? "—"}</td>
                  <td className="text-sm text-gray-600">{item.email ?? "—"}</td>
                  <td className="text-sm text-gray-600">{item.review_status}</td>
                  <td className="text-sm text-gray-600">
                    {item.matched_subject_display_name ? (
                      <Link className="text-[#1D4E35] hover:text-[#143726]" href={`/utenze/${item.matched_subject_id}`}>
                        {item.matched_subject_display_name}
                      </Link>
                    ) : (
                      "—"
                    )}
                  </td>
                  <td className="text-sm text-gray-600">{formatDateTime(item.wc_synced_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="mt-5 flex items-center justify-between text-sm text-gray-600">
        <button className="btn-secondary" type="button" disabled={page <= 1 || loading} onClick={() => setPage((v) => Math.max(1, v - 1))}>
          Indietro
        </button>
        <span>
          Pagina {page} / {totalPages}
        </span>
        <button
          className="btn-secondary"
          type="button"
          disabled={page >= totalPages || loading}
          onClick={() => setPage((v) => Math.min(totalPages, v + 1))}
        >
          Avanti
        </button>
      </div>
    </section>
  );
}
