"use client";

import { ProtectedPage } from "@/components/app/protected-page";
import { TruckIcon, RefreshIcon, AlertTriangleIcon } from "@/components/ui/icons";
import { useState, useEffect } from "react";

export default function MiniAppPage() {
  const [isOnline, setIsOnline] = useState(true);

  useEffect(() => {
    setIsOnline(navigator.onLine);
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);
    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);
    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, []);

  return (
    <ProtectedPage
      title="Mini-App Operatori — GAIA Operazioni"
      description="Interfaccia mobile-first per operatori sul campo."
      breadcrumb="Mini-App"
      requiredModule="operazioni"
    >
      {!isOnline && (
        <div className="mb-4 rounded-lg bg-amber-50 px-4 py-3 text-sm text-amber-800 border border-amber-200">
          ⚠ Connessione assente — Le azioni verranno salvate come bozze locali e sincronizzate quando tornerà la rete.
        </div>
      )}

      <div className="mx-auto max-w-md space-y-4 py-8">
        <h2 className="text-center text-xl font-semibold text-gray-800">Operazioni Rapide</h2>

        <div className="grid gap-4">
          <button
            type="button"
            className="flex items-center gap-4 rounded-2xl border-2 border-green-200 bg-green-50 p-6 text-left transition hover:bg-green-100 active:scale-[0.98]"
          >
            <RefreshIcon className="h-8 w-8 shrink-0 text-green-700" />
            <div>
              <p className="text-lg font-semibold text-green-800">Avvia Attività</p>
              <p className="text-sm text-green-600">Seleziona e inizia una nuova attività</p>
            </div>
          </button>

          <button
            type="button"
            className="flex items-center gap-4 rounded-2xl border-2 border-blue-200 bg-blue-50 p-6 text-left transition hover:bg-blue-100 active:scale-[0.98]"
          >
            <TruckIcon className="h-8 w-8 shrink-0 text-blue-700" />
            <div>
              <p className="text-lg font-semibold text-blue-800">Chiudi Attività</p>
              <p className="text-sm text-blue-600">Registra la chiusura dell&apos;attività in corso</p>
            </div>
          </button>

          <button
            type="button"
            className="flex items-center gap-4 rounded-2xl border-2 border-amber-200 bg-amber-50 p-6 text-left transition hover:bg-amber-100 active:scale-[0.98]"
          >
            <AlertTriangleIcon className="h-8 w-8 shrink-0 text-amber-700" />
            <div>
              <p className="text-lg font-semibold text-amber-800">Nuova Segnalazione</p>
              <p className="text-sm text-amber-600">Crea una segnalazione dal campo</p>
            </div>
          </button>
        </div>

        <div className="mt-6 rounded-xl border border-gray-200 bg-gray-50 p-4">
          <p className="text-sm font-medium text-gray-600">Stato connessione</p>
          <p className={`mt-1 text-sm font-semibold ${isOnline ? "text-green-600" : "text-amber-600"}`}>
            {isOnline ? "Connesso" : "Non connesso — modalità offline"}
          </p>
        </div>
      </div>
    </ProtectedPage>
  );
}
