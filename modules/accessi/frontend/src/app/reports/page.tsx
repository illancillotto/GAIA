"use client";

import { ProtectedPage } from "@/components/app/protected-page";
import { EmptyState } from "@/components/ui/empty-state";
import { DocumentIcon } from "@/components/ui/icons";

export default function ReportsPage() {
  return (
    <ProtectedPage
      title="Report"
      description="Area predisposta per export report e pacchetti di bonifica accessi."
      breadcrumb="Validazione"
    >
      <EmptyState
        icon={DocumentIcon}
        title="Report non ancora disponibili"
        description="La sezione è pronta per ospitare export CSV/PDF e reportistica di audit nei prossimi sviluppi."
      />
    </ProtectedPage>
  );
}
