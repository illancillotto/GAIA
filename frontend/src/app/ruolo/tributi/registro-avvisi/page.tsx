"use client";

import { RuoloModulePage } from "@/components/ruolo/module-page";
import { NoticeRegisterWorkspace } from "@/components/ruolo/notice-register/workspace";

export default function NoticeRegisterPage() {
  return <RuoloModulePage title="Registro avvisi" description="Storico documenti, notifiche e verifiche STEP." breadcrumb="Registro avvisi" requiredSection="ruolo.tributi.view">
    <NoticeRegisterWorkspace />
  </RuoloModulePage>;
}
