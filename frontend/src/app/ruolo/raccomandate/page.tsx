"use client";

import { RegisteredMailsAccess } from "@/components/ruolo/registered-mails-console";
import { RuoloModulePage } from "@/components/ruolo/module-page";

export default function RuoloRaccomandatePage() {
  return (
    <RuoloModulePage
      title="Raccomandate Poste Online"
      description="Revisione delle associazioni tra invii Poste e avvisi, con conferma individuale dell'operatore."
      breadcrumb="Raccomandate"
      requiredSection="ruolo.tributi.view"
    >
      <RegisteredMailsAccess />
    </RuoloModulePage>
  );
}
