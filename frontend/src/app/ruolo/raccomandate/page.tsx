"use client";

import { RegisteredMailsConsole } from "@/components/ruolo/registered-mails-console";
import { RuoloModulePage } from "@/components/ruolo/module-page";

export default function RuoloRaccomandatePage() {
  return (
    <RuoloModulePage
      title="Raccomandate Poste Online"
      description="Console read-only per matching, anomalie e recupero operativo degli invii Poste collegati ai tributi."
      breadcrumb="Raccomandate"
      requiredSection="ruolo.tributi.view"
    >
      <RegisteredMailsConsole />
    </RuoloModulePage>
  );
}
