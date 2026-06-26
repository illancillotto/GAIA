"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { ProtectedPage } from "@/components/app/protected-page";
import {
  ModuleWorkspaceHero,
  ModuleWorkspaceKpiRow,
  ModuleWorkspaceKpiTile,
  ModuleWorkspaceMiniStat,
  ModuleWorkspaceNoticeCard,
} from "@/components/layout/module-workspace-hero";
import { getPresenzeDashboardSummary, listAllPresenzeCollaborators, listPresenzeSyncJobs } from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import { getPresenzeCompanyLabel } from "@/lib/presenze-display";
import type { PresenzeCollaborator, PresenzeDashboardSummaryResponse, PresenzeSyncJob } from "@/types/api";

function currentMonthBounds(): { start: string; end: string } {
  const now = new Date();
  const start = new Date(now.getFullYear(), now.getMonth(), 1);
  const end = new Date(now.getFullYear(), now.getMonth() + 1, 0);
  const format = (value: Date) =>
    `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, "0")}-${String(value.getDate()).padStart(2, "0")}`;
  return { start: format(start), end: format(end) };
}

function formatMonthLabelFromIso(isoDate: string): string {
  return new Intl.DateTimeFormat("it-IT", { month: "long", year: "numeric" }).format(new Date(`${isoDate}T00:00:00`));
}

function formatHours(minutes: number): string {
  return `${(minutes / 60).toFixed(1)} h`;
}

function safeDisplay(value: unknown, fallback = "n/d"): string {
  if (value == null) return fallback;
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  if (typeof value === "object") {
    const record = value as Record<string, unknown>;
    if (typeof record.name === "string" && record.name.trim()) {
      return record.name;
    }
    if (typeof record.employee_code === "string" && record.employee_code.trim()) {
      return record.employee_code;
    }
  }
  return fallback;
}

