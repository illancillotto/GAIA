"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";

import { ElaborazionePanelHeader } from "@/components/elaborazioni/module-chrome";
import { EmptyState } from "@/components/ui/empty-state";
import { UserIcon } from "@/components/ui/icons";
import { getStepContribuente, listStepContribuenti } from "@/lib/api";
import type { StepContribuenteDetail, StepContribuenteRow, StepPage } from "@/types/step";

import { StepContribuenteDetailPanel } from "./step-contribuente-detail";
import { formatEuro } from "./step-format";

const PAGE_SIZE = 25;

type PanelProps = { token: string; onError: (message: string) => void };

function ContribuentiTable({ rows, selectedId, onSelect }: { rows: StepContribuenteRow[]; selectedId: string | null; onSelect: (id: string) => void }) {
  return (
    <table className="min-w-full divide-y divide-gray-200 text-sm">
      <thead className="bg-gray-50 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
        <tr>
          <th className="px-3 py-2">Contribuente</th>
          <th className="px-3 py-2">Documenti</th>
          <th className="px-3 py-2 text-right">Residuo</th>
        </tr>
      </thead>
      <tbody className="divide-y divide-gray-100">
        {rows.map((row) => (
          <tr key={row.id} className={row.id === selectedId ? "bg-[#eef7f1]" : undefined}>
            <td className="px-3 py-2">
              <button className="text-left font-medium text-[#1D4E35] hover:underline" onClick={() => onSelect(row.id)} type="button">
                {row.denominazione ?? row.codice_fiscale}
              </button>
              <p className="text-xs text-gray-500">{row.codice_fiscale}</p>
            </td>
            <td className="px-3 py-2 text-gray-600">
              {row.numero_documenti ?? "—"} · {row.stato_documenti ?? "—"}
            </td>
            <td className="px-3 py-2 text-right">{formatEuro(row.residuo)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function Pager({ page, total, onPage }: { page: number; total: number; onPage: (page: number) => void }) {
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  return (
    <div className="flex items-center justify-between text-sm text-gray-600">
      <span>
        {total} contribuenti · pagina {page} di {pages}
      </span>
      <div className="flex gap-2">
        <button className="btn-secondary" disabled={page <= 1} onClick={() => onPage(page - 1)} type="button">
          Precedente
        </button>
        <button className="btn-secondary" disabled={page >= pages} onClick={() => onPage(page + 1)} type="button">
          Successiva
        </button>
      </div>
    </div>
  );
}

export function StepContribuentiPanel({ token, onError }: PanelProps) {
  const [search, setSearch] = useState({ q: "", onlyResiduo: false, page: 1 });
  const [draft, setDraft] = useState("");
  const [data, setData] = useState<StepPage<StepContribuenteRow> | null>(null);
  const [detail, setDetail] = useState<StepContribuenteDetail | null>(null);

  const load = useCallback(async () => {
    try {
      setData(await listStepContribuenti(token, { q: search.q, onlyResiduo: search.onlyResiduo, page: search.page, pageSize: PAGE_SIZE }));
    } catch (error) {
      onError(error instanceof Error ? error.message : "Errore caricamento contribuenti STEP");
    }
  }, [token, search, onError]);

  useEffect(() => {
    void load();
  }, [load]);

  async function select(id: string): Promise<void> {
    try {
      setDetail(await getStepContribuente(token, id));
    } catch (error) {
      onError(error instanceof Error ? error.message : "Errore caricamento scheda STEP");
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault();
    setSearch({ ...search, q: draft.trim(), page: 1 });
  }

  return (
    <section className="overflow-hidden rounded-[24px] border border-[#d9dfd6] bg-white shadow-sm">
      <ElaborazionePanelHeader badge="Archivio" title="Contribuenti STEP" description="Copia in sola lettura delle schede STEP. Gli importi STEP non sono pagamenti GAIA." />
      <div className="grid gap-6 p-6 xl:grid-cols-[1fr,1.1fr]">
        <div className="space-y-4">
          <form className="flex flex-wrap gap-2" onSubmit={handleSubmit}>
            <input aria-label="Cerca contribuente" className="input flex-1" onChange={(event) => setDraft(event.target.value)} placeholder="Codice fiscale o denominazione" value={draft} />
            <button className="btn-secondary" type="submit">
              Cerca
            </button>
            <label className="flex items-center gap-2 text-sm text-gray-700">
              <input checked={search.onlyResiduo} onChange={(event) => setSearch({ ...search, onlyResiduo: event.target.checked, page: 1 })} type="checkbox" />
              Solo con residuo
            </label>
          </form>
          {data && data.items.length > 0 ? (
            <>
              <ContribuentiTable onSelect={(id) => void select(id)} rows={data.items} selectedId={detail?.id ?? null} />
              <Pager onPage={(page) => setSearch({ ...search, page })} page={data.page} total={data.total} />
            </>
          ) : (
            <EmptyState icon={UserIcon} title="Nessun contribuente" description="Importa un archivio o avvia una sincronizzazione STEP." />
          )}
        </div>
        <div>{detail ? <StepContribuenteDetailPanel detail={detail} onError={onError} token={token} /> : <p className="text-sm text-gray-500">Seleziona un contribuente per vedere documenti, tributi, collegamenti al ruolo e pagamenti.</p>}</div>
      </div>
    </section>
  );
}
