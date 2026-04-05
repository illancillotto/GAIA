"use client";

import { ProtectedPage } from "@/components/app/protected-page";
import { TruckIcon } from "@/components/ui/icons";

export default function MezziPage() {
  return (
    <ProtectedPage
      title="Mezzi — GAIA Operazioni"
      description="Gestione anagrafica mezzi, assegnazioni, sessioni utilizzo, carburante e manutenzioni."
      breadcrumb="Mezzi"
      requiredModule="operazioni"
    >
      <div className="flex flex-col items-center justify-center py-16">
        <TruckIcon className="h-12 w-12 text-gray-300" />
        <h2 className="mt-4 text-lg font-medium text-gray-700">Mezzi</h2>
        <p className="mt-2 text-sm text-gray-500">Lista mezzi e gestione completa in implementazione.</p>
      </div>
    </ProtectedPage>
  );
}
