"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";

import {
  OperazioniCollectionHero,
  OperazioniCollectionPanel,
  OperazioniHeroNotice,
  OperazioniMetricStrip,
} from "@/components/operazioni/collection-layout";
import { OperazioniModulePage } from "@/components/operazioni/operazioni-module-page";
import { EmptyState } from "@/components/ui/empty-state";
import { MetricCard } from "@/components/ui/metric-card";
import { DocumentIcon } from "@/components/ui/icons";
import { createReport, startActivity, stopActivity } from "@/features/operazioni/api/client";
import {
  deleteDraft,
  DraftRecord,
  getAllDrafts,
  getPendingCount,
  markDraftPending,
  updateDraftSyncStatus,
} from "@/features/operazioni/utils/offline-drafts";

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
  const [isOnline, setIsOnline] = useState(true);
  const [syncingIds, setSyncingIds] = useState<string[]>([]);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const wasOnlineRef = useRef(true);
  const autoSyncInFlightRef = useRef(false);

  const purgeSyncedDrafts = useCallback(async (items?: DraftRecord[]) => {
    const syncedDrafts = (items ?? await getAllDrafts()).filter((draft) => draft.syncStatus === "synced");
    for (const draft of syncedDrafts) {
      // eslint-disable-next-line no-await-in-loop
      await deleteDraft(draft.id);
    }
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const syncStatus = () => setIsOnline(window.navigator.onLine);
    syncStatus();
    window.addEventListener("online", syncStatus);
    window.addEventListener("offline", syncStatus);
    return () => {
      window.removeEventListener("online", syncStatus);
      window.removeEventListener("offline", syncStatus);
    };
  }, []);

  const loadData = useCallback(async () => {
    try {
      const allDrafts = await getAllDrafts();
      if (allDrafts.some((draft) => draft.syncStatus === "synced")) {
        await purgeSyncedDrafts(allDrafts);
      }
      const [visibleDrafts, count] = await Promise.all([getAllDrafts(), getPendingCount()]);
      setDrafts(visibleDrafts);
      setPendingCount(count);
    } catch {
      setDrafts([]);
      setPendingCount(0);
    } finally {
      setIsLoading(false);
    }
  }, [purgeSyncedDrafts]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  const syncDraft = useCallback(async (draft: DraftRecord, options?: { silentSuccess?: boolean }) => {
    if (!isOnline) {
      setError("La sincronizzazione manuale richiede una connessione attiva.");
      return false;
    }

    setSyncingIds((current) => [...current, draft.id]);
    setError(null);
    setFeedback(null);

    try {
      await markDraftPending(draft.id);

      if (draft.type === "report") {
        await createReport(draft.data);
      } else if (draft.data.action === "stop" && typeof draft.data.activity_id === "string") {
        const payload = { ...draft.data };
        const activityId = String(payload.activity_id);
        delete payload.activity_id;
        delete payload.action;
        await stopActivity(activityId, payload);
      } else {
        await startActivity(draft.data);
      }

      await deleteDraft(draft.id);
      if (!options?.silentSuccess) {
        setFeedback(`Bozza ${draft.id} sincronizzata correttamente.`);
      }
      await loadData();
      return true;
    } catch (syncError) {
      const message = syncError instanceof Error ? syncError.message : "Errore sincronizzazione bozza";
      await updateDraftSyncStatus(draft.id, "error", message);
      setError(message);
      await loadData();
      return false;
    } finally {
      setSyncingIds((current) => current.filter((id) => id !== draft.id));
    }
  }, [isOnline, loadData]);

  const syncPendingDrafts = useCallback(async (mode: "manual" | "auto" = "manual") => {
    if (!isOnline) {
      setError("La sincronizzazione richiede una connessione attiva.");
      return;
    }

    const queue = drafts.filter((draft) => draft.syncStatus === "pending" || draft.syncStatus === "error");
    if (queue.length === 0) {
      if (mode === "manual") {
        setFeedback("Non ci sono bozze in attesa da sincronizzare.");
      }
      return;
    }

    if (mode === "auto") {
      autoSyncInFlightRef.current = true;
      setFeedback(`Connessione ripristinata: sincronizzazione automatica di ${queue.length} bozze in corso.`);
    } else {
      setFeedback(null);
    }

    let successCount = 0;
    let failureCount = 0;
    for (const draft of queue) {
      // sequential to avoid overlapping mutations against the same browser-local queue
      // and to keep backend side effects deterministic.
      // eslint-disable-next-line no-await-in-loop
      const success = await syncDraft(draft, { silentSuccess: true });
      if (success) {
        successCount += 1;
      } else {
        failureCount += 1;
      }
    }
    if (failureCount > 0) {
      setError(`${failureCount} bozze non sincronizzate. Verifica i dettagli nella coda.`);
    } else {
      setError(null);
    }
    setFeedback(
      mode === "auto"
        ? `Riconnessione completata: ${successCount} bozze sincronizzate${failureCount > 0 ? `, ${failureCount} da ritentare` : ""}.`
        : `${successCount} bozze sincronizzate${failureCount > 0 ? `, ${failureCount} con errore` : ""}.`,
    );
    autoSyncInFlightRef.current = false;
  }, [drafts, isOnline, syncDraft]);

  useEffect(() => {
    const wasOnline = wasOnlineRef.current;
    wasOnlineRef.current = isOnline;
    if (!isOnline || wasOnline || autoSyncInFlightRef.current) {
      return;
    }
    if (!drafts.some((draft) => draft.syncStatus === "pending" || draft.syncStatus === "error")) {
      return;
    }
    void syncPendingDrafts("auto");
  }, [drafts, isOnline, syncPendingDrafts]);

  async function removeDraft(id: string) {
    await deleteDraft(id);
    await loadData();
  }

  return (
    <div className="page-stack">
      <OperazioniCollectionHero
        eyebrow="Offline queue"
        icon={<DocumentIcon className="h-3.5 w-3.5" />}
        title="Bozze locali, code di sincronizzazione e recupero errori per la mini-app."
        description="La pagina mostra tutto ciò che è stato trattenuto in IndexedDB e aiuta a leggere subito cosa è in attesa, cosa è fallito e cosa è già stato inviato."
      >
        {pendingCount > 0 ? (
          <OperazioniHeroNotice
            title="Sincronizzazione in sospeso"
            description={`${pendingCount} bozze restano in attesa di invio automatico appena la connessione torna disponibile.`}
          />
        ) : (
          <OperazioniHeroNotice title="Coda pulita" description="Non risultano bozze in attesa di sincronizzazione." />
        )}
        <div className="rounded-2xl border border-white/80 bg-white/75 px-4 py-3">
          <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-gray-500">Sincronizzazione</p>
          <button type="button" className="btn-secondary mt-3" onClick={() => void syncPendingDrafts()} disabled={!isOnline || syncingIds.length > 0}>
            {syncingIds.length > 0 ? "Sincronizzazione..." : "Sincronizza coda"}
          </button>
        </div>
      </OperazioniCollectionHero>

      <OperazioniMetricStrip>
        <MetricCard label="Bozze totali" value={drafts.length} sub="Tutte le bozze salvate localmente" />
        <MetricCard label="In attesa" value={pendingCount} sub="Da sincronizzare" variant={pendingCount > 0 ? "warning" : "default"} />
        <MetricCard label="Sincronizzate" value={drafts.filter((d) => d.syncStatus === "synced").length} sub="Inviate con successo" variant="success" />
        <MetricCard label="Con errori" value={drafts.filter((d) => d.syncStatus === "error").length} sub="Da ritentare" variant={drafts.filter((d) => d.syncStatus === "error").length > 0 ? "danger" : "default"} />
      </OperazioniMetricStrip>

      <OperazioniCollectionPanel
        title="Elenco bozze"
        description="Bozze salvate localmente con timestamp di ultimo aggiornamento e stato di sincronizzazione."
        count={drafts.length}
      >
        {error ? <p className="mb-4 text-sm text-red-700">{error}</p> : null}
        {feedback ? <p className="mb-4 text-sm text-emerald-700">{feedback}</p> : null}
        {isLoading ? (
          <p className="text-sm text-gray-500">Caricamento bozze in corso.</p>
        ) : drafts.length === 0 ? (
          <EmptyState
            icon={DocumentIcon}
            title="Nessuna bozza salvata"
            description="Le azioni eseguite offline verranno salvate qui automaticamente."
          />
        ) : (
          <div className="max-h-[32rem] overflow-y-auto pr-1">
            <div className="space-y-3">
              {drafts.map((draft) => (
                <div key={draft.id} className="rounded-[24px] border border-[#e6ebe5] bg-[linear-gradient(180deg,_#ffffff,_#fbfcfa)] px-4 py-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="text-sm font-semibold text-gray-900">{draft.type === "activity" ? "Attività" : "Segnalazione"}</p>
                      <p className="mt-1 text-xs leading-5 text-gray-500">
                        {new Date(draft.updatedAt).toLocaleString("it-IT")}
                        {draft.syncError ? ` · ${draft.syncError}` : ""}
                      </p>
                    </div>
                    <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${statusTone[draft.syncStatus] || "bg-gray-100 text-gray-600"}`}>
                      {statusLabels[draft.syncStatus]}
                    </span>
                  </div>
                  <div className="mt-4 flex flex-wrap gap-3">
                    {(draft.syncStatus === "pending" || draft.syncStatus === "error") ? (
                      <button
                        type="button"
                        className="btn-secondary"
                        disabled={!isOnline || syncingIds.includes(draft.id)}
                        onClick={() => void syncDraft(draft)}
                      >
                        {syncingIds.includes(draft.id) ? "Sincronizzazione..." : "Sincronizza"}
                      </button>
                    ) : null}
                    {draft.syncStatus === "draft" ? (
                      <button
                        type="button"
                        className="btn-secondary"
                        disabled={!isOnline || syncingIds.includes(draft.id)}
                        onClick={() => void syncDraft(draft)}
                      >
                        Invia ora
                      </button>
                    ) : null}
                    <button type="button" className="btn-secondary" onClick={() => void removeDraft(draft.id)}>
                      Elimina
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </OperazioniCollectionPanel>

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
