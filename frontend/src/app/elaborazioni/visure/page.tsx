import { ProtectedPage } from "@/components/app/protected-page";
import { ElaborazioniVisureWorkspaceClient } from "./visure-workspace-client";

export default function ElaborazioniVisurePage() {
  return (
    <ProtectedPage
      title="Visure"
      description="Ingresso operativo per visure singole e monitor dei lotti recenti."
      breadcrumb="Elaborazioni / Visure"
    >
      <div className="space-y-6">
        <ElaborazioniVisureWorkspaceClient />
      </div>
    </ProtectedPage>
  );
}
