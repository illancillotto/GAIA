"use client";

import { ProtectedPage } from "@/components/app/protected-page";
import { AlertTriangleIcon } from "@/components/ui/icons";

export default function SegnalazioniPage() {
  return (
    <ProtectedPage
      title="Segnalazioni — GAIA Operazioni"
      description="Gestione segnalazioni dal campo con creazione automatica pratiche."
      breadcrumb="Segnalazioni"
      requiredModule="operazioni"
    >
      <div className="flex flex-col items-center justify-center py-16">
        <AlertTriangleIcon className="h-12 w-12 text-gray-300" />
        <h2 className="mt-4 text-lg font-medium text-gray-700">Segnalazioni</h2>
        <p className="mt-2 text-sm text-gray-500">Lista segnalazioni e creazione in implementazione.</p>
      </div>
    </ProtectedPage>
  );
}
