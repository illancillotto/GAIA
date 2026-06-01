import { ProtectedPage } from "@/components/app/protected-page";
import { WikiConversationsPage } from "@/features/wiki/WikiConversationsPage";

export const metadata = {
  title: "Conversazioni Wiki — GAIA",
  description: "Thread persistiti del Wiki Agent GAIA",
};

export default function WikiConversationsRoute() {
  return (
    <ProtectedPage
      title="Conversazioni Wiki"
      description="Ricerca e riapertura dei thread persistiti del Wiki Agent."
      breadcrumb="GAIA / Wiki / Conversazioni"
    >
      <WikiConversationsPage />
    </ProtectedPage>
  );
}
