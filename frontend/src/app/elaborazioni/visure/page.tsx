import { ProtectedPage } from "@/components/app/protected-page";
import { ElaborazioniVisureWorkspaceClient } from "./visure-workspace-client";

const VISURE_BREADCRUMB = [
  { label: "Elaborazioni", href: "/elaborazioni" },
  { label: "Visure" },
];

export default function ElaborazioniVisurePage() {
  return (
    <ProtectedPage
      title="Visure"
      description="Ingresso operativo per visure singole e monitor dei lotti recenti."
      breadcrumbItems={VISURE_BREADCRUMB}
    >
      <div className="space-y-6">
        <ElaborazioniVisureWorkspaceClient />
      </div>
    </ProtectedPage>
  );
}
