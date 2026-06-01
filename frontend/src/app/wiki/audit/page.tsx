import { ProtectedPage } from "@/components/app/protected-page";
import { WikiAuditPage } from "@/features/wiki/WikiAuditPage";

export const metadata = {
  title: "Audit Wiki — GAIA",
  description: "Registro amministrativo delle tool call del Wiki Agent.",
};

export default function WikiAuditRoute() {
  return (
    <ProtectedPage
      title="Audit Wiki"
      description="Consultazione amministrativa delle tool call del Wiki Agent, con filtri per modulo, intent e utente."
      breadcrumb="GAIA / Wiki / Audit"
      requiredRoles={["admin", "super_admin"]}
    >
      <WikiAuditPage />
    </ProtectedPage>
  );
}
