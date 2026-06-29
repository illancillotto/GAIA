"use client";

import { useSearchParams } from "next/navigation";

import { AttivitaContent } from "@/app/operazioni/attivita/attivita-content";
import { OperazioniModulePage } from "@/components/operazioni/operazioni-module-page";

export default function AttivitaPage() {
  const searchParams = useSearchParams();
  const initialOperatorUserId = searchParams.get("operator_user_id");

  return (
    <OperazioniModulePage
      title="Attività"
      description="Avvio e chiusura attività operatori, approvazioni e catalogo."
      breadcrumb="Lista"
    >
      {() => <AttivitaContent initialOperatorUserId={initialOperatorUserId} />}
    </OperazioniModulePage>
  );
}
