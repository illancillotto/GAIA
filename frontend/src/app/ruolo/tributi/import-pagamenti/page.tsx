import Link from "next/link";

import { RuoloModulePage } from "@/components/ruolo/module-page";
import { EmptyState } from "@/components/ui/empty-state";
import { DocumentIcon } from "@/components/ui/icons";

export default function RuoloTributiImportPagamentiPage() {
  return (
    <RuoloModulePage
      title="Import Pagamenti Tributi"
      description="Predisposizione del workflow di import pagamenti CapaciTas."
      breadcrumb="Import pagamenti"
      requiredSection="ruolo.tributi.import_payments"
    >
      <section className="rounded-[28px] border border-[#d8dfd3] bg-white p-6 shadow-panel">
        <EmptyState
          icon={DocumentIcon}
          title="Tracciato Excel CapaciTas in attesa"
          description="La struttura backend per job e pagamenti e pronta. Il mapping colonne verra implementato quando sara disponibile il file Excel reale."
        />
        <div className="mt-6 flex flex-wrap justify-center gap-3">
          <Link className="btn-secondary" href="/ruolo/tributi">
            Torna ai tributi
          </Link>
        </div>
      </section>
    </RuoloModulePage>
  );
}
