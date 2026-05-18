"use client";

import { CatastoPage } from "@/components/catasto/catasto-page";
import { ParticelleSearchWorkspace } from "@/components/catasto/particelle-search-workspace";

export default function CatastoParticellePage() {
  return (
    <CatastoPage
      title="Particelle"
      description="Lista particelle del dominio Catasto con filtri principali."
      breadcrumb="Catasto / Particelle"
      requiredModule="catasto"
    >
      <ParticelleSearchWorkspace mode="all" />
    </CatastoPage>
  );
}
