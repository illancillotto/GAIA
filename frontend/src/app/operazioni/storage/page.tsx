"use client";

import { ProtectedPage } from "@/components/app/protected-page";
import { ServerIcon } from "@/components/ui/icons";

export default function StoragePage() {
  return (
    <ProtectedPage
      title="Storage — GAIA Operazioni"
      description="Monitoraggio quota storage allegati e alert soglie."
      breadcrumb="Storage"
      requiredModule="operazioni"
    >
      <div className="flex flex-col items-center justify-center py-16">
        <ServerIcon className="h-12 w-12 text-gray-300" />
        <h2 className="mt-4 text-lg font-medium text-gray-700">Storage Allegati</h2>
        <p className="mt-2 text-sm text-gray-500">Dashboard storage e gestione quote in implementazione.</p>
      </div>
    </ProtectedPage>
  );
}
