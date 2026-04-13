"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

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

export function ElaborazioniBonificaSyncWorkspace() {
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

  async function handleRefresh(): Promise<void> {
    setRefreshing(true);
    setRunMessage(null);
    try {
      await loadAll({ silent: true });
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
      await loadAll({ silent: true });
    } catch (runError) {
      setError(runError instanceof Error ? runError.message : "Errore avvio sync Bonifica");
    } finally {
      setRunning(false);
    }
  }

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

  return (
    <ProtectedPage
      title="Bonifica Oristanese"
      description="Console operativa per avviare e monitorare la sync WhiteCompany: operatori, segnalazioni, mezzi, organigrammi e consorziati."
      breadcrumb="Elaborazioni / Bonifica"
      requiredModule="catasto"
    >
      <ElaborazioneHero
        badge={
          <>
            <RefreshIcon className="h-3.5 w-3.5" />
            Bonifica Sync
          </>
        }
        title="Esecuzione e monitoraggio sync WhiteCompany"
        description="Seleziona le entity da sincronizzare, applica una finestra temporale solo dove previsto e consulta lo stato persistito del runtime."
        actions={
          error ? (
            <ElaborazioneNoticeCard title="Errore" description={error} tone="danger" />
          ) : runMessage ? (
            <ElaborazioneNoticeCard title="Sync avviata" description={runMessage} tone="success" />
          ) : (
            <ElaborazioneNoticeCard
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
    </ProtectedPage>
  );
}