export default function PresenzePage() {
  const [summary, setSummary] = useState<PresenzeDashboardSummaryResponse | null>(null);
  const [collaborators, setCollaborators] = useState<PresenzeCollaborator[]>([]);
  const [jobs, setJobs] = useState<PresenzeSyncJob[]>([]);
  const [selectedCollaborator, setSelectedCollaborator] = useState<PresenzeCollaborator | null>(null);
  const [collaboratorSearch, setCollaboratorSearch] = useState("");
  const [isCollaboratorsLoading, setIsCollaboratorsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = getStoredAccessToken();
    if (!token) return;
    const { start, end } = currentMonthBounds();
    Promise.all([getPresenzeDashboardSummary(token, { periodStart: start, periodEnd: end }), listPresenzeSyncJobs(token, { limit: 6 })])
      .then(([dashboardSummary, jobsResponse]) => {
        setSummary(dashboardSummary);
        setJobs(jobsResponse);
      })
      .catch((loadError) => setError(loadError instanceof Error ? loadError.message : "Errore caricamento modulo Giornaliere"));
  }, []);

  useEffect(() => {
    const token = getStoredAccessToken();
    if (!token) return;

    let cancelled = false;
    const loadCollaborators = () => {
      setIsCollaboratorsLoading(true);
      listAllPresenzeCollaborators(token)
        .then((items) => {
          if (!cancelled) {
            setCollaborators(items);
          }
        })
        .catch((loadError) => {
          if (!cancelled) {
            setError(loadError instanceof Error ? loadError.message : "Errore caricamento collaboratori giornaliere");
          }
        })
        .finally(() => {
          if (!cancelled) {
            setIsCollaboratorsLoading(false);
          }
        });
    };

    const useIdleCallback = typeof window !== "undefined" && "requestIdleCallback" in window;
    const handle = useIdleCallback ? window.requestIdleCallback(loadCollaborators, { timeout: 800 }) : window.setTimeout(loadCollaborators, 150);

    return () => {
      cancelled = true;
      if (useIdleCallback && "cancelIdleCallback" in window) {
        window.cancelIdleCallback(handle);
      } else {
        window.clearTimeout(handle);
      }
    };
  }, []);

  const mappedCount = summary?.mapped_collaborators_total ?? 0;
  const dashboardMonthLabel = useMemo(() => formatMonthLabelFromIso(currentMonthBounds().start), []);
  const normalizedCollaboratorSearch = collaboratorSearch.trim().toLowerCase();
  const recentCollaborators = useMemo(() => {
    const baseItems = normalizedCollaboratorSearch
      ? collaborators.filter((item) =>
          [
            safeDisplay(item.name, "").toLowerCase(),
            safeDisplay(item.employee_code, "").toLowerCase(),
            getPresenzeCompanyLabel(item.company_label, item.company_code, "").toLowerCase(),
          ].some((value) => value.includes(normalizedCollaboratorSearch)),
        )
      : collaborators;
    return baseItems.slice(0, normalizedCollaboratorSearch ? 10 : 6);
  }, [collaborators, normalizedCollaboratorSearch]);
  const ordinaryMinutes = summary?.ordinary_minutes_total ?? 0;
  const absenceMinutes = summary?.absence_minutes_total ?? 0;
  const extraMinutes = summary?.extra_minutes_total ?? 0;
  const straordinarioMinutes = summary?.straordinario_minutes_total ?? 0;
  const maggiorPresenzaMinutes = summary?.maggior_presenza_minutes_total ?? 0;
  const trasfertaMinutes = summary?.trasferta_minutes_total ?? 0;
  const trasfertaDays = summary?.trasferta_days_total ?? 0;
  const trasfertaMontanoDays = summary?.trasferta_montano_days_total ?? 0;
  const anomalyCount = summary?.anomaly_total ?? 0;
  const specialDayCount = summary?.special_day_total ?? 0;
  const recoveryDaysMatured = summary?.recovery_days_matured_total ?? 0;
  const recoveryDaysUsed = summary?.recovery_days_used_total ?? 0;
  const recoveryDaysBalance = summary?.recovery_days_balance_total ?? 0;
  const workedDaysCount = summary?.worked_days_total ?? 0;
  const absenceDaysCount = summary?.absence_days_total ?? 0;
  const justifiedDaysCount = summary?.justified_days_total ?? 0;
  const activeCollaboratorsCount = summary?.active_collaborators_total ?? 0;
  const causeStats = summary?.cause_stats ?? {};
  const scheduleStats = useMemo(
    () => (summary?.schedule_stats ?? []).map((item) => [item.code, item.count] as const),
    [summary],
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
    : "Avvia una sync giornaliere per popolare il modulo.";

  return (
    <ProtectedPage title="GAIA Giornaliere" description="Collaboratori, giornaliere e riepiloghi eventi del portale presenze." breadcrumb="Giornaliere" requiredModule="presenze">
      <div className="space-y-8">
        <ModuleWorkspaceHero
          badge={<>Modulo Giornaliere</>}
          title="Supervisiona collaboratori, cartellini ed export giornaliere da un unico workspace."
          description="Il modulo sincronizza i dati del portale presenze, salva giornaliere e riepiloghi eventi nel database GAIA e genera il file `.xlsm` dai dati persistiti."
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
            <ModuleWorkspaceKpiTile label="Collaboratori" value={summary?.collaborators_total ?? 0} hint="Importati a database" />
            <ModuleWorkspaceKpiTile label="Mappati GAIA" value={mappedCount} hint="Con application_user_id" variant="emerald" />
            <ModuleWorkspaceKpiTile label="Collaboratori attivi mese" value={activeCollaboratorsCount} hint={dashboardMonthLabel} />
            <ModuleWorkspaceKpiTile label="Giornaliere mese" value={summary?.daily_records_total ?? 0} hint="Righe cartellino persistite" />
            <ModuleWorkspaceKpiTile label="Ore ordinarie" value={formatHours(ordinaryMinutes)} hint="Totale mese" variant="emerald" />
            <ModuleWorkspaceKpiTile label="Extra effettivi" value={formatHours(extraMinutes)} hint="Straordinario + maggior presenza" variant="amber" />
            <ModuleWorkspaceKpiTile label="Trasferte" value={formatHours(trasfertaMinutes)} hint={`${trasfertaDays} giornate${trasfertaMontanoDays > 0 ? ` · montano ${trasfertaMontanoDays}` : ""}`} />
            <ModuleWorkspaceKpiTile label="Recuperi maturati" value={recoveryDaysMatured} hint="Da festivita soppresse" />
            <ModuleWorkspaceKpiTile label="Saldo recuperi" value={recoveryDaysBalance} hint={`Usati ${recoveryDaysUsed}`} />
          </ModuleWorkspaceKpiRow>
        </ModuleWorkspaceHero>

        {error ? <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div> : null}

        <div className="grid gap-6 xl:grid-cols-4">
          <ModuleWorkspaceMiniStat eyebrow="Presenze" value={workedDaysCount} description="Giornate con ore ordinarie registrate nel mese." tone="success" />
          <ModuleWorkspaceMiniStat eyebrow="Assenze" value={absenceDaysCount} description={`Totale ore assenza ${formatHours(absenceMinutes)}.`} tone="warning" />
          <ModuleWorkspaceMiniStat eyebrow="Trasferte" value={trasfertaDays} description={`Ore ${formatHours(trasfertaMinutes)}${trasfertaMontanoDays > 0 ? ` · montano ${trasfertaMontanoDays}` : ""}.`} />
          <ModuleWorkspaceMiniStat eyebrow="Anomalie" value={anomalyCount} description="Giornate con stato anomalo o rilievi nel dettaglio giornaliero." tone="warning" />
          <ModuleWorkspaceMiniStat eyebrow="Recuperi" value={recoveryDaysBalance} description={`Maturati ${recoveryDaysMatured}, fruiti ${recoveryDaysUsed}.`} />
        </div>

        <div className="grid gap-6 xl:grid-cols-3">
          <article className="panel-card">
            <div className="mb-4">
              <p className="section-title">Presenze mese</p>
              <p className="section-copy">Quadro macro del cartellino mensile importato in GAIA.</p>
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="rounded-2xl border border-gray-100 bg-gray-50 p-4">
                <p className="text-xs uppercase tracking-[0.16em] text-gray-400">Ore ordinarie</p>
                <p className="mt-2 text-2xl font-semibold text-gray-900">{formatHours(ordinaryMinutes)}</p>
              </div>
              <div className="rounded-2xl border border-gray-100 bg-gray-50 p-4">
                <p className="text-xs uppercase tracking-[0.16em] text-gray-400">Ore assenza</p>
                <p className="mt-2 text-2xl font-semibold text-gray-900">{formatHours(absenceMinutes)}</p>
              </div>
              <div className="rounded-2xl border border-gray-100 bg-gray-50 p-4">
                <p className="text-xs uppercase tracking-[0.16em] text-gray-400">Straordinario</p>
                <p className="mt-2 text-2xl font-semibold text-emerald-700">{formatHours(straordinarioMinutes)}</p>
              </div>
              <div className="rounded-2xl border border-gray-100 bg-gray-50 p-4">
                <p className="text-xs uppercase tracking-[0.16em] text-gray-400">Maggior presenza</p>
                <p className="mt-2 text-2xl font-semibold text-emerald-700">{formatHours(maggiorPresenzaMinutes)}</p>
              </div>
            </div>
            <div className="mt-4 grid gap-3 sm:grid-cols-3">
              <div className="rounded-2xl border border-gray-100 bg-white p-3 text-sm text-gray-700">
                Giorni speciali
                <p className="mt-1 text-lg font-semibold text-gray-900">{specialDayCount}</p>
              </div>
              <div className="rounded-2xl border border-gray-100 bg-white p-3 text-sm text-gray-700">
                Assenze giustificate
                <p className="mt-1 text-lg font-semibold text-gray-900">{justifiedDaysCount}</p>
              </div>
              <div className="rounded-2xl border border-gray-100 bg-white p-3 text-sm text-gray-700">
                Extra effettivi
                <p className="mt-1 text-lg font-semibold text-gray-900">{formatHours(extraMinutes)}</p>
              </div>
            </div>
          </article>

          <article className="panel-card">
            <div className="mb-4">
              <p className="section-title">Causali assenza</p>
              <p className="section-copy">Distribuzione delle principali causali normalizzate lette dalle giornaliere.</p>
            </div>
            <div className="space-y-3">
              {[
                ["ferie", causeStats.ferie ?? 0, "Ferie"],
                ["permesso", causeStats.permesso ?? 0, "Permessi"],
                ["malattia", causeStats.malattia ?? 0, "Malattia"],
              ].map(([key, value, label]) => (
                <div key={key} className="rounded-2xl border border-gray-100 bg-gray-50 px-4 py-3">
                  <div className="flex items-center justify-between gap-3">
                    <p className="text-sm font-medium text-gray-700">{label}</p>
                    <p className="text-lg font-semibold text-gray-900">{value}</p>
                  </div>
                </div>
              ))}
              {Object.keys(causeStats).length === 0 ? <p className="text-sm text-gray-500">Nessuna causale assenza rilevata nel mese.</p> : null}
            </div>
          </article>

          <article className="panel-card">
            <div className="mb-4">
              <p className="section-title">Orari prevalenti</p>
              <p className="section-copy">Codici turno o orario piu frequenti sulle giornaliere del mese.</p>
            </div>
            <div className="space-y-3">
              {scheduleStats.map(([code, count]) => (
                <div key={code} className="rounded-2xl border border-gray-100 bg-gray-50 px-4 py-3">
                  <div className="flex items-center justify-between gap-3">
                    <p className="font-medium text-gray-900">{code}</p>
                    <span className="rounded-full bg-white px-2.5 py-1 text-xs font-medium text-gray-600">{count} gg</span>
                  </div>
                </div>
              ))}
              {scheduleStats.length === 0 ? <p className="text-sm text-gray-500">Nessun codice orario disponibile.</p> : null}
            </div>
          </article>
        </div>

        <div className="grid gap-6 xl:grid-cols-3">
          <article className="panel-card xl:col-span-2">
            <div className="mb-4 flex items-center justify-between gap-3">
              <div>
                <p className="section-title">Collaboratori del mese</p>
                <p className="section-copy">Stato mapping e accesso rapido al dettaglio calendario/eventi.</p>
              </div>
              <Link className="btn-secondary" href="/presenze/collaboratori">
                Apri lista
              </Link>
            </div>
            <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <label className="block sm:max-w-sm sm:flex-1">
                <span className="sr-only">Cerca collaboratore</span>
                <input
                  className="form-control w-full"
                  type="search"
                  value={collaboratorSearch}
                  onChange={(event) => setCollaboratorSearch(event.target.value)}
                  placeholder="Cerca per nome, matricola o azienda"
                />
              </label>
              {normalizedCollaboratorSearch ? (
                <p className="text-xs text-gray-500">
                  Risultati rapidi: {recentCollaborators.length}
                </p>
              ) : null}
            </div>
            <div className="space-y-3">
              {isCollaboratorsLoading && collaborators.length === 0 ? <p className="text-sm text-gray-500">Caricamento collaboratori…</p> : null}
              {recentCollaborators.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => setSelectedCollaborator(item)}
                  className="flex w-full items-center justify-between gap-3 rounded-2xl border border-gray-100 bg-gray-50 px-4 py-3 text-left transition hover:bg-white"
                >
                  <div>
                    <p className="font-medium text-gray-900">{safeDisplay(item.name)}</p>
                    <p className="text-xs text-gray-500">
                      {[
                        `Matricola ${safeDisplay(item.employee_code)}`,
                        getPresenzeCompanyLabel(item.company_label, item.company_code, "") ? `Azienda ${getPresenzeCompanyLabel(item.company_label, item.company_code, "")}` : null,
                        safeDisplay(item.birth_date, "Data nascita n/d"),
                      ]
                        .filter(Boolean)
                        .join(" · ")}
                    </p>
                  </div>
                  <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${item.application_user_id ? "bg-emerald-100 text-emerald-700" : "bg-amber-100 text-amber-700"}`}>
                    {item.application_user_id ? "Mappato" : "Da mappare"}
                  </span>
                </button>
              ))}
              {recentCollaborators.length === 0 ? (
                <p className="text-sm text-gray-500">
                  {normalizedCollaboratorSearch ? "Nessun collaboratore trovato per questa ricerca." : "Nessun collaboratore disponibile."}
                </p>
              ) : null}
            </div>
          </article>

          <article className="panel-card">
            <div className="mb-4">
              <p className="section-title">Flussi operativi</p>
              <p className="section-copy">Accesso rapido ai percorsi principali del modulo.</p>
            </div>
            <div className="space-y-3">
              <Link className="btn-secondary block text-center" href="/presenze/sync">Sync Giornaliere</Link>
              <Link className="btn-secondary block text-center" href="/presenze/giornaliere">Giornaliere</Link>
              <Link className="btn-secondary block text-center" href="/presenze/export">Export XLSM</Link>
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

        {selectedCollaborator ? (
          <div
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4 py-6"
            onClick={() => setSelectedCollaborator(null)}
          >
            <div
              className="flex h-[90vh] w-full max-w-7xl flex-col overflow-hidden rounded-2xl bg-white shadow-2xl"
              onClick={(event) => event.stopPropagation()}
            >
              <div className="flex items-center justify-between gap-4 border-b border-gray-100 px-6 py-4">
                <div className="min-w-0">
                  <p className="section-title">Dettaglio collaboratore</p>
                  <p className="mt-1 truncate text-sm text-gray-500">
                    {[
                      safeDisplay(selectedCollaborator.name),
                      `Matricola ${safeDisplay(selectedCollaborator.employee_code)}`,
                      getPresenzeCompanyLabel(selectedCollaborator.company_label, selectedCollaborator.company_code, ""),
                    ]
                      .filter(Boolean)
                      .join(" · ")}
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <Link className="btn-secondary" href={`/presenze/collaboratori/${selectedCollaborator.id}`} target="_blank">
                    Apri pagina completa
                  </Link>
                  <button className="btn-secondary" type="button" onClick={() => setSelectedCollaborator(null)}>
                    Chiudi
                  </button>
                </div>
              </div>
              <div className="min-h-0 flex-1 bg-[#f7faf7] p-4">
                <iframe
                  className="h-full w-full rounded-2xl border border-gray-200 bg-white"
                  src={`/presenze/collaboratori/${selectedCollaborator.id}?embedded=1`}
                  title={`Dettaglio collaboratore ${safeDisplay(selectedCollaborator.name)}`}
                />
              </div>
            </div>
          </div>
        ) : null}
      </div>
    </ProtectedPage>
  );
}
