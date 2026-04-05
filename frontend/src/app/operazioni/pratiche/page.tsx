"use client";

import { ProtectedPage } from "@/components/app/protected-page";
import { DocumentIcon } from "@/components/ui/icons";

export default function PratichePage() {
  return (
    <ProtectedPage
      title="Pratiche — GAIA Operazioni"
      description="Gestione pratiche interne: assegnazione, avanzamento stati, chiusura."
      breadcrumb="Pratiche"
      requiredModule="operazioni"
    >
      <div className="flex flex-col items-center justify-center py-16">
        <DocumentIcon className="h-12 w-12 text-gray-300" />
        <h2 className="mt-4 text-lg font-medium text-gray-700">Pratiche Interne</h2>
        <p className="mt-2 text-sm text-gray-500">Lista pratiche e timeline eventi in implementazione.</p>
      </div>
    </ProtectedPage>
  );
}
