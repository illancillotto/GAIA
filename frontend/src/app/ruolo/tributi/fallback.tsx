"use client";

import { RuoloModulePage } from "@/components/ruolo/module-page";

export function RuoloTributiFallback() {
  return (
    <RuoloModulePage
      title="Tributi Ruolo"
      description="Tracciamento pagamenti, scoperti, note operative e link CapaciTas sugli avvisi a ruolo."
      breadcrumb="Tributi"
      requiredSection="ruolo.tributi.view"
    >
      <p className="text-sm text-gray-400">Caricamento sezione tributi...</p>
    </RuoloModulePage>
  );
}
