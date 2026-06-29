"use client";

import { AttivitaContent } from "@/app/operazioni/attivita/page";
import { OperazioniModulePage } from "@/components/operazioni/operazioni-module-page";

export default function AttivitaContatoriPage() {
  return (
    <OperazioniModulePage
      title="Attività contatori"
      description="Attività operative provenienti da GaTe Mobile e collegate alle letture contatori in Catasto."
      breadcrumb="Contatori"
    >
      {() => (
        <AttivitaContent
          initialScopeFilter="mobile_meter"
          title="Attività contatori dal campo con collegamento diretto alla lettura registrata in Catasto."
          description="La vista isola le attività GaTe Mobile che hanno generato una lettura contatore, così da seguire avanzamento operativo e riscontro del dato acquisito."
        />
      )}
    </OperazioniModulePage>
  );
}
