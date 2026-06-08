import { ProtectedPage } from "@/components/app/protected-page";
import { WikiRequestsPage } from "@/features/wiki/WikiRequestsPage";

export const metadata = {
  title: "Richieste Wiki — GAIA",
  description: "Coda amministrativa delle richieste registrate dal Wiki Agent.",
};

export default function WikiRequestsRoute() {
  return (
    <ProtectedPage
      title="Richieste Wiki"
      description="Gestione amministrativa delle richieste registrate dai fallback del Wiki Agent."
      breadcrumb="GAIA / Wiki / Richieste"
      requiredRoles={["admin", "super_admin"]}
    >
      <WikiRequestsPage />
    </ProtectedPage>
  );
}
