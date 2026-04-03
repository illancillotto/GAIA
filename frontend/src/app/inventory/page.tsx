"use client";

import Link from "next/link";

import { ProtectedPage } from "@/components/app/protected-page";
import { InventoryHero, InventoryNoticeCard } from "@/components/inventory/module-chrome";
import { RefreshIcon } from "@/components/ui/icons";

export default function InventoryPage() {
  return (
    <ProtectedPage
      title="GAIA Inventario"
      description="Modulo in corso di sviluppo e ridefinizione funzionale."
      breadcrumb="Inventario"
      requiredModule="inventory"
    >
      <InventoryHero
        badge={
          <>
            <RefreshIcon className="h-3.5 w-3.5" />
            Modulo in sviluppo
          </>
        }
        title="Il dominio Inventario è in corso di sviluppo."
        description="La pagina resta volutamente essenziale durante la ridefinizione del perimetro funzionale. Le funzionalità operative verranno esposte progressivamente nelle prossime release."
        actions={
          <InventoryNoticeCard
            title="Stato attuale"
            description="Il dominio è in lavorazione. La dashboard Inventario sarà estesa quando saranno definiti i contenuti finali del modulo."
            tone="info"
          />
        }
      >
        <div className="rounded-2xl border border-[#d9dfd6] bg-white p-6 shadow-panel">
          <p className="text-sm leading-7 text-gray-600">
            Se ti serve operare sui flussi attuali (richieste, batch e automazioni), usa il modulo{" "}
            <Link className="font-medium text-[#1D4E35] underline underline-offset-2" href="/elaborazioni">
              Elaborazioni
            </Link>
            .
          </p>
        </div>
      </InventoryHero>
    </ProtectedPage>
  );
}
