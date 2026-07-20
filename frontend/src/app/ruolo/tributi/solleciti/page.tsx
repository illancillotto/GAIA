import Link from "next/link";

import { RuoloModulePage } from "@/components/ruolo/module-page";
import { EmptyState } from "@/components/ui/empty-state";
import { DocumentIcon } from "@/components/ui/icons";

export default function RuoloTributiSollecitiPage() {
  return (
    <RuoloModulePage
      title="Solleciti Tributi"
      description="Registro e generazione dei solleciti di pagamento."
      breadcrumb="Solleciti"
      requiredSection="ruolo.tributi.generate_reminders"
    >
      <section className="rounded-[28px] border border-[#d8dfd3] bg-white p-6 shadow-panel">
        <EmptyState
          icon={DocumentIcon}
          title="Generazione solleciti da implementare"
          description="La milestone prevede template .docx, storico solleciti e download. Nessun invio automatico verra attivato in questa fase."
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
