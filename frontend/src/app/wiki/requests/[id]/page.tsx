import { ProtectedPage } from "@/components/app/protected-page";
import { WikiRequestsPage } from "@/features/wiki/WikiRequestsPage";

export const metadata = {
  title: "Dettaglio richiesta Wiki — GAIA",
  description: "Dettaglio amministrativo di una richiesta registrata dal Wiki Agent.",
};

export default async function WikiRequestDetailRoute({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return (
    <ProtectedPage
      title="Dettaglio richiesta Wiki"
      description="Timeline, assegnazione e gestione operativa della richiesta selezionata."
      breadcrumb="GAIA / Wiki / Richieste / Dettaglio"
      requiredRoles={["admin", "super_admin"]}
    >
      <WikiRequestsPage initialRequestId={id} />
    </ProtectedPage>
  );
}
