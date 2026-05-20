import { ProtectedPage } from "@/components/app/protected-page";
import { ElaborazioneRequestWorkspace } from "@/components/elaborazioni/request-workspace";

export default function ElaborazioniVisurePage() {
  return (
    <ProtectedPage
      title="Visure"
      description="Ingresso operativo per visure singole e monitor dei lotti recenti."
      breadcrumb="Elaborazioni / Visure"
    >
      <div className="space-y-6">
        <ElaborazioneRequestWorkspace embedded initialMode="recent" />
      </div>
    </ProtectedPage>
  );
}
