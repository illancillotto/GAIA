"use client";

import { ProtectedPage } from "@/components/app/protected-page";
import { PresenzeSyncWorkspace } from "@/components/presenze/presenze-sync-workspace";

export default function ElaborazioniPresenzeSyncPage() {
  return (
    <ProtectedPage
      title="Sync Presenze INAZ"
      description="Console operativa per worker, autosync, storico job e diagnostica delle giornaliere."
      breadcrumb="Elaborazioni / Presenze INAZ"
      requiredModule="presenze"
    >
      <PresenzeSyncWorkspace />
    </ProtectedPage>
  );
}
