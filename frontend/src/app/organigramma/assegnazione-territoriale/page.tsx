"use client";

import { ProtectedPage } from "@/components/app/protected-page";
import { OrganigrammaWorkspace } from "@/features/organigramma/organigramma-workspace";

export default function AssegnazioneTerritorialePage() {
  return (
    <ProtectedPage
      title="Assegnazione territoriale"
      description="Pagina dedicata per costruire e consultare l'assegnazione territoriale dei collaboratori."
      breadcrumb="Governance · Assegnazione territoriale"
      requiredModule="organigramma"
      requiredSection="organigramma.read"
      hideContentHeader
    >
      <OrganigrammaWorkspace
        structureKind="territoriale"
        entityKey="assegnazione-territoriale"
        entityLabel="assegnazione territoriale"
        schemaTitle="Schema territoriale"
        eyebrow="Governance · Assegnazione territoriale"
        pageTitle="Assegnazione territoriale"
        pageDescription="Usa la stessa logica dell'organigramma per assegnare collaboratori a distretti, settori o squadre territoriali. Non tutti gli utenti devono avere un'assegnazione."
        exportFilenamePrefix="assegnazione-territoriale-snapshot"
        emphasizeUnassignedFilter
      />
    </ProtectedPage>
  );
}
