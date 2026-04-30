"use client";

import { useEffect, useMemo, useState } from "react";

import { AnagraficaModulePage } from "@/components/utenze/anagrafica-module-page";
import {
  getUtenzeAnprConfig,
  getUtenzeAnprJobStatus,
  triggerUtenzeAnprJob,
  updateUtenzeAnprConfig,
} from "@/lib/api";
import { formatDateTime } from "@/lib/presentation";
import type { AnprJobTriggerResult, AnprSyncConfig, AnprSyncConfigUpdateInput, CurrentUser } from "@/types/api";

const POLLING_INTERVAL_MS = 30_000;

type ConfigFormState = {
  max_calls_per_day: number;
  job_enabled: boolean;
  job_cron: string;
  lookback_years: number;
  retry_not_found_days: number;
};

function buildFormState(config: AnprSyncConfig): ConfigFormState {
  return {
    max_calls_per_day: config.max_calls_per_day,
    job_enabled: config.job_enabled,
    job_cron: config.job_cron,
    lookback_years: config.lookback_years,
    retry_not_found_days: config.retry_not_found_days,
  };
}

function isAdminRole(role: string): boolean {
  return role === "admin" || role === "super_admin";
}

function hasRecordedRun(status: AnprJobTriggerResult | null): boolean {
  if (!status) {
    return false;
  }
  if (status.message === "job idle" && status.subjects_processed === 0 && status.deceased_found === 0 && status.errors === 0 && status.calls_used === 0) {
    return false;
  }
  return true;
}

export default function AnprConfigPage() {
  return (
    <AnagraficaModulePage
      title="Configurazione ANPR"
      description="Configurazione job PDND/ANPR e monitoraggio dell’ultima esecuzione."
      breadcrumb="Configurazione ANPR"
    >
      {({ token, currentUser }) => <AnprConfigWorkspace token={token} currentUser={currentUser} />}
    </AnagraficaModulePage>
  );
}

