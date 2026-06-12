"use client";

import { ProtectedPage } from "@/components/app/protected-page";
import { OrganigrammaWorkspace } from "@/features/organigramma/organigramma-workspace";

export default function InazAssegnazioneTerritorialePage() {
  return (
    <ProtectedPage
      title="Assegnazione territoriale"
      description="Pagina dedicata Inaz per costruire e consultare l'assegnazione territoriale dei collaboratori."
      breadcrumb="Inaz"
      requiredModule="inaz"
      hideContentHeader
    >
      <OrganigrammaWorkspace
        structureKind="territoriale"
        forceStandardOnOpen
        forcedGuidedDensityOnOpen="compact"
        entityKey="assegnazione-territoriale"
        entityLabel="assegnazione territoriale"
        schemaTitle="Schema territoriale"
        eyebrow="Inaz · Assegnazione territoriale"
        pageTitle="Assegnazione territoriale"
        pageDescription="Usa la stessa logica dell'organigramma per assegnare collaboratori a distretti, settori o squadre territoriali. Non tutti gli utenti devono avere un'assegnazione."
        exportFilenamePrefix="assegnazione-territoriale-snapshot"
        emphasizeUnassignedFilter
      />
    </ProtectedPage>
  );
}
