"use client";

import { OperazioniModulePage } from "@/components/operazioni/operazioni-module-page";
import { MetricCard } from "@/components/ui/metric-card";
import { EmptyState } from "@/components/ui/empty-state";
import { ServerIcon } from "@/components/ui/icons";

function StorageContent() {
  return (
    <div className="page-stack">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-gray-500">
          Monitoraggio quota storage allegati, alert soglie e gestione dello spazio disponibile.
        </p>
      </div>

      <div className="surface-grid">
        <MetricCard label="Spazio utilizzato" value={0} sub="Bytes occupati dagli allegati" />
        <MetricCard label="Quota totale" value={50} sub="GB disponibili (soglia 50GB)" />
        <MetricCard label="Percentuale" value={0} sub="Spazio utilizzato rispetto alla quota" variant="success" />
        <MetricCard label="Alert attivi" value={0} sub="Soglie superate da monitorare" />
      </div>

      <article className="panel-card">
        <div className="mb-4">
          <p className="section-title">Stato storage</p>
          <p className="section-copy">Dettagli utilizzo spazio disco per gli allegati del modulo Operazioni.</p>
        </div>

        <div className="rounded-xl border border-dashed border-gray-200 bg-gray-50 p-8 text-center">
          <ServerIcon className="mx-auto h-10 w-10 text-gray-300" />
          <p className="mt-3 text-sm font-medium text-gray-900">Monitoraggio storage</p>
          <p className="mt-1 text-sm text-gray-500">Dashboard storage e gestione quote in implementazione.</p>
        </div>
      </article>

      <article className="panel-card">
        <div className="mb-4">
          <p className="section-title">Soglie alert</p>
          <p className="section-copy">Configurazione soglie di allerta per lo spazio storage.</p>
        </div>

        <div className="space-y-3">
          {[
            { level: "70%", label: "Warning", tone: "bg-amber-50 text-amber-700", status: "Non superata" },
            { level: "85%", label: "Warning alto", tone: "bg-orange-50 text-orange-700", status: "Non superata" },
            { level: "95%", label: "Critico", tone: "bg-rose-50 text-rose-700", status: "Non superata" },
          ].map((threshold) => (
            <div key={threshold.level} className="flex items-center justify-between rounded-lg border border-gray-100 px-4 py-3">
              <div className="flex items-center gap-3">
                <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${threshold.tone}`}>{threshold.level}</span>
                <span className="text-sm font-medium text-gray-900">{threshold.label}</span>
              </div>
              <span className="text-sm text-gray-500">{threshold.status}</span>
            </div>
          ))}
        </div>
      </article>
    </div>
  );
}

export default function StoragePage() {
  return (
    <OperazioniModulePage
      title="Storage allegati"
      description="Quota storage allegati e alert sulle soglie."
      breadcrumb="Monitoraggio"
    >
      {() => <StorageContent />}
    </OperazioniModulePage>
  );
}
