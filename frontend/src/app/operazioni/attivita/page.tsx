"use client";

import { AttivitaContent } from "@/app/operazioni/attivita/attivita-content";
import { OperazioniModulePage } from "@/components/operazioni/operazioni-module-page";

export default function AttivitaPage() {
  return (
    <OperazioniModulePage
      title="Attività"
      description="Avvio e chiusura attività operatori, approvazioni e catalogo."
      breadcrumb="Lista"
    >
      {() => <AttivitaContent />}
    </OperazioniModulePage>
  );
}
