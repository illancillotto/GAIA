"use client";

import { ProtectedPage } from "@/components/app/protected-page";
import { OrganigrammaWorkspace } from "@/features/organigramma/organigramma-workspace";

export default function InazOrgStructurePage() {
  return (
    <ProtectedPage
      title="Organigramma Inaz"
      description="Gerarchia canonica, perimetro responsabili-collaboratori ed eccezioni di visibilità per il dominio Inaz."
      breadcrumb="Inaz"
      requiredModule="inaz"
      hideContentHeader
    >
      <OrganigrammaWorkspace />
    </ProtectedPage>
  );
}
