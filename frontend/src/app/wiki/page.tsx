import { ProtectedPage } from "@/components/app/protected-page";
import { WikiPage } from "@/features/wiki/WikiPage";

export const metadata = {
  title: "Wiki — GAIA",
  description: "Documentazione e assistente GAIA",
};

export default function WikiRoute() {
  return (
    <ProtectedPage
      title="Wiki"
      description="Documentazione indicizzata e assistente contestuale per i flussi GAIA."
      breadcrumb="GAIA / Wiki"
    >
      <WikiPage />
    </ProtectedPage>
  );
}