function AnprConfigWorkspace({ token, currentUser }: { token: string; currentUser: CurrentUser }) {
  const [config, setConfig] = useState<AnprSyncConfig | null>(null);
  const [formState, setFormState] = useState<ConfigFormState | null>(null);
  const [jobStatus, setJobStatus] = useState<AnprJobTriggerResult | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [isTriggering, setIsTriggering] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);
  const isAdmin = isAdminRole(currentUser.role);

  useEffect(() => {
    if (!isAdmin) {
      setIsLoading(false);
      return;
    }
    const currentToken = token;

    async function loadData() {
      try {
        const [nextConfig, nextJobStatus] = await Promise.all([
          getUtenzeAnprConfig(currentToken),
          getUtenzeAnprJobStatus(currentToken),
        ]);
        setConfig(nextConfig);
        setFormState(buildFormState(nextConfig));
        setJobStatus(nextJobStatus);
        setError(null);
      } catch (currentError) {
        setError(currentError instanceof Error ? currentError.message : "Impossibile caricare la configurazione ANPR");
      } finally {
        setIsLoading(false);
      }
    }

    void loadData();
  }, [isAdmin, token]);

  useEffect(() => {
    if (!isAdmin) {
      return;
    }
    const currentToken = token;

    const intervalId = window.setInterval(() => {
      void getUtenzeAnprJobStatus(currentToken)
        .then((nextStatus) => {
          setJobStatus(nextStatus);
        })
        .catch(() => {
          // Keep the latest visible status when polling fails.
        });
    }, POLLING_INTERVAL_MS);

    return () => window.clearInterval(intervalId);
  }, [isAdmin, token]);

  const isDirty = useMemo(() => {
    if (!config || !formState) {
      return false;
    }
    return (
      config.max_calls_per_day !== formState.max_calls_per_day ||
      config.job_enabled !== formState.job_enabled ||
      config.job_cron !== formState.job_cron ||
      config.lookback_years !== formState.lookback_years ||
      config.retry_not_found_days !== formState.retry_not_found_days
    );
  }, [config, formState]);

  async function refreshJobStatus() {
    const nextJobStatus = await getUtenzeAnprJobStatus(token);
    setJobStatus(nextJobStatus);
  }

  async function handleSave() {
    if (!formState) {
      return;
    }

    setIsSaving(true);
    setError(null);
    setSaveMessage(null);
    try {
      const payload: AnprSyncConfigUpdateInput = {
        max_calls_per_day: formState.max_calls_per_day,
        job_enabled: formState.job_enabled,
        job_cron: formState.job_cron.trim(),
        lookback_years: formState.lookback_years,
        retry_not_found_days: formState.retry_not_found_days,
      };
      const nextConfig = await updateUtenzeAnprConfig(token, payload);
      setConfig(nextConfig);
      setFormState(buildFormState(nextConfig));
      setSaveMessage("Configurazione ANPR aggiornata.");
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "Impossibile salvare la configurazione ANPR");
    } finally {
      setIsSaving(false);
    }
  }

  async function handleTrigger() {
    setIsTriggering(true);
    setError(null);
    setSaveMessage(null);
    try {
      const result = await triggerUtenzeAnprJob(token);
      setJobStatus(result);
      setSaveMessage("Job ANPR avviato.");
      await refreshJobStatus();
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "Impossibile avviare il job ANPR");
    } finally {
      setIsTriggering(false);
    }
  }

  if (!isAdmin) {
    return (
      <article className="panel-card border border-red-100 bg-red-50/60">
        <p className="text-sm font-medium text-red-700">Accesso non autorizzato</p>
        <p className="mt-1 text-sm text-red-600">Solo gli amministratori possono gestire la configurazione ANPR.</p>
      </article>
    );
  }

  return (
    <>
            {error ? (
              <article className="panel-card border border-red-100 bg-red-50/60">
                <p className="text-sm font-medium text-red-700">Errore configurazione</p>
                <p className="mt-1 text-sm text-red-600">{error}</p>
              </article>
            ) : null}

            {saveMessage ? (
              <article className="panel-card border border-emerald-100 bg-emerald-50/70">
                <p className="text-sm font-medium text-emerald-800">{saveMessage}</p>
              </article>
            ) : null}

            <div className="grid gap-4 xl:grid-cols-[minmax(0,1.2fr)_minmax(320px,0.8fr)]">
              <article className="panel-card">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="section-title">Configurazione job</p>
                    <p className="section-copy mt-1">Parametri operativi del job giornaliero di verifica decessi su PDND/ANPR.</p>
                  </div>
                  <a
                    className="text-sm font-medium text-[#1D4E35] underline underline-offset-4"
                    href="https://crontab.guru/"
                    target="_blank"
                    rel="noreferrer"
                  >
                    Apri crontab.guru
                  </a>
                </div>

                <div className="mt-5 grid gap-4 md:grid-cols-2">
                  <label className="block text-sm font-medium text-gray-700">
                    Max chiamate/giorno
                    <input
                      className="form-control mt-1"
                      type="number"
                      min={1}
                      max={10000}
                      value={formState?.max_calls_per_day ?? ""}
                      onChange={(event) =>
                        setFormState((current) =>
                          current
                            ? { ...current, max_calls_per_day: Math.min(10000, Math.max(1, Number(event.target.value) || 1)) }
                            : current,
                        )
                      }
                      disabled={isLoading || isSaving}
                    />
                  </label>

                  <label className="flex items-center gap-3 rounded-xl border border-[#d8e2d8] bg-[#f8fbf7] px-4 py-3 text-sm font-medium text-gray-700 md:self-end">
                    <input
                      type="checkbox"
                      checked={formState?.job_enabled ?? false}
                      onChange={(event) =>
                        setFormState((current) => (current ? { ...current, job_enabled: event.target.checked } : current))
                      }
                      disabled={isLoading || isSaving}
                    />
                    Job abilitato
                  </label>

                  <label className="block text-sm font-medium text-gray-700 md:col-span-2">
                    Cron job
                    <input
                      className="form-control mt-1"
                      type="text"
                      placeholder="0 2 * * *"
                      value={formState?.job_cron ?? ""}
                      onChange={(event) =>
                        setFormState((current) => (current ? { ...current, job_cron: event.target.value } : current))
                      }
                      disabled={isLoading || isSaving}
                    />
                  </label>

                  <label className="block text-sm font-medium text-gray-700">
                    Lookback anni
                    <input
                      className="form-control mt-1"
                      type="number"
                      min={1}
                      max={10}
                      value={formState?.lookback_years ?? ""}
                      onChange={(event) =>
                        setFormState((current) =>
                          current
                            ? { ...current, lookback_years: Math.min(10, Math.max(1, Number(event.target.value) || 1)) }
                            : current,
                        )
                      }
                      disabled={isLoading || isSaving}
                    />
                  </label>

                  <label className="block text-sm font-medium text-gray-700">
                    Retry not found (giorni)
                    <input
                      className="form-control mt-1"
                      type="number"
                      min={1}
                      max={365}
                      value={formState?.retry_not_found_days ?? ""}
                      onChange={(event) =>
                        setFormState((current) =>
                          current
                            ? { ...current, retry_not_found_days: Math.min(365, Math.max(1, Number(event.target.value) || 1)) }
                            : current,
                        )
                      }
                      disabled={isLoading || isSaving}
                    />
                  </label>
                </div>

                <div className="mt-5 flex flex-wrap items-center gap-3">
                  <button
                    className="btn-primary"
                    type="button"
                    onClick={() => void handleSave()}
                    disabled={isLoading || isSaving || !formState || !isDirty}
                  >
                    {isSaving ? "Salvataggio..." : "Salva configurazione"}
                  </button>
                  <p className="text-sm text-gray-500">
                    {config?.updated_at ? `Ultimo aggiornamento: ${formatDateTime(config.updated_at)}` : "Configurazione di default attiva."}
                  </p>
                </div>
              </article>

              <article className="panel-card">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="section-title">Stato job</p>
                    <p className="section-copy mt-1">Monitoraggio dell’ultima esecuzione disponibile, con polling automatico ogni 30 secondi.</p>
                  </div>
                  <button
                    className="btn-secondary"
                    type="button"
                    onClick={() => void refreshJobStatus()}
                    disabled={isLoading || isTriggering}
                  >
                    Aggiorna
                  </button>
                </div>

                <div className="mt-5 grid gap-3 sm:grid-cols-2">
                  <div className="rounded-xl border border-[#d8e2d8] bg-[#f8fbf7] px-4 py-3 sm:col-span-2">
                    <p className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">Ultima esecuzione</p>
                    <p className="mt-1 text-sm text-gray-800">
                      {hasRecordedRun(jobStatus) ? formatDateTime(jobStatus!.started_at) : "Nessuna esecuzione registrata"}
                    </p>
                    <p className="mt-1 text-xs text-gray-500">{jobStatus?.message ?? "Stato non disponibile"}</p>
                  </div>
                  <div className="rounded-xl border border-gray-100 bg-white px-4 py-3">
                    <p className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">Soggetti verificati</p>
                    <p className="mt-1 text-2xl font-semibold text-gray-900">{jobStatus?.subjects_processed ?? 0}</p>
                  </div>
                  <div className="rounded-xl border border-gray-100 bg-white px-4 py-3">
                    <p className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">Deceduti trovati</p>
                    <p className="mt-1 text-2xl font-semibold text-gray-900">{jobStatus?.deceased_found ?? 0}</p>
                  </div>
                  <div className="rounded-xl border border-gray-100 bg-white px-4 py-3">
                    <p className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">Errori</p>
                    <p className="mt-1 text-2xl font-semibold text-gray-900">{jobStatus?.errors ?? 0}</p>
                  </div>
                  <div className="rounded-xl border border-gray-100 bg-white px-4 py-3">
                    <p className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">Chiamate usate</p>
                    <p className="mt-1 text-2xl font-semibold text-gray-900">{jobStatus?.calls_used ?? 0}</p>
                  </div>
                </div>

                <div className="mt-5 flex flex-wrap items-center gap-3">
                  <button
                    className="btn-primary"
                    type="button"
                    onClick={() => void handleTrigger()}
                    disabled={isLoading || isTriggering || !formState?.job_enabled}
                  >
                    {isTriggering ? "Avvio in corso..." : "Esegui ora"}
                  </button>
                  {!formState?.job_enabled ? (
                    <p className="text-sm text-amber-700">Abilita il job per poter avviare l’esecuzione manuale.</p>
                  ) : null}
                </div>
              </article>
            </div>
    </>
  );
}
