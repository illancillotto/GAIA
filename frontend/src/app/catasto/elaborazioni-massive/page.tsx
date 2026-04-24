"use client";

import { CatastoPage } from "@/components/catasto/catasto-page";
import { AnagraficaBulkPanel } from "@/components/catasto/anagrafica/AnagraficaBulkPanel";

export default function CatastoElaborazioniMassivePage() {
  return (
    <CatastoPage
      title="Elaborazione massiva"
      description="Carica un file di riferimenti catastali e ottieni anagrafica e utenze correlate."
      breadcrumb="Catasto / Elaborazione massiva"
      requiredModule="catasto"
    >
      <AnagraficaBulkPanel />
    </CatastoPage>
  );
}

