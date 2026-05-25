"use client";

import { useCallback, useEffect, useState } from "react";

import { ProtectedPage } from "@/components/app/protected-page";
import { ElaborazioneHero, ElaborazioneNoticeCard, ElaborazionePanelHeader } from "@/components/elaborazioni/module-chrome";
import { ElaborazioneWorkspaceModal } from "@/components/elaborazioni/workspace-modal";
import { ModuleWorkspaceKpiRow, ModuleWorkspaceKpiTile } from "@/components/layout/module-workspace-hero";
import { RefreshIcon, TruckIcon } from "@/components/ui/icons";
import { getVehicleAutodocSyncStatus, queueVehicleAutodocSync, type VehicleAutodocSyncJob } from "@/features/operazioni/api/client";
import { formatDateTime } from "@/lib/presentation";

function formatMetricNumber(value: number | null | undefined, maximumFractionDigits = 0): string {
  if (value == null) return "—";
  return new Intl.NumberFormat("it-IT", { maximumFractionDigits }).format(value);
}

function formatAutodocStatus(status: string | null | undefined): string {
  switch (status) {
    case "queued":
      return "In coda";
    case "running":
      return "In esecuzione";
    case "completed":
      return "Completato";
    case "failed":
      return "Fallito";
    default:
      return status ?? "Nessun job";
  }
}

