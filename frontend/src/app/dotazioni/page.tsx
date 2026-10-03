"use client";

import { ProtectedPage } from "@/components/app/protected-page";
import { DotazioniList } from "@/features/dotazioni/DotazioniList";

export default function DotazioniPage() {
  return <ProtectedPage title="GAIA Dotazioni" description="Beni del Consorzio, assegnazioni e custodie." breadcrumb="Dotazioni" requiredModule="dotazioni" requiredSection="dotazioni.view">
    <DotazioniList />
  </ProtectedPage>;
}
