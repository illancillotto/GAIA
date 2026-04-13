"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";

import { ProtectedPage } from "@/components/app/protected-page";
import {
  ElaborazioneHero,
  ElaborazioneMiniStat,
  ElaborazioneNoticeCard,
  ElaborazionePanelHeader,
} from "@/components/elaborazioni/module-chrome";
import { EmptyState } from "@/components/ui/empty-state";
import { CheckIcon, LockIcon, RefreshIcon } from "@/components/ui/icons";
import { getBonificaSyncStatus, getCurrentUser, listBonificaOristaneseCredentials, runBonificaSync } from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import { formatDateTime } from "@/lib/presentation";
import type { BonificaOristaneseCredential, BonificaSyncEntityStatus, BonificaSyncStatusResponse, CurrentUser } from "@/types/api";

const ENTITY_DEFINITIONS: Array<{
  key: string;
  label: string;
  description: string;
  dateAware: boolean;
}> = [
  {
    key: "report_types",
    label: "Tipologie segnalazione",
    description: "Lookup categorie segnalazione per il modulo Operazioni.",
    dateAware: false,
  },
  {
    key: "reports",
    label: "Segnalazioni",
    description: "Import segnalazioni WhiteCompany (date range applicabile).",
    dateAware: true,
  },
  {
    key: "vehicles",
    label: "Automezzi e attrezzature",
    description: "Lookup mezzi e attrezzature WhiteCompany.",
    dateAware: false,
  },
  {
    key: "refuels",
    label: "Registro rifornimenti",
    description: "Import rifornimenti WhiteCompany (date range applicabile).",
    dateAware: true,
  },
  {
    key: "taken_charge",
    label: "Prese in carico automezzi",
    description: "Import prese in carico WhiteCompany (date range applicabile).",
    dateAware: true,
  },
  {
    key: "users",
    label: "Operatori WhiteCompany (NO consorziati)",
    description: "Upsert in `wc_operator` con link opzionale a `application_users` via email.",
    dateAware: false,
  },
  {
    key: "areas",
    label: "Aree territoriali",
    description: "Lookup aree WhiteCompany per Operazioni.",
    dateAware: false,
  },
  {
    key: "warehouse_requests",
    label: "Richieste magazzino",
    description: "Import richieste magazzino (date range applicabile) verso Inventory.",
    dateAware: true,
  },
  {
    key: "org_charts",
    label: "Organigrammi",
    description: "Import organigrammi verso Accessi (chart + entries).",
    dateAware: false,
  },
  {
    key: "consorziati",
    label: "Consorziati (staging Utenze)",
    description: "Staging in `bonifica_user_staging` con approvazione manuale verso `ana_subjects`.",
    dateAware: false,
  },
];

type SyncLogEntry = {
  id: string;
  at: string;
  tone: "info" | "success" | "warning" | "danger";
  message: string;
};

function statusTone(status: string): "default" | "success" | "warning" {
  if (status === "completed") return "success";
  if (status === "running") return "warning";
  return "default";
}

function normalizeEntityKeys(entities: BonificaSyncStatusResponse | null): string[] {
  if (!entities) return [];
  return Object.keys(entities.entities ?? {});
}

function resolveStatus(status: BonificaSyncEntityStatus | undefined): BonificaSyncEntityStatus | null {
  return status ?? null;
}

function isAdminUser(user: CurrentUser | null): boolean {
  return Boolean(user && (user.role === "admin" || user.role === "super_admin"));
}

function isValidIsoDate(value: string): boolean {
  return /^\d{4}-\d{2}-\d{2}$/.test(value);
}

