"use client";

import { ProtectedPage } from "@/components/app/protected-page";
import { OrganigrammaWorkspace } from "@/features/organigramma/organigramma-workspace";

export default function OrganigrammaPage() {
  return (
    <ProtectedPage
      title="Organigramma operativo"
      description="Gerarchia canonica, perimetro persona→responsabile→unità ed eccezioni di visibilità."
      breadcrumb="Governance · Organigramma"
      requiredModule="organigramma"
      requiredSection="organigramma.read"
      hideContentHeader
    >
      <OrganigrammaWorkspace />
    </ProtectedPage>
  );
}
