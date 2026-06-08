import { ProtectedPage } from "@/components/app/protected-page";
import { WikiSupportPage } from "@/features/wiki/WikiSupportPage";

export const metadata = {
  title: "Supporto Wiki — GAIA",
  description: "Assistenza, segnalazioni problemi e richieste funzione dal Wiki Agent.",
};

export default function WikiSupportRoute() {
  return (
    <ProtectedPage
      title="Supporto Wiki"
      description="Un solo ingresso per domande operative, anomalie e richieste funzionali su GAIA."
      breadcrumb="GAIA / Wiki / Supporto"
    >
      <WikiSupportPage />
    </ProtectedPage>
  );
}
