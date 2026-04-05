"use client";

import { ProtectedPage } from "@/components/app/protected-page";
import { RefreshIcon } from "@/components/ui/icons";

export default function AttivitaPage() {
  return (
    <ProtectedPage
      title="Attività — GAIA Operazioni"
      description="Gestione attività operatori: avvio, chiusura, approvazioni e catalogo."
      breadcrumb="Attività"
      requiredModule="operazioni"
    >
      <div className="flex flex-col items-center justify-center py-16">
        <RefreshIcon className="h-12 w-12 text-gray-300" />
        <h2 className="mt-4 text-lg font-medium text-gray-700">Attività Operatori</h2>
        <p className="mt-2 text-sm text-gray-500">Lista attività e workflow approvazione in implementazione.</p>
      </div>
    </ProtectedPage>
  );
}
