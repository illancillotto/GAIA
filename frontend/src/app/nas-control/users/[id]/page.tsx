"use client";

import { useParams } from "next/navigation";

import { ProtectedPage } from "@/components/app/protected-page";
import { UserDetailPanel } from "@/components/app/user-detail-panel";

export default function UserDetailPage() {
  const params = useParams<{ id: string }>();
  const userId = Number(params.id);

  return (
    <ProtectedPage
      title="Dettaglio utente"
      description="Vista analitica di permessi effettivi, review e tracce operative del singolo utente NAS."
      breadcrumb="Utenti"
      requiredSection="accessi.users"
    >
      <UserDetailPanel userId={userId} />
    </ProtectedPage>
  );
}
