"use client";

import { RuoloModulePage } from "@/components/ruolo/module-page";

export function RuoloTributiDetailFallback() {
  return (
    <RuoloModulePage
      title="Dettaglio Tributo"
      description="Gestione puntuale di pagamento, stato operativo, note e link CapaciTas."
      breadcrumb="Dettaglio tributo"
      requiredSection="ruolo.tributi.view"
    >
      <p className="text-sm text-gray-400">Caricamento dettaglio tributo...</p>
    </RuoloModulePage>
  );
}
