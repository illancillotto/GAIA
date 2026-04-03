"use client";

import Link from "next/link";

import { ProtectedPage } from "@/components/app/protected-page";
import { CatastoHero, CatastoNoticeCard } from "@/components/catasto/module-chrome";
import { RefreshIcon } from "@/components/ui/icons";

export default function CatastoDashboardPage() {
  return (
    <ProtectedPage
      title="GAIA Catasto"
      description="Modulo in corso di sviluppo e ridefinizione funzionale."
      breadcrumb="Catasto"
      requiredModule="catasto"
    >
      <CatastoHero
        badge={
          <>
            <RefreshIcon className="h-3.5 w-3.5" />
            Modulo in sviluppo
          </>
        }
        title="Il dominio Catasto è in corso di sviluppo."
        description="La pagina resta volutamente essenziale durante la ridefinizione del perimetro funzionale. I flussi operativi continuano a vivere nel modulo Elaborazioni."
        actions={
          <CatastoNoticeCard
            title="Stato attuale"
            description="Il dominio è in lavorazione. La dashboard Catasto sarà ricostruita quando saranno definiti i contenuti finali del modulo."
            tone="info"
          />
        }
      >
        <div className="rounded-2xl border border-[#d9dfd6] bg-white p-6 shadow-panel">
          <p className="text-sm leading-7 text-gray-600">
            Se devi continuare a lavorare su richieste, batch, CAPTCHA o credenziali operative, usa il modulo{" "}
            <Link className="font-medium text-[#1D4E35] underline underline-offset-2" href="/elaborazioni">
              Elaborazioni
            </Link>
            .
          </p>
        </div>
      </CatastoHero>
    </ProtectedPage>
  );
}
