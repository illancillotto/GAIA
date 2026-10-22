"use client";

import { useCallback, useEffect, useState } from "react";

import { ElaborazionePanelHeader } from "@/components/elaborazioni/module-chrome";
import { EmptyState } from "@/components/ui/empty-state";
import { CheckIcon } from "@/components/ui/icons";
import { listStepLinkAnomalies } from "@/lib/api";
import type { StepLinkAnomaly, StepLinkStatus, StepPage } from "@/types/step";

import { LINK_STATUS_LABELS, formatEuro } from "./step-format";

const PAGE_SIZE = 50;

type PanelProps = { token: string; onError: (message: string) => void };

function AnomaliesTable({ items }: { items: StepLinkAnomaly[] }) {
  return (
    <table className="min-w-full divide-y divide-gray-200 text-sm">
      <thead className="bg-gray-50 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
        <tr>
          <th className="px-3 py-2">Contribuente</th>
          <th className="px-3 py-2">Documento</th>
          <th className="px-3 py-2">Riferimento STEP</th>
          <th className="px-3 py-2">Esito</th>
          <th className="px-3 py-2 text-right">Carico</th>
        </tr>
      </thead>
      <tbody className="divide-y divide-gray-100">
        {items.map((item) => (
          <tr key={item.id}>
            <td className="px-3 py-2">
              {item.denominazione ?? "—"}
              <p className="text-xs text-gray-500">{item.codice_fiscale}</p>
            </td>
            <td className="px-3 py-2 text-gray-600">{item.num_doc}</td>
            <td className="px-3 py-2 text-gray-600">
              {item.reference_key}
              {item.anno_rif ? ` (${item.anno_rif})` : ""}
            </td>
            <td className="px-3 py-2">{LINK_STATUS_LABELS[item.status]}</td>
            <td className="px-3 py-2 text-right">{formatEuro(item.imp_carico)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export function StepLinkAnomaliesPanel({ token, onError }: PanelProps) {
  const [status, setStatus] = useState<StepLinkStatus | "">("");
  const [page, setPage] = useState(1);
  const [data, setData] = useState<StepPage<StepLinkAnomaly> | null>(null);

  const load = useCallback(async () => {
    try {
      setData(await listStepLinkAnomalies(token, { status, page, pageSize: PAGE_SIZE }));
    } catch (error) {
      onError(error instanceof Error ? error.message : "Errore caricamento anomalie STEP");
    }
  }, [token, status, page, onError]);

  useEffect(() => {
    void load();
  }, [load]);

  const pages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;

  return (
    <section className="overflow-hidden rounded-[24px] border border-[#d9dfd6] bg-white shadow-sm">
      <ElaborazionePanelHeader
        badge="Ruolo"
        title="Collegamenti da verificare"
        description="Riferimenti avviso STEP senza un avviso GAIA univoco. Il collegamento usa solo il codice avviso: nessun abbinamento per codice fiscale, nome o importo."
      />
      <div className="space-y-4 p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <select
            aria-label="Esito collegamento"
            className="input max-w-xs"
            onChange={(event) => {
              setStatus(event.target.value as StepLinkStatus | "");
              setPage(1);
            }}
            value={status}
          >
            <option value="">Tutti i non collegati</option>
            <option value="not_found">{LINK_STATUS_LABELS.not_found}</option>
            <option value="ambiguous">{LINK_STATUS_LABELS.ambiguous}</option>
            <option value="unrecognized">{LINK_STATUS_LABELS.unrecognized}</option>
            <option value="linked">{LINK_STATUS_LABELS.linked}</option>
          </select>
          <div className="flex items-center gap-2 text-sm text-gray-600">
            <span>
              {data?.total ?? 0} righe · pagina {page} di {pages}
            </span>
            <button className="btn-secondary" disabled={page <= 1} onClick={() => setPage(page - 1)} type="button">
              Precedente
            </button>
            <button className="btn-secondary" disabled={page >= pages} onClick={() => setPage(page + 1)} type="button">
              Successiva
            </button>
          </div>
        </div>
        {data && data.items.length > 0 ? (
          <div className="overflow-x-auto">
            <AnomaliesTable items={data.items} />
          </div>
        ) : (
          <EmptyState icon={CheckIcon} title="Nessuna riga" description="Nessun collegamento con questo esito." />
        )}
      </div>
    </section>
  );
}
