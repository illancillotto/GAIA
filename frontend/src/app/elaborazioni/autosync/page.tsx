import { ProtectedPage } from "@/components/app/protected-page";
import { ElaborazioneRequestWorkspace } from "@/components/elaborazioni/request-workspace";

const AUTOSYNC_BREADCRUMB = [
  { label: "Elaborazioni", href: "/elaborazioni" },
  { label: "Monitor AutoSync" },
];

export default function ElaborazioniAutoSyncPage() {
  return (
    <ProtectedPage
      title="Monitor AutoSync"
      description="Monitor operativo, stato e configurazione della sincronizzazione continua delle visure a ruolo."
      breadcrumbItems={AUTOSYNC_BREADCRUMB}
    >
      <ElaborazioneRequestWorkspace embedded initialMode="autosync" />
    </ProtectedPage>
  );
}
