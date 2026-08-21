import { ProtectedPage } from "@/components/app/protected-page";
import { SisterPortalHealthWorkspace } from "@/components/elaborazioni/sister-portal-health-workspace";


export const metadata = {
  title: "Stato portale SISTER - GAIA",
  description: "Telemetria, tempi e affidabilita delle visure SISTER.",
};


export default function SisterPortalHealthPage() {
  return (
    <ProtectedPage
      title="Stato portale SISTER"
      description="Telemetria operativa, tempi per fase e protezioni dinamiche delle visure."
      breadcrumb="GAIA / Elaborazioni / Stato portale SISTER"
      requiredModule="catasto"
      hideContentHeader
    >
      <SisterPortalHealthWorkspace />
    </ProtectedPage>
  );
}
