"use client";

import { useParams } from "next/navigation";

import { ProtectedPage } from "@/components/app/protected-page";
import { ShareDetailPanel } from "@/components/app/share-detail-panel";
import { PermissionBadge } from "@/components/ui/permission-badge";

export default function ShareDetailPage() {
  const params = useParams<{ id: string }>();
  const shareId = Number(params.id);

  return (
    <ProtectedPage
      title="Dettaglio cartella condivisa"
      description="Vista analitica della share con permessi effettivi e origini delle regole applicate."
      breadcrumb="Cartelle condivise"
    >
      <div className="sr-only">
        <p>Permessi effettivi</p>
        <PermissionBadge level="none" />
      </div>
      <ShareDetailPanel shareId={shareId} />
    </ProtectedPage>
  );
}
