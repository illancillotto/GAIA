"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { OperazioniModulePage } from "@/components/operazioni/operazioni-module-page";
import { MetricCard } from "@/components/ui/metric-card";
import { EmptyState } from "@/components/ui/empty-state";
import { DocumentIcon, ChevronRightIcon } from "@/components/ui/icons";
import { getAllDrafts, getPendingCount, DraftRecord } from "@/features/operazioni/utils/offline-drafts";

const statusLabels: Record<string, string> = {
  draft: "Bozza locale",
  pending: "In attesa di sincronizzazione",
  synced: "Sincronizzato",
  error: "Errore di invio",
};

const statusTone: Record<string, string> = {
  draft: "bg-gray-100 text-gray-600",
  pending: "bg-amber-50 text-amber-700",
  synced: "bg-emerald-50 text-emerald-700",
  error: "bg-rose-50 text-rose-700",
};

function BozzeContent() {
  const [drafts, setDrafts] = useState<DraftRecord[]>([]);
  const [pendingCount, setPendingCount] = useState(0);
  const [isLoading, setIsLoading] = useState(true);

  const loadData = useCallback(async () => {
    try {
      const [allDrafts, count] = await Promise.all([
        getAllDrafts(),
        getPendingCount(),
      ]);
      setDrafts(allDrafts);
      setPendingCount(count);
    } catch {
      setDrafts([]);
      setPendingCount(0);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  return (
    <div className="page-stack">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-gray-500">
          Gestione bozze locali salvate offline e sincronizzazione con il server quando la connessione e disponibile.
        </p>
      </div>

      {pendingCount > 0 && (
        <article className="panel-card">
          <p className="text-sm font-medium text-amber-700">{pendingCount} bozze in attesa di sincronizzazione</p>
          <p className="mt-1 text-sm text-gray-600">Le bozze verranno inviate automaticamente quando la connessione tornera disponibile.</p>
        </article>
      )}

      <div className="surface-grid">
        <MetricCard label="Bozze totali" value={drafts.length} sub="Tutte le bozze salvate localmente" />
        <MetricCard label="In attesa" value={pendingCount} sub="Da sincronizzare" variant={pendingCount > 0 ? "warning" : "default"} />
        <MetricCard label="Sincronizzate" value={drafts.filter((d) => d.syncStatus === "synced").length} sub="Inviate con successo" variant="success" />
        <MetricCard label="Con errori" value={drafts.filter((d) => d.syncStatus === "error").length} sub="Da ritentare" variant={drafts.filter((d) => d.syncStatus === "error").length > 0 ? "danger" : "default"} />
      </div>

      <article className="panel-card">
        <div className="mb-4 flex items-center justify-between gap-3">
          <div>
            <p className="section-title">Elenco bozze</p>
            <p className="section-copy">Bozze salvate localmente con stato di sincronizzazione.</p>
          </div>
        </div>

        {isLoading ? (
          <p className="text-sm text-gray-500">Caricamento bozze in corso.</p>
        ) : drafts.length === 0 ? (
          <EmptyState
            icon={DocumentIcon}
            title="Nessuna bozza salvata"
            description="Le azioni eseguite offline verranno salvate qui automaticamente."
          />
        ) : (
          <div className="max-h-[32rem] space-y-3 overflow-y-auto pr-1">
            {drafts.map((draft) => (
              <div
                key={draft.id}
                className="flex w-full items-center justify-between rounded-lg border border-gray-100 px-4 py-3"
              >
                <div>
                  <p className="text-sm font-medium text-gray-900">
                    {draft.type === "activity" ? "Attività" : "Segnalazione"}
                  </p>
                  <p className="mt-1 text-xs text-gray-500">
                    {new Date(draft.updatedAt).toLocaleString("it-IT")}
                    {draft.syncError ? ` · ${draft.syncError}` : ""}
                  </p>
                </div>
                <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${statusTone[draft.syncStatus] || "bg-gray-100 text-gray-600"}`}>
                  {statusLabels[draft.syncStatus]}
                </span>
              </div>
            ))}
          </div>
        )}
      </article>

      <div className="flex gap-3">
        <Link href="/operazioni/miniapp" className="btn-secondary">
          Torna alla Mini-App
        </Link>
        <Link href="/operazioni" className="btn-secondary">
          Dashboard Operazioni
        </Link>
      </div>
    </div>
  );
}

export default function MiniAppBozzePage() {
  return (
    <OperazioniModulePage
      title="Bozze locali"
      description="Bozze salvate in locale e sincronizzazione con il backend."
      breadcrumb="Mini-app"
    >
      {() => <BozzeContent />}
    </OperazioniModulePage>
  );
}
