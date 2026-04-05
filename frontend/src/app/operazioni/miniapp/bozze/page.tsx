"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";

import { ProtectedPage } from "@/components/app/protected-page";
import { TruckIcon, RefreshIcon, AlertTriangleIcon, DocumentIcon } from "@/components/ui/icons";
import { getAllDrafts, getPendingCount, generateDraftId, saveDraft, DraftRecord } from "@/features/operazioni/utils/offline-drafts";

const statusLabels: Record<string, string> = {
  draft: "Bozza locale",
  pending: "In attesa di sincronizzazione",
  synced: "Sincronizzato",
  error: "Errore di invio",
};

const statusColors: Record<string, string> = {
  draft: "bg-gray-100 text-gray-600",
  pending: "bg-amber-100 text-amber-700",
  synced: "bg-green-100 text-green-700",
  error: "bg-red-100 text-red-700",
};

export default function MiniAppBozzePage() {
  const [drafts, setDrafts] = useState<DraftRecord[]>([]);
  const [pendingCount, setPendingCount] = useState(0);
  const [isOnline, setIsOnline] = useState(true);

  const loadDrafts = useCallback(async () => {
    const [allDrafts, count] = await Promise.all([
      getAllDrafts(),
      getPendingCount(),
    ]);
    setDrafts(allDrafts);
    setPendingCount(count);
  }, []);

  useEffect(() => {
    void loadDrafts();
  }, [loadDrafts]);

  useEffect(() => {
    setIsOnline(navigator.onLine);
    const handleOnline = () => {
      setIsOnline(true);
      void loadDrafts();
    };
    const handleOffline = () => setIsOnline(false);
    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);
    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, [loadDrafts]);

  return (
    <ProtectedPage
      title="Bozze — GAIA Operazioni"
      description="Gestione bozze locali e sincronizzazione."
      breadcrumb="Bozze"
      requiredModule="operazioni"
    >
      {!isOnline && (
        <div className="mb-4 rounded-lg bg-amber-50 px-4 py-3 text-sm text-amber-800 border border-amber-200">
          ⚠ Connessione assente — Le nuove azioni verranno salvate come bozze locali.
        </div>
      )}

      {pendingCount > 0 && isOnline && (
        <div className="mb-4 rounded-lg bg-blue-50 px-4 py-3 text-sm text-blue-800 border border-blue-200">
          🔄 {pendingCount} bozze in attesa di sincronizzazione.
        </div>
      )}

      <div className="mx-auto max-w-2xl py-4">
        <h2 className="text-lg font-semibold text-gray-800">Bozze e Sincronizzazione</h2>

        {drafts.length === 0 ? (
          <div className="mt-8 rounded-xl border border-dashed border-gray-300 p-8 text-center">
            <DocumentIcon className="mx-auto h-10 w-10 text-gray-300" />
            <p className="mt-3 text-sm text-gray-500">Nessuna bozza salvata.</p>
            <Link href="/operazioni/miniapp" className="mt-4 inline-block text-sm font-medium text-green-600 hover:text-green-700">
              ← Torna alla Mini-App
            </Link>
          </div>
        ) : (
          <div className="mt-4 space-y-3">
            {drafts.map((draft) => (
              <div
                key={draft.id}
                className="rounded-xl border border-gray-200 bg-white p-4"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    {draft.type === "activity" ? (
                      <RefreshIcon className="h-5 w-5 text-blue-600" />
                    ) : (
                      <AlertTriangleIcon className="h-5 w-5 text-amber-600" />
                    )}
                    <div>
                      <p className="text-sm font-medium text-gray-800">
                        {draft.type === "activity" ? "Attività" : "Segnalazione"}
                      </p>
                      <p className="text-xs text-gray-500">
                        {new Date(draft.updatedAt).toLocaleString("it-IT")}
                      </p>
                    </div>
                  </div>
                  <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${statusColors[draft.syncStatus]}`}>
                    {statusLabels[draft.syncStatus]}
                  </span>
                </div>
                {draft.syncError && (
                  <p className="mt-2 text-xs text-red-600">{draft.syncError}</p>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </ProtectedPage>
  );
}
