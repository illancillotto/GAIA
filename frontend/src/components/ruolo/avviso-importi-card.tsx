import { ModuleWorkspaceMiniStat } from "@/components/layout/module-workspace-hero";
import { FolderIcon } from "@/components/ui/icons";
import type { RuoloAvvisoDetailResponse } from "@/types/ruolo";

export function formatEuro(value: number | null | undefined): string {
  if (value == null) return "—";
  return new Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR" }).format(value);
}

export function AvvisoImportiCard({ avviso }: { avviso: RuoloAvvisoDetailResponse }) {
  return (
    <article className="rounded-[28px] border border-[#d8dfd3] bg-white p-6 shadow-panel">
      <div>
        <p className="inline-flex items-center gap-2 rounded-full bg-[#eef3ec] px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.2em] text-[#1D4E35]">
          <FolderIcon className="h-3.5 w-3.5" />
          Ripartizione importi
        </p>
        <p className="mt-3 text-lg font-semibold text-gray-900">Quadro economico sintetico dell&apos;avviso.</p>
        <p className="mt-2 text-sm leading-6 text-gray-600">
          Gli importi sono separati per tributo e aiutano a leggere rapidamente il peso amministrativo della posizione.
        </p>
      </div>
      <div className="mt-6 grid gap-3">
        <ModuleWorkspaceMiniStat
          eyebrow="Tributo 0648"
          value={formatEuro(avviso.importo_totale_0648)}
          description="Quota manutenzione consortile."
          compact
        />
        <ModuleWorkspaceMiniStat
          eyebrow="Tributo 0985"
          value={formatEuro(avviso.importo_totale_0985)}
          description="Quota irrigazione."
          compact
        />
        <ModuleWorkspaceMiniStat
          eyebrow="Tributo 0668"
          value={formatEuro(avviso.importo_totale_0668)}
          description="Quota sistemazione idraulica."
          compact
        />
        <ModuleWorkspaceMiniStat
          eyebrow="Totale complessivo"
          value={formatEuro(avviso.importo_totale_euro)}
          description="Somma finale dell'avviso."
          tone="success"
          compact
        />
      </div>
    </article>
  );
}
