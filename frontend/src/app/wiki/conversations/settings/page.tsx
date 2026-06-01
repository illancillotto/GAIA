import { ProtectedPage } from "@/components/app/protected-page";
import { WikiConversationGovernanceSettingsPage } from "@/features/wiki/WikiConversationGovernanceSettingsPage";

export const metadata = {
  title: "Settings Conversazioni Wiki — GAIA",
  description: "Soglie review e backfill storico della governance conversazioni Wiki.",
};

export default function WikiConversationGovernanceSettingsRoute() {
  return (
    <ProtectedPage
      title="Settings conversazioni Wiki"
      description="Configurazione soglie review, backfill metriche e marcatura copertura dati."
      breadcrumb="GAIA / Wiki / Conversazioni / Settings"
      requiredRoles={["admin", "super_admin"]}
    >
      <WikiConversationGovernanceSettingsPage />
    </ProtectedPage>
  );
}
