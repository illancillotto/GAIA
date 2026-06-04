"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { ProtectedPage } from "@/components/app/protected-page";
import {
  ModuleWorkspaceHero,
  ModuleWorkspaceKpiRow,
  ModuleWorkspaceKpiTile,
  ModuleWorkspaceNoticeCard,
} from "@/components/layout/module-workspace-hero";
import { listInazCollaborators, listInazDailyRecords, listInazSyncJobs } from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import type { InazCollaborator, InazDailyRecord, InazSyncJob } from "@/types/api";

function currentMonthBounds(): { start: string; end: string } {
  const now = new Date();
  const start = new Date(now.getFullYear(), now.getMonth(), 1);
  const end = new Date(now.getFullYear(), now.getMonth() + 1, 0);
  const format = (value: Date) =>
    `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, "0")}-${String(value.getDate()).padStart(2, "0")}`;
  return { start: format(start), end: format(end) };
}

export default function InazPage() {
  const [collaborators, setCollaborators] = useState<InazCollaborator[]>([]);
  const [records, setRecords] = useState<InazDailyRecord[]>([]);
  const [jobs, setJobs] = useState<InazSyncJob[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = getStoredAccessToken();
    if (!token) return;
    const { start, end } = currentMonthBounds();
    Promise.all([
      listInazCollaborators(token, { page: 1, pageSize: 6 }),
      listInazDailyRecords(token, { dateFrom: start, dateTo: end, page: 1, pageSize: 8 }),
      listInazSyncJobs(token),
    ])
      .then(([collaboratorResponse, recordResponse, jobsResponse]) => {
        setCollaborators(collaboratorResponse.items);
        setRecords(recordResponse.items);
        setJobs(jobsResponse.slice(0, 6));
      })
      .catch((loadError) => setError(loadError instanceof Error ? loadError.message : "Errore caricamento modulo Inaz"));
  }, []);

  const mappedCount = useMemo(() => collaborators.filter((item) => item.application_user_id != null).length, [collaborators]);
  const ordinaryHours = useMemo(
    () => (records.reduce((sum, item) => sum + (item.ordinary_minutes ?? 0), 0) / 60).toFixed(1),
    [records],
  );
  const latestJob = jobs[0] ?? null;
  const latestJobProgress = latestJob?.params_json?.progress;
  const latestJobTitle = latestJob
    ? latestJob.status === "running"
      ? "Sync in esecuzione"
      : latestJob.status === "completed"
        ? "Ultima sync completata"
        : `Ultima sync: ${latestJob.status}`
    : "Nessuna sync registrata";
  const latestJobDescription = latestJob
    ? latestJobProgress?.index && latestJobProgress?.total
      ? `Avanzamento ${latestJobProgress.index}/${latestJobProgress.total} · completati ${latestJobProgress.completed_collaborators ?? 0} · falliti ${latestJobProgress.failed_collaborators ?? latestJob.records_errors}`
      : `Periodo ${latestJob.period_start} / ${latestJob.period_end} · importati ${latestJob.records_imported} · errori ${latestJob.records_errors}`
    : "Avvia una sync Inaz per popolare il modulo.";

  return (
    <ProtectedPage title="GAIA Inaz" description="Collaboratori, giornaliere e riepiloghi eventi Inaz." breadcrumb="Inaz" requiredModule="inaz">
      <div className="space-y-8">
        <ModuleWorkspaceHero
          badge={<>Modulo Inaz</>}
          title="Supervisiona collaboratori, cartellini ed export giornaliere da un unico workspace."
          description="Il modulo sincronizza i dati Inaz, salva giornaliere e riepiloghi eventi nel database GAIA e genera il file `.xlsm` dai dati persistiti."
          actions={
            <>
              <ModuleWorkspaceNoticeCard
                title={latestJobTitle}
                description={latestJobDescription}
                tone={latestJob?.status === "completed" ? "success" : latestJob?.status === "failed" ? "danger" : latestJob?.status === "running" ? "warning" : "warning"}
              />
              <ModuleWorkspaceNoticeCard
                title={mappedCount > 0 ? "Collaboratori mappati" : "Mapping da completare"}
                description={
                  mappedCount > 0
                    ? `${mappedCount} collaboratori risultano gia collegati a utenti GAIA.`
                    : "Nessun collaboratore risulta ancora collegato a `application_users`."
                }
                tone={mappedCount > 0 ? "info" : "warning"}
              />
            </>
          }
        >
          <ModuleWorkspaceKpiRow>
            <ModuleWorkspaceKpiTile label="Collaboratori" value={collaborators.length} hint="Estratti recenti" />
            <ModuleWorkspaceKpiTile label="Mappati GAIA" value={mappedCount} hint="Con application_user_id" variant="emerald" />
            <ModuleWorkspaceKpiTile label="Giornaliere mese" value={records.length} hint="Periodo corrente" />
            <ModuleWorkspaceKpiTile label="Ore ordinarie" value={`${ordinaryHours} h`} hint="Campione dashboard" />
          </ModuleWorkspaceKpiRow>
        </ModuleWorkspaceHero>

        {error ? <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div> : null}

        <div className="grid gap-6 xl:grid-cols-3">
          <article className="panel-card xl:col-span-2">
            <div className="mb-4 flex items-center justify-between gap-3">
              <div>
                <p className="section-title">Collaboratori recenti</p>
                <p className="section-copy">Stato mapping e accesso rapido al dettaglio calendario/eventi.</p>
              </div>
              <Link className="btn-secondary" href="/inaz/collaboratori">
                Apri lista
              </Link>
            </div>
            <div className="space-y-3">
              {collaborators.map((item) => (
                <Link key={item.id} href={`/inaz/collaboratori/${item.id}`} className="flex items-center justify-between gap-3 rounded-2xl border border-gray-100 bg-gray-50 px-4 py-3 transition hover:bg-white">
                  <div>
                    <p className="font-medium text-gray-900">{item.name}</p>
                    <p className="text-xs text-gray-500">
                      Matricola {item.employee_code} · Azienda {item.company_code ?? "n/d"} · {item.birth_date ?? "Data nascita n/d"}
                    </p>
                  </div>
                  <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${item.application_user_id ? "bg-emerald-100 text-emerald-700" : "bg-amber-100 text-amber-700"}`}>
                    {item.application_user_id ? "Mappato" : "Da mappare"}
                  </span>
                </Link>
              ))}
              {collaborators.length === 0 ? <p className="text-sm text-gray-500">Nessun collaboratore disponibile.</p> : null}
            </div>
          </article>

          <article className="panel-card">
            <div className="mb-4">
              <p className="section-title">Flussi operativi</p>
              <p className="section-copy">Accesso rapido ai percorsi principali del modulo.</p>
            </div>
            <div className="space-y-3">
              <Link className="btn-secondary block text-center" href="/inaz/sync">Sync Inaz</Link>
              <Link className="btn-secondary block text-center" href="/inaz/giornaliere">Giornaliere</Link>
              <Link className="btn-secondary block text-center" href="/inaz/export">Export XLSM</Link>
            </div>
            <div className="mt-6 space-y-2">
              <p className="text-sm font-medium text-gray-700">Storico sync</p>
              {jobs.map((job) => (
                <div key={job.id} className="rounded-xl border border-gray-100 bg-gray-50 px-3 py-2 text-sm">
                  <p className="font-medium text-gray-900">{new Intl.DateTimeFormat("it-IT", { month: "long", year: "numeric" }).format(new Date(`${job.period_start}T00:00:00`))}</p>
                  <p className="text-xs text-gray-500">
                    {job.status} · importati {job.records_imported} · errori {job.records_errors}
                  </p>
                  {job.params_json?.progress?.index && job.params_json?.progress?.total ? (
                    <p className="text-xs text-gray-500">
                      avanzamento {job.params_json.progress.index}/{job.params_json.progress.total}
                    </p>
                  ) : null}
                </div>
              ))}
              {jobs.length === 0 ? <p className="text-sm text-gray-500">Nessun job disponibile.</p> : null}
            </div>
          </article>
        </div>
      </div>
    </ProtectedPage>
  );
}