export function ElaborazioniBonificaSyncWorkspace({ embedded = false }: { embedded?: boolean } = {}) {
  const [currentUser, setCurrentUser] = useState<CurrentUser | null>(null);
  const [syncStatus, setSyncStatus] = useState<BonificaSyncStatusResponse | null>(null);
  const [bonificaCredentials, setBonificaCredentials] = useState<BonificaOristaneseCredential[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [runMessage, setRunMessage] = useState<string | null>(null);
  const [selectedEntities, setSelectedEntities] = useState<string[]>([]);
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [runStartedAt, setRunStartedAt] = useState<string | null>(null);
  const [syncLog, setSyncLog] = useState<SyncLogEntry[]>([]);
  const previousStatusesRef = useRef<Record<string, string>>({});
  const lastRunEntityKeysRef = useRef<string[]>([]);
  const runCompletionLoggedRef = useRef(false);

  const admin = isAdminUser(currentUser);
  const entityStatusByKey = syncStatus?.entities ?? {};
  const availableEntityKeys = useMemo(() => normalizeEntityKeys(syncStatus), [syncStatus]);
  const selectedEntityDefinitions = useMemo(
    () => ENTITY_DEFINITIONS.filter((entity) => selectedEntities.includes(entity.key)),
    [selectedEntities],
  );
  const hasDateAwareSelection = selectedEntityDefinitions.some((entity) => entity.dateAware);
  const activeBonificaCredentialsCount = useMemo(
    () => bonificaCredentials.filter((credential) => credential.active).length,
    [bonificaCredentials],
  );
  const hasActiveBonificaCredential = activeBonificaCredentialsCount > 0;
  const bonificaWarningCount = useMemo(
    () => bonificaCredentials.filter((credential) => credential.active && Boolean(credential.last_error)).length,
    [bonificaCredentials],
  );
  const latestBonificaIssue = useMemo(() => {
    const messages = bonificaCredentials
      .filter((credential) => credential.active && Boolean(credential.last_error))
      .map((credential) => credential.last_error)
      .filter((value): value is string => Boolean(value));
    return messages.at(0) ?? null;
  }, [bonificaCredentials]);

  const entityOrder = useMemo(() => {
    const keys = ENTITY_DEFINITIONS.map((item) => item.key);
    if (availableEntityKeys.length === 0) return keys;
    const extra = availableEntityKeys.filter((key) => !keys.includes(key));
    return [...keys, ...extra];
  }, [availableEntityKeys]);

  const defaultEntityKeys = useMemo(() => ENTITY_DEFINITIONS.map((entity) => entity.key), []);
  const targetEntityKeys = useMemo(
    () => (selectedEntities.length > 0 ? selectedEntities : defaultEntityKeys),
    [defaultEntityKeys, selectedEntities],
  );

  const progress = useMemo(() => {
    if (!syncStatus) {
      return { percent: 0, finished: 0, total: targetEntityKeys.length, runningKeys: [] as string[] };
    }
    const startedAfter = runStartedAt ? Date.parse(runStartedAt) : null;
    const statuses = syncStatus.entities ?? {};
    const runningKeys = targetEntityKeys.filter((key) => statuses[key]?.status === "running");
    const finishedKeys = targetEntityKeys.filter((key) => {
      const status = statuses[key];
      if (!status) return false;
      if (startedAfter != null) {
        const startedAt = status.last_started_at ? Date.parse(status.last_started_at) : null;
        if (startedAt == null || Number.isNaN(startedAt) || startedAt < startedAfter) return false;
      }
      return status.status === "completed" || status.status === "failed";
    });
    const total = targetEntityKeys.length || 1;
    const finished = finishedKeys.length;
    const percent = Math.min(100, Math.round((finished / total) * 100));
    return { percent, finished, total: targetEntityKeys.length, runningKeys };
  }, [runStartedAt, syncStatus, targetEntityKeys]);

  const activeJobsCount = useMemo(() => {
    if (!syncStatus) return 0;
    return Object.values(syncStatus.entities).filter((item) => item.status === "running").length;
  }, [syncStatus]);

  const failedJobsCount = useMemo(() => {
    if (!syncStatus) return 0;
    return Object.values(syncStatus.entities).filter((item) => item.status === "failed").length;
  }, [syncStatus]);

  const completedJobsCount = useMemo(() => {
    if (!syncStatus) return 0;
    return Object.values(syncStatus.entities).filter((item) => item.status === "completed").length;
  }, [syncStatus]);

  function appendLog(message: string, tone: SyncLogEntry["tone"] = "info"): void {
    const entryAt = new Date().toISOString();
    setSyncLog((current) => [
      {
        id: `${entryAt}-${current.length}`,
        at: entryAt,
        tone,
        message,
      },
      ...current,
    ].slice(0, 80));
  }

  async function loadAll({ silent = false }: { silent?: boolean } = {}): Promise<void> {
    const token = getStoredAccessToken();
    if (!token) return;

    if (!silent) {
      setLoading(true);
    }
    try {
      const [user, status, credentials] = await Promise.all([
        getCurrentUser(token),
        getBonificaSyncStatus(token),
        listBonificaOristaneseCredentials(token),
      ]);
      setCurrentUser(user);
      setSyncStatus(status);
      setBonificaCredentials(credentials);
      setError(null);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Errore caricamento stato sync Bonifica");
    } finally {
      if (!silent) {
        setLoading(false);
      }
    }
  }

  useEffect(() => {
    void loadAll();
  }, []);

  useEffect(() => {
    if (!admin) return;
    const activeJobs = syncStatus ? Object.values(syncStatus.entities ?? {}).filter((item) => item.status === "running").length : 0;
    if (!runStartedAt && activeJobs === 0) return;
    if (activeJobs === 0 && !running) return;

    const intervalId = window.setInterval(() => {
      void loadAll({ silent: true });
    }, 3000);

    return () => window.clearInterval(intervalId);
  }, [admin, runStartedAt, running, syncStatus]);

  useEffect(() => {
    if (!syncStatus) return;

    const trackedKeys = lastRunEntityKeysRef.current;
    if (trackedKeys.length === 0) {
      previousStatusesRef.current = Object.fromEntries(
        Object.entries(syncStatus.entities ?? {}).map(([key, value]) => [key, value.status]),
      );
      return;
    }

    const currentStatuses = syncStatus.entities ?? {};
    for (const key of trackedKeys) {
      const previousStatus = previousStatusesRef.current[key];
      const nextStatus = currentStatuses[key]?.status;
      if (!nextStatus || previousStatus === nextStatus) continue;

      const entityLabel = ENTITY_DEFINITIONS.find((item) => item.key === key)?.label ?? key;
      if (nextStatus === "running") {
        appendLog(`${entityLabel}: job in esecuzione.`, "warning");
      } else if (nextStatus === "completed") {
        const synced = currentStatuses[key]?.records_synced ?? 0;
        const skipped = currentStatuses[key]?.records_skipped ?? 0;
        appendLog(`${entityLabel}: completata. Synced ${synced}, skipped ${skipped}.`, "success");
      } else if (nextStatus === "failed") {
        const detail = currentStatuses[key]?.error_detail;
        appendLog(`${entityLabel}: fallita${detail ? ` — ${detail}` : "."}`, "danger");
      }
    }

    previousStatusesRef.current = Object.fromEntries(
      Object.entries(currentStatuses).map(([key, value]) => [key, value.status]),
    );
  }, [syncStatus]);

  useEffect(() => {
    if (!runStartedAt || progress.total === 0) return;
    if (progress.finished < progress.total) return;
    if (runCompletionLoggedRef.current) return;
    runCompletionLoggedRef.current = true;
    appendLog(`Sync completata: ${progress.finished}/${progress.total} entity chiuse.`, failedJobsCount > 0 ? "warning" : "success");
    lastRunEntityKeysRef.current = [];
  }, [failedJobsCount, progress.finished, progress.total, runStartedAt]);

  async function handleRefresh(): Promise<void> {
    setRefreshing(true);
    setRunMessage(null);
    try {
      await loadAll({ silent: true });
      appendLog("Stato sync aggiornato manualmente.", "info");
    } finally {
      setRefreshing(false);
    }
  }

  function toggleEntity(key: string): void {
    setSelectedEntities((current) => {
      if (current.includes(key)) {
        return current.filter((item) => item !== key);
      }
      return [...current, key];
    });
  }

  function selectAllEntities(): void {
    setSelectedEntities(defaultEntityKeys);
  }

  function clearEntitySelection(): void {
    setSelectedEntities([]);
  }

  async function handleRunSync(): Promise<void> {
    const token = getStoredAccessToken();
    if (!token) return;

    if (!hasActiveBonificaCredential) {
      setError("Nessuna credenziale Bonifica attiva. Configura almeno un account nel pool prima di avviare la sync.");
      return;
    }

    setRunning(true);
    setRunMessage(null);
    setError(null);
    try {
      const entitiesToRun = selectedEntities.length > 0 ? selectedEntities : defaultEntityKeys;
      const payload: Record<string, unknown> = {
        entities: selectedEntities.length > 0 ? selectedEntities : "all",
      };
      if (hasDateAwareSelection) {
        payload.date_from = isValidIsoDate(dateFrom) ? dateFrom : null;
        payload.date_to = isValidIsoDate(dateTo) ? dateTo : null;
      }
      const response = await runBonificaSync(token, payload as never);
      const jobSummary = Object.entries(response.jobs ?? {})
        .map(([entity, job]) => `${entity}: ${job.status}`)
        .join(" · ");
      setRunMessage(jobSummary || "Sync avviata.");
      const startedAt = new Date().toISOString();
      setRunStartedAt(startedAt);
      setSyncLog([]);
      lastRunEntityKeysRef.current = entitiesToRun;
      runCompletionLoggedRef.current = false;
      appendLog(`Avvio sync WhiteCompany su ${entitiesToRun.length} entity.`, "info");
      for (const [entity, job] of Object.entries(response.jobs ?? {})) {
        const entityLabel = ENTITY_DEFINITIONS.find((item) => item.key === entity)?.label ?? entity;
        appendLog(`${entityLabel}: job creato (${job.status}).`, job.status === "running" ? "warning" : "info");
      }
      await loadAll({ silent: true });
    } catch (runError) {
      setError(runError instanceof Error ? runError.message : "Errore avvio sync Bonifica");
      appendLog(runError instanceof Error ? `Errore avvio sync: ${runError.message}` : "Errore avvio sync Bonifica.", "danger");
    } finally {
      setRunning(false);
    }
  }

  const content = (
    <>
      <ElaborazioneHero
        compact
        badge={
          <>
            <RefreshIcon className="h-3.5 w-3.5" />
            WhiteCompany Sync
          </>
        }
        title="Sync WhiteCompany"
        description="Seleziona le entity e avvia la sync. Per entity date-aware puoi usare date_from/date_to."
        actions={
          error ? (
            <ElaborazioneNoticeCard compact title="Errore" description={error} tone="danger" />
          ) : runMessage ? (
            <ElaborazioneNoticeCard compact title="Sync avviata" description={runMessage} tone="success" />
          ) : (
            <ElaborazioneNoticeCard
              compact
              title="Split utenti"
              description="`users` sincronizza solo operatori (esclude Consorziati). `consorziati` alimenta lo staging Utenze e richiede approvazione manuale."
            />
          )
        }
      >
        <div className="grid gap-3 sm:grid-cols-3">
          <ElaborazioneMiniStat eyebrow="Running" value={activeJobsCount} description="Entity attualmente in esecuzione." tone={activeJobsCount > 0 ? "warning" : "default"} />
          <ElaborazioneMiniStat eyebrow="Completed" value={completedJobsCount} description="Ultimi job completati con successo." tone={completedJobsCount > 0 ? "success" : "default"} />
          <ElaborazioneMiniStat eyebrow="Failed" value={failedJobsCount} description="Entity con ultimo job fallito." tone={failedJobsCount > 0 ? "warning" : "default"} />
        </div>
      </ElaborazioneHero>

      <article className="overflow-hidden rounded-[28px] border border-[#d9dfd6] bg-white shadow-panel">
        <ElaborazionePanelHeader
          badge={
            <>
              <LockIcon className="h-3.5 w-3.5" />
              Avvio sync
            </>
          }
          title="Seleziona entity e avvia"
          description="La sync richiede ruolo admin/super_admin. Per entity date-aware puoi indicare date_from/date_to (YYYY-MM-DD)."
        />
        <div className="space-y-6 p-6">
          {runStartedAt ? (
            <div className="rounded-2xl border border-[#cfe0d3] bg-[#f5faf6] px-4 py-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[#5b7862]">Progress sync</p>
                  <div className="mt-1 text-sm text-gray-700">
                    <span className="font-semibold">{progress.finished}</span> / {progress.total} entity chiuse
                  </div>
                  {progress.runningKeys.length > 0 ? (
                    <p className="mt-1 text-xs text-gray-500">In corso: {progress.runningKeys.join(", ")}</p>
                  ) : null}
                </div>
                <div className="rounded-full bg-white px-3 py-1 text-sm font-semibold text-[#1D4E35] shadow-sm">{progress.percent}%</div>
              </div>
              <div className="mt-3 h-3 w-full overflow-hidden rounded-full bg-white shadow-inner">
                <div className="h-full rounded-full bg-[#1D4E35] transition-all duration-500" style={{ width: `${progress.percent}%` }} />
              </div>
            </div>
          ) : null}
          {!admin ? (
            <div className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
              Questa console e disponibile solo per utenti con ruolo <span className="font-semibold">admin</span> o{" "}
              <span className="font-semibold">super_admin</span>. Puoi comunque consultare lo stato se hai accesso alla pagina.
            </div>
          ) : null}
          {admin && !hasActiveBonificaCredential ? (
            <div className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
              Nessuna credenziale Bonifica risulta <span className="font-semibold">attiva</span> nel pool. Vai su{" "}
              <Link href="/elaborazioni/settings" className="font-semibold text-[#1D4E35] hover:text-[#143726]">
                Credenziali
              </Link>{" "}
              e abilita almeno un account prima di avviare la sync.
            </div>
          ) : null}
          {admin && hasActiveBonificaCredential && bonificaWarningCount > 0 ? (
            <div className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
              Il pool Bonifica ha {bonificaWarningCount} credenziali <span className="font-semibold">attive</span> con warning recenti
              (`last_error`). Prima di lanciare la sync, esegui un <span className="font-semibold">Test</span> dalla pagina{" "}
              <Link href="/elaborazioni/settings" className="font-semibold text-[#1D4E35] hover:text-[#143726]">
                Credenziali
              </Link>
              {latestBonificaIssue ? (
                <>
                  <span className="mx-2 text-amber-700">·</span>
                  <span className="text-amber-800" title={latestBonificaIssue}>
                    Ultimo errore: {latestBonificaIssue}
                  </span>
                </>
              ) : null}
              .
            </div>
          ) : null}

          <div className="grid gap-3 lg:grid-cols-2">
            <div className="rounded-2xl border border-gray-100 bg-gray-50 p-4">
              <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-gray-400">Entity</p>
              <div className="mt-3 flex flex-wrap gap-2">
                <button className="btn-secondary" type="button" disabled={!admin || running} onClick={selectAllEntities}>
                  Seleziona tutte
                </button>
                <button className="btn-secondary" type="button" disabled={!admin || running} onClick={clearEntitySelection}>
                  Pulisci
                </button>
              </div>
              <div className="mt-3 space-y-2">
                {ENTITY_DEFINITIONS.map((entity) => (
                  <label key={entity.key} className="flex items-start gap-3 rounded-xl border border-white bg-white/80 px-3 py-2.5">
                    <input
                      type="checkbox"
                      className="mt-1 h-4 w-4 accent-[#1D4E35]"
                      checked={selectedEntities.includes(entity.key)}
                      onChange={() => toggleEntity(entity.key)}
                      disabled={!admin || running}
                    />
                    <span className="min-w-0">
                      <span className="block text-sm font-medium text-gray-900">{entity.label}</span>
                      <span className="mt-1 block text-xs text-gray-500">{entity.description}</span>
                      {entity.key === "consorziati" ? (
                        <span className="mt-2 block text-xs">
                          <Link href="/utenze/bonifica-staging" className="font-medium text-[#1D4E35] hover:text-[#143726]" target="_blank">
                            Apri staging consorziati
                          </Link>
                        </span>
                      ) : null}
                    </span>
                    {entity.dateAware ? (
                      <span className="ml-auto inline-flex shrink-0 items-center gap-1 rounded-full bg-amber-50 px-2 py-1 text-[11px] font-semibold text-amber-700">
                        Date
                      </span>
                    ) : null}
                  </label>
                ))}
              </div>
              <p className="mt-3 text-xs text-gray-500">
                Se non selezioni nulla, verra usato <span className="font-semibold">entities=all</span>.
              </p>
            </div>

            <div className="space-y-4">
              <div className="rounded-2xl border border-gray-100 bg-gray-50 p-4">
                <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-gray-400">Finestra temporale</p>
                <p className="mt-2 text-sm text-gray-600">
                  Applicata solo a: <span className="font-semibold">reports, refuels, taken_charge, warehouse_requests</span>. Se vuota,
                  il backend usa i default (es. ultimi 30 giorni).
                </p>
                <div className="mt-4 grid gap-3 md:grid-cols-2">
                  <label className="space-y-2">
                    <span className="label-caption">Da (YYYY-MM-DD)</span>
                    <input
                      className="form-control"
                      value={dateFrom}
                      onChange={(event) => setDateFrom(event.target.value)}
                      placeholder="2026-04-01"
                      disabled={!admin || running || !hasDateAwareSelection}
                    />
                  </label>
                  <label className="space-y-2">
                    <span className="label-caption">A (YYYY-MM-DD)</span>
                    <input
                      className="form-control"
                      value={dateTo}
                      onChange={(event) => setDateTo(event.target.value)}
                      placeholder="2026-04-13"
                      disabled={!admin || running || !hasDateAwareSelection}
                    />
                  </label>
                </div>
                {!hasDateAwareSelection ? (
                  <p className="mt-3 text-xs text-gray-500">
                    Seleziona almeno una entity date-aware per abilitare i campi data.
                  </p>
                ) : null}
              </div>

              <div className="flex flex-wrap gap-3">
                <button className="btn-secondary" type="button" disabled={refreshing || loading} onClick={() => void handleRefresh()}>
                  {refreshing ? "Aggiorno..." : "Aggiorna stato"}
                </button>
                <button
                  className="btn-primary"
                  type="button"
                  disabled={!admin || running || loading || !hasActiveBonificaCredential}
                  onClick={() => void handleRunSync()}
                >
                  {running ? "Sync in corso..." : "Avvia sync"}
                </button>
              </div>
            </div>
          </div>
        </div>
      </article>

      <article className="overflow-hidden rounded-[28px] border border-[#d9dfd6] bg-white shadow-panel">
        <ElaborazionePanelHeader
          badge={
            <>
              <RefreshIcon className="h-3.5 w-3.5" />
              Log
            </>
          }
          title="Log operativo"
          description="Eventi locali della run corrente: avvio job, polling stato, completamenti e fallimenti per entity."
        />
        <div className="p-6">
          {syncLog.length === 0 ? (
            <EmptyState icon={RefreshIcon} title="Nessun log disponibile" description="Avvia una sync o aggiorna lo stato per popolare il log operativo." />
          ) : (
            <div className="max-h-[22rem] space-y-2 overflow-y-auto pr-2">
              {syncLog.map((entry) => {
                const toneClassName =
                  entry.tone === "success"
                    ? "border-emerald-100 bg-emerald-50 text-emerald-800"
                    : entry.tone === "warning"
                      ? "border-amber-100 bg-amber-50 text-amber-800"
                      : entry.tone === "danger"
                        ? "border-rose-100 bg-rose-50 text-rose-800"
                        : "border-gray-100 bg-gray-50 text-gray-700";

                return (
                  <div key={entry.id} className={`rounded-2xl border px-3 py-2 ${toneClassName}`}>
                    <div className="flex items-start justify-between gap-3">
                      <p className="text-sm">{entry.message}</p>
                      <span className="shrink-0 text-[11px] font-medium opacity-70">{formatDateTime(entry.at)}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </article>

      <article className="overflow-hidden rounded-[28px] border border-[#d9dfd6] bg-white shadow-panel">
        <ElaborazionePanelHeader
          badge={
            <>
              <CheckIcon className="h-3.5 w-3.5" />
              Stato
            </>
          }
          title="Stato per entity"
          description="Stato derivato da `wc_sync_job`. `never` indica che non esistono run precedenti per l'entity."
        />
        <div className="p-6">
          {loading ? (
            <p className="text-sm text-gray-500">Caricamento stato sync in corso...</p>
          ) : !syncStatus ? (
            <EmptyState icon={RefreshIcon} title="Nessuno stato disponibile" description="Impossibile leggere lo stato della sync dal backend." />
          ) : (
            <div className="overflow-x-auto">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Entity</th>
                    <th>Stato</th>
                    <th>Ultimo avvio</th>
                    <th>Ultimo termine</th>
                    <th>Synced</th>
                    <th>Skipped</th>
                    <th>Errori</th>
                    <th>Dettaglio</th>
                  </tr>
                </thead>
                <tbody>
                  {entityOrder.map((entityKey) => {
                    const status = resolveStatus(entityStatusByKey[entityKey]);
                    const definition = ENTITY_DEFINITIONS.find((item) => item.key === entityKey);
                    if (!status) {
                      return (
                        <tr key={entityKey}>
                          <td className="font-medium text-gray-900">{definition?.label ?? entityKey}</td>
                          <td colSpan={7} className="text-sm text-gray-500">
                            Stato non disponibile.
                          </td>
                        </tr>
                      );
                    }
                    const badgeTone = statusTone(status.status);
                    const badgeClassName =
                      badgeTone === "success"
                        ? "bg-emerald-50 text-emerald-700"
                        : badgeTone === "warning"
                          ? "bg-amber-50 text-amber-700"
                          : "bg-gray-100 text-gray-700";
                    const detailPreview = status.error_detail ? status.error_detail.split("\n").slice(0, 2).join(" · ") : "";
                    return (
                      <tr key={entityKey}>
                        <td className="min-w-[14rem]">
                          <p className="font-medium text-gray-900">{definition?.label ?? entityKey}</p>
                          <p className="mt-1 text-xs text-gray-400">{entityKey}</p>
                        </td>
                        <td>
                          <span className={`inline-flex rounded-full px-2 py-1 text-[11px] font-semibold ${badgeClassName}`}>{status.status}</span>
                        </td>
                        <td className="text-sm text-gray-600">{formatDateTime(status.last_started_at)}</td>
                        <td className="text-sm text-gray-600">{formatDateTime(status.last_finished_at)}</td>
                        <td className="text-sm text-gray-600">{status.records_synced ?? "—"}</td>
                        <td className="text-sm text-gray-600">{status.records_skipped ?? "—"}</td>
                        <td className="text-sm text-gray-600">{status.records_errors ?? "—"}</td>
                        <td className="max-w-[34ch] truncate text-xs text-gray-500" title={status.error_detail ?? undefined}>
                          {detailPreview || "—"}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </article>
    </>
  );

  if (embedded) {
    return <div className="space-y-6">{content}</div>;
  }

  return (
    <ProtectedPage
      title="Bonifica Oristanese"
      description="Console operativa per avviare e monitorare la sync WhiteCompany: operatori, segnalazioni, mezzi, organigrammi e consorziati."
      breadcrumb="Elaborazioni / Bonifica"
      requiredModule="catasto"
    >
      {content}
    </ProtectedPage>
  );
}
