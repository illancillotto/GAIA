import { ProtectedPage } from "@/components/app/protected-page";
import { WikiRequestsPage } from "@/features/wiki/WikiRequestsPage";

export const metadata = {
  title: "Inbox Supporto Wiki — GAIA",
  description: "Coda amministrativa delle segnalazioni operative e anomalie raccolte dal Wiki Agent.",
};

export default function WikiSupportInboxRoute() {
  return (
    <ProtectedPage
      title="Inbox supporto Wiki"
      description="Triage amministrativo di supporto operativo, anomalie, accessi e problemi dati raccolti dal Wiki Agent."
      breadcrumb="GAIA / Wiki / Supporto / Inbox"
      requiredRoles={["admin", "super_admin"]}
    >
      <WikiRequestsPage supportOnly />
    </ProtectedPage>
  );
}
