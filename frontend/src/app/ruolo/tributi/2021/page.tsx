"use client";

import { RuoloModulePage } from "@/components/ruolo/module-page";
import { CampaignWorkspace } from "@/components/ruolo/campaign-2021/workspace";

export default function Campaign2021Page() {
  return <RuoloModulePage title="Avvisi e solleciti 2021" description="Perimetro, riconciliazione e anteprime da importi approvati." breadcrumb="Avvisi e solleciti 2021" requiredSection="ruolo.tributi.view">
    <CampaignWorkspace />
  </RuoloModulePage>;
}