export function ElaborazioniAutodocWorkspace({ embedded = false }: { embedded?: boolean }) {
  const [job, setJob] = useState<VehicleAutodocSyncJob | null>(null);
  const [busy, setBusy] = useState<"full" | "cached" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isVehiclesModalOpen, setIsVehiclesModalOpen] = useState(false);

  const loadStatus = useCallback(async (): Promise<void> => {
    try {
      const response = await getVehicleAutodocSyncStatus();
      setJob(response);
      setError(null);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Errore caricamento stato AUTODOC");
    }
  }, []);

  useEffect(() => {
    void loadStatus();
  }, [loadStatus]);

  useEffect(() => {
    if (!job || !["queued", "running"].includes(job.status)) return;
    const intervalId = window.setInterval(() => void loadStatus(), 5000);
    return () => window.clearInterval(intervalId);
  }, [job, loadStatus]);

  async function handleQueueAutodocSync(mode: "full" | "cached"): Promise<void> {
    setBusy(mode);
    try {
      const response = await queueVehicleAutodocSync({
        only_with_autodoc_url: true,
        force_refresh: mode === "full",
      });
      setJob(response.job);
      setError(null);
      await loadStatus();
    } catch (queueError) {
      setError(queueError instanceof Error ? queueError.message : "Errore avvio sync AUTODOC");
    } finally {
      setBusy(null);
    }
  }

  const content = (
    <>
      <ElaborazioneHero
        compact={embedded}
        badge={
          <>
            <RefreshIcon className="h-3.5 w-3.5" />
            AUTODOC mezzi
          </>
        }
        title="Sync massiva dei dettagli AUTODOC."
        description="Questa pagina aggiorna i mezzi che hanno già un link AUTODOC salvato e mostra l'ultimo esito del worker dedicato."
        actions={
          error ? (
            <ElaborazioneNoticeCard title="Errore monitor" description={error} tone="danger" compact={embedded} />
          ) : (
            <ElaborazioneNoticeCard
              title="Modalità supportata"
              description="La sync massiva lavora sui mezzi con URL AUTODOC già noto. La discovery automatica da targa non è inclusa in questo flusso."
              compact={embedded}
            />
          )
        }
      >
        <ModuleWorkspaceKpiRow compact={embedded}>
          <ModuleWorkspaceKpiTile compact={embedded} label="Ultimo stato" value={formatAutodocStatus(job?.status)} hint={job?.started_at ? `Avvio ${formatDateTime(job.started_at)}` : "Nessun job registrato"} />
          <ModuleWorkspaceKpiTile compact={embedded} label="Sincronizzati" variant="emerald" value={formatMetricNumber(job?.records_synced ?? null)} hint={`Skippati ${formatMetricNumber(job?.records_skipped ?? null)}`} />
          <ModuleWorkspaceKpiTile compact={embedded} label="Errori" variant={(job?.records_errors ?? 0) > 0 ? "amber" : "default"} value={formatMetricNumber(job?.records_errors ?? null)} hint={job?.finished_at ? `Fine ${formatDateTime(job.finished_at)}` : "Job non concluso"} />
          <ModuleWorkspaceKpiTile compact={embedded} label="Modalità" value={job?.params_json?.force_refresh ? "Refresh URL salvati" : "Solo non sincronizzati"} hint="Solo mezzi con link AUTODOC salvato" />
        </ModuleWorkspaceKpiRow>
      </ElaborazioneHero>

      <article className="overflow-hidden rounded-[28px] border border-[#d9dfd6] bg-white shadow-panel">
        <ElaborazionePanelHeader
          badge={
            <>
              <RefreshIcon className="h-3.5 w-3.5" />
              Azioni AUTODOC
            </>
          }
          title="Avvio e monitoraggio run"
          description="Il refresh forzato rilegge tutte le schede note. La modalità veloce aggiorna solo i mezzi non ancora sincronizzati."
        />
        <div className="grid gap-6 p-6 lg:grid-cols-[1.15fr,0.85fr]">
          <div className="space-y-4">
            {job?.error_detail ? (
              <div className="rounded-2xl border border-amber-100 bg-amber-50 px-4 py-3">
                <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-amber-700">Ultimo errore</p>
                <p className="mt-2 break-words text-sm text-amber-900">{job.error_detail}</p>
              </div>
            ) : (
              <div className="rounded-2xl border border-gray-100 bg-[#f7faf8] px-4 py-3 text-sm text-gray-600">
                Se una sync è già in coda o in esecuzione, il backend restituisce il job aperto invece di crearne uno nuovo.
              </div>
            )}
            <div className="rounded-2xl border border-gray-100 bg-gray-50 px-4 py-4 text-sm text-gray-600">
              <p className="font-medium text-gray-900">Dettaglio worker</p>
              <div className="mt-2 space-y-1 text-xs text-gray-500">
                <p>Job id: {job?.job_id ?? "nessun job"}</p>
                <p>Entity worker: {job?.entity ?? "autodoc_vehicle_details"}</p>
              </div>
            </div>
          </div>
          <div className="rounded-[24px] border border-[#d9dfd6] bg-[#f7faf8] p-5">
            <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[#1D4E35]">Comandi</p>
            <div className="mt-5 flex flex-wrap gap-3">
              <button className="btn-primary" disabled={busy != null} onClick={() => void handleQueueAutodocSync("full")} type="button">
                {busy === "full" ? "Avvio refresh..." : "Refresh URL salvati"}
              </button>
              <button className="btn-secondary" disabled={busy != null} onClick={() => void handleQueueAutodocSync("cached")} type="button">
                {busy === "cached" ? "Avvio sync..." : "Solo non sincronizzati"}
              </button>
              <button className="btn-secondary" onClick={() => setIsVehiclesModalOpen(true)} type="button">
                <TruckIcon className="h-4 w-4" />
                Apri parco mezzi
              </button>
            </div>
          </div>
        </div>
      </article>
      <ElaborazioneWorkspaceModal
        description="Apre il modulo Operazioni per consultare mezzi, schede e sync puntuali AUTODOC."
        href="/operazioni/mezzi"
        onClose={() => setIsVehiclesModalOpen(false)}
        open={isVehiclesModalOpen}
        title="Parco mezzi"
      />
    </>
  );

  if (embedded) {
    return content;
  }

  return (
    <ProtectedPage
      title="GAIA Elaborazioni"
      description="Workspace dedicato alla sync massiva AUTODOC dei mezzi con link già censito."
      breadcrumb="Elaborazioni"
      requiredModule="catasto"
    >
      {content}
    </ProtectedPage>
  );
}
