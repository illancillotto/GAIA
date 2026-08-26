"use client";

import { Children, useEffect, useState } from "react";

import {
  listGisAuditLogs,
  listGisCatalogLayerExports,
  listGisShapefileImports,
} from "@/lib/api/gis";
import type {
  GisAuditLog,
  GisCatalogLayer,
  GisCatalogLayerExport,
  GisShapefileImport,
} from "@/types/gis";

const importStatusLabels: Record<string, string> = {
  uploaded: "Caricato",
  validated: "Pronto da controllare",
  rejected: "Rigettato",
  published: "Pubblicato",
  failed: "Fallito",
};

function readableDate(value: string): string {
  return new Intl.DateTimeFormat("it-IT", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(new Date(value));
}

function historyError(error: unknown): string {
  return error instanceof Error ? error.message : "Storico GIS non disponibile";
}

export function GisActivityCenter({
  token,
  layers,
  showAudit = false,
  onResumeImport,
}: {
  token: string;
  layers: GisCatalogLayer[];
  showAudit?: boolean;
  onResumeImport?: (item: GisShapefileImport) => void;
}) {
  const [imports, setImports] = useState<GisShapefileImport[]>([]);
  const [exports, setExports] = useState<GisCatalogLayerExport[]>([]);
  const [audit, setAudit] = useState<GisAuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    const auditRequest = showAudit
      ? listGisAuditLogs(token, { limit: 25 })
      : Promise.resolve(null);
    void Promise.all([
      listGisShapefileImports(token, { limit: 25 }),
      listGisCatalogLayerExports(token, { limit: 25 }),
      auditRequest,
    ])
      .then(([importHistory, exportHistory, auditHistory]) => {
        if (cancelled) return;
        setImports(importHistory.items);
        setExports(exportHistory.items);
        setAudit(auditHistory?.items ?? []);
      })
      .catch((loadError: unknown) => {
        if (!cancelled) setError(historyError(loadError));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [reloadKey, showAudit, token]);

  function layerTitle(layerId: string): string {
    return layers.find((layer) => layer.id === layerId)?.title ?? "Mappa non disponibile";
  }

  return (
    <section className="rounded-[28px] border border-[#d9dfd6] bg-white p-5 shadow-sm">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#526a59]">Attività persistenti</p>
          <h3 className="mt-2 text-xl font-semibold text-gray-950">Coda e storico GIS</h3>
          <p className="mt-2 text-sm leading-6 text-gray-600">Le attività restano disponibili anche dopo aver chiuso o aggiornato la pagina.</p>
        </div>
        <button className="btn-secondary" type="button" disabled={loading} onClick={() => setReloadKey((value) => value + 1)}>
          {loading ? "Aggiornamento..." : "Aggiorna storico"}
        </button>
      </div>

      {error ? <p className="mt-4 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-semibold text-red-700" role="alert">{error}</p> : null}
      {loading ? <p className="mt-4 text-sm text-gray-600" role="status">Caricamento attività...</p> : null}

      <div className="mt-5 grid gap-5 xl:grid-cols-2">
        <HistoryColumn title="Import recenti" empty="Nessun import registrato.">
          {imports.map((item) => (
            <HistoryItem
              key={item.id}
              title={item.target_layer_title}
              meta={`${importStatusLabels[item.status] ?? item.status} · ${item.feature_count} elementi · ${readableDate(item.updated_at)}`}
              action={onResumeImport ? <button className="btn-secondary" type="button" onClick={() => onResumeImport(item)}>Riprendi</button> : null}
            />
          ))}
        </HistoryColumn>
        <HistoryColumn title="Export recenti" empty="Nessun export registrato.">
          {exports.map((item) => (
            <HistoryItem
              key={item.id}
              title={layerTitle(item.layer_id)}
              meta={`${item.status} · ${item.version_label} · ${readableDate(item.created_at)}`}
            />
          ))}
        </HistoryColumn>
      </div>

      {showAudit ? (
        <details className="mt-5 rounded-2xl border border-[#e2e9e3] bg-[#f8faf8] p-4">
          <summary className="cursor-pointer font-semibold text-[#1D4E35]">Consulta audit amministrativo ({audit.length})</summary>
          <div className="mt-4 grid gap-2">
            {audit.length === 0 ? <p className="text-sm text-gray-600">Nessun evento audit registrato.</p> : null}
            {audit.map((item) => <HistoryItem key={item.id} title={item.event_type} meta={`${item.target_type ?? "GIS"} · ${readableDate(item.created_at)}`} />)}
          </div>
        </details>
      ) : null}
    </section>
  );
}

function HistoryColumn({ title, empty, children }: { title: string; empty: string; children: React.ReactNode }) {
  const hasItems = Children.count(children) > 0;
  return (
    <div className="rounded-2xl border border-[#e2e9e3] bg-[#f8faf8] p-4">
      <h4 className="font-semibold text-gray-950">{title}</h4>
      <div className="mt-3 grid gap-2">{hasItems ? children : <p className="text-sm text-gray-600">{empty}</p>}</div>
    </div>
  );
}

function HistoryItem({ title, meta, action }: { title: string; meta: string; action?: React.ReactNode }) {
  return (
    <article className="flex flex-col gap-3 rounded-xl border border-white bg-white p-3 shadow-sm sm:flex-row sm:items-center sm:justify-between">
      <div><p className="text-sm font-semibold text-gray-950">{title}</p><p className="mt-1 text-xs leading-5 text-gray-500">{meta}</p></div>
      {action}
    </article>
  );
}
