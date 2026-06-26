"use client";

import { ProtectedPage } from "@/components/app/protected-page";
import { OrganigrammaWorkspace } from "@/features/organigramma/organigramma-workspace";

export default function PresenzeOrgStructurePage() {
  return (
    <ProtectedPage
      title="Organigramma giornaliere"
      description="Gerarchia canonica, perimetro responsabili-collaboratori ed eccezioni di visibilità per il dominio giornaliere."
      breadcrumb="Giornaliere"
      requiredModule="presenze"
      hideContentHeader
    >
      <OrganigrammaWorkspace forceStandardOnOpen forcedGuidedDensityOnOpen="compact" />
    </ProtectedPage>
  );
}
