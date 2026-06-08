import { ProtectedPage } from "@/components/app/protected-page";
import { WikiSupportAnalyticsPage } from "@/features/wiki/WikiSupportAnalyticsPage";

export const metadata = {
  title: "Analytics supporto Wiki — GAIA",
  description: "Trend richieste, anomalie e feature nate dal Wiki Agent.",
};

export default function WikiSupportAnalyticsRoute() {
  return (
    <ProtectedPage
      title="Analytics supporto Wiki"
      description="Trend supporto, anomalie, accessi e richieste funzionali emerse dal Wiki."
      breadcrumb="GAIA / Wiki / Supporto / Analytics"
      requiredRoles={["admin", "super_admin"]}
    >
      <WikiSupportAnalyticsPage />
    </ProtectedPage>
  );
}
