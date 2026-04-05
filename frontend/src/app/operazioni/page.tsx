"use client";

import { ProtectedPage } from "@/components/app/protected-page";
import { TruckIcon } from "@/components/ui/icons";

export default function OperazioniDashboardPage() {
  return (
    <ProtectedPage
      title="GAIA Operazioni"
      description="Modulo per la gestione delle operazioni sul campo: mezzi, attività operatori, segnalazioni e pratiche."
      breadcrumb="Operazioni"
      requiredModule="operazioni"
    >
      <div className="flex flex-col items-center justify-center py-16">
        <TruckIcon className="h-16 w-16 text-gray-300" />
        <h2 className="mt-4 text-lg font-medium text-gray-700">GAIA Operazioni</h2>
        <p className="mt-2 max-w-md text-center text-sm text-gray-500">
          Modulo in corso di implementazione. Coprirà la gestione di mezzi, attività operatori,
          segnalazioni, pratiche interne e mini-app operatori.
        </p>
        <div className="mt-8 grid grid-cols-2 gap-4 sm:grid-cols-4">
          {[
            { label: "Mezzi", status: "In sviluppo" },
            { label: "Attività", status: "In sviluppo" },
            { label: "Segnalazioni", status: "In sviluppo" },
            { label: "Pratiche", status: "In sviluppo" },
          ].map((item) => (
            <div
              key={item.label}
              className="rounded-xl border border-gray-200 bg-gray-50 px-4 py-3 text-center"
            >
              <p className="text-sm font-medium text-gray-700">{item.label}</p>
              <p className="mt-1 text-xs text-gray-400">{item.status}</p>
            </div>
          ))}
        </div>
      </div>
    </ProtectedPage>
  );
}
