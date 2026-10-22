"use client";

import { useCallback, useEffect, useState } from "react";

import { ProtectedPage } from "@/components/app/protected-page";
import { ElaborazioneHero, ElaborazioneMiniStat, ElaborazioneNoticeCard } from "@/components/elaborazioni/module-chrome";
import { useAppShellContext } from "@/components/layout/app-shell-context";
import { LockIcon } from "@/components/ui/icons";
import { usePolling } from "@/hooks/use-polling";
import { getStepOverview, listStepCredentials, listStepJobs } from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import { formatDateTime } from "@/lib/presentation";
import type { StepCredential, StepOverview, StepSyncJob } from "@/types/step";

import { StepContribuentiPanel } from "./step-contribuenti-panel";
import { StepCredentialsPanel } from "./step-credentials-panel";
import { ACTIVE_JOB_STATUSES, LINK_STATUS_LABELS, formatEuro } from "./step-format";
import { StepJobsPanel } from "./step-jobs-panel";
import { StepLinkAnomaliesPanel } from "./step-link-anomalies-panel";

function OverviewStats({ overview }: { overview: StepOverview | null }) {
  const value = (number: number | undefined) => (number ?? 0).toLocaleString("it-IT");
  return (
    <div className="grid gap-4 md:grid-cols-4">
      <ElaborazioneMiniStat eyebrow="Contribuenti" value={value(overview?.contribuenti)} description={`${value(overview?.documenti)} documenti · ${value(overview?.tributi)} tributi`} />
      <ElaborazioneMiniStat eyebrow="Residuo STEP" value={formatEuro(overview?.residuo_totale)} description={`${value(overview?.pagamenti)} pagamenti · ${value(overview?.pdf_scaricati)} PDF`} />
      <ElaborazioneMiniStat
        eyebrow="Collegati al ruolo"
        value={value(overview?.links.linked)}
        description={`${value(overview?.links.not_found)} ${LINK_STATUS_LABELS.not_found.toLowerCase()} · ${value(overview?.links.ambiguous)} ambigui · ${value(overview?.links.unrecognized)} non riconosciuti`}
      />
      <ElaborazioneMiniStat eyebrow="Ultimo aggiornamento" value={overview?.ultimo_aggiornamento ? formatDateTime(overview.ultimo_aggiornamento) : "Mai"} description="Ultima lettura elenco o import." />
    </div>
  );
}

export function StepWorkspaceContent() {
  const { currentUser } = useAppShellContext();
  const isSuperAdmin = currentUser?.role === "super_admin";
  const [token, setToken] = useState<string | null>(null);
  const [overview, setOverview] = useState<StepOverview | null>(null);
  const [credentials, setCredentials] = useState<StepCredential[]>([]);
  const [jobs, setJobs] = useState<StepSyncJob[]>([]);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!token) return;
    try {
      setOverview(await getStepOverview(token));
      if (isSuperAdmin) {
        const [credentialRows, jobRows] = await Promise.all([listStepCredentials(token), listStepJobs(token)]);
        setCredentials(credentialRows);
        setJobs(jobRows);
      }
      setError(null);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Errore caricamento STEP");
    }
  }, [token, isSuperAdmin]);

  useEffect(() => {
    setToken(getStoredAccessToken());
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const hasActiveJobs = jobs.some((job) => ACTIVE_JOB_STATUSES.has(job.status));
  usePolling(load, { enabled: hasActiveJobs, intervalMs: 10000 });

  const changed = useCallback(
    async (message: string | null) => {
      setNotice(message);
      await load();
    },
    [load],
  );

  if (!token) return null;

  return (
    <div className="space-y-7">
      <ElaborazioneHero
        badge={
          <>
            <LockIcon className="h-3.5 w-3.5" />
            STEP
          </>
        }
        title="Riscossione coattiva STEP: archivio e collegamento al ruolo."
        description="Copia in sola lettura di contribuenti, documenti, tributi, PDF e pagamenti STEP. I collegamenti agli avvisi non modificano il registro avvisi né creano pagamenti GAIA."
        actions={error ? <ElaborazioneNoticeCard title="Errore STEP" description={error} tone="danger" /> : <ElaborazioneNoticeCard title={hasActiveJobs ? "Worker in attività" : "Worker pronto"} description={hasActiveJobs ? "La lista job si aggiorna automaticamente." : "Dati aggiornati all'ultima sincronizzazione."} />}
      >
        <OverviewStats overview={overview} />
      </ElaborazioneHero>
      {notice ? <ElaborazioneNoticeCard title="Operazione registrata" description={notice} /> : null}
      {isSuperAdmin ? (
        <div className="grid gap-6 xl:grid-cols-[0.9fr,1.1fr]">
          <StepCredentialsPanel credentials={credentials} onChanged={changed} onError={setError} token={token} />
          <StepJobsPanel archives={overview?.import_archives ?? []} jobs={jobs} onChanged={changed} onError={setError} token={token} />
        </div>
      ) : null}
      <StepContribuentiPanel onError={setError} token={token} />
      <StepLinkAnomaliesPanel onError={setError} token={token} />
    </div>
  );
}

export function ElaborazioniStepWorkspace() {
  return (
    <ProtectedPage
      title="STEP"
      description="Sincronizzazione riscossione coattiva STEP e collegamento agli avvisi del ruolo."
      breadcrumb="Elaborazioni / STEP"
      requiredModule="ruolo"
      requiredSection="ruolo.tributi.view"
    >
      <StepWorkspaceContent />
    </ProtectedPage>
  );
}
