"use client";

import { OrganigrammaWorkspace } from "@/app/organigramma/page";
import { ProtectedPage } from "@/components/app/protected-page";

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
