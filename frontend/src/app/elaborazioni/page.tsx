"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { ProtectedPage } from "@/components/app/protected-page";
import {
  ElaborazioneHero,
  ElaborazioneNoticeCard,
  ElaborazionePanelHeader,
} from "@/components/elaborazioni/module-chrome";
import { ModuleWorkspaceKpiRow, ModuleWorkspaceKpiTile } from "@/components/layout/module-workspace-hero";
import { ElaborazioneOperationMessage } from "@/components/elaborazioni/operation-message";
import { ElaborazioneWorkspaceModal } from "@/components/elaborazioni/workspace-modal";
import { EmptyState } from "@/components/ui/empty-state";
import { DocumentIcon, FolderIcon, LockIcon, RefreshIcon, SearchIcon, UsersIcon } from "@/components/ui/icons";
import {
  getElaborazioneBatches,
  getElaborazioneCaptchaSummary,
  getElaborazioneCredentials,
  getBonificaSyncStatus,
  listBonificaOristaneseCredentials,
  listCapacitasCredentials,
  retryFailedElaborazioneBatch,
  startElaborazioneBatch,
} from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import { formatDateTime } from "@/lib/presentation";
import type {
  BonificaOristaneseCredential,
  BonificaSyncStatusResponse,
  CapacitasCredential,
  ElaborazioneBatch,
  ElaborazioneCaptchaSummary,
  ElaborazioneCredentialStatus,
} from "@/types/api";

const DASHBOARD_REFRESH_INTERVAL_MS = 5000;

const QUICK_ACTIONS = [
  {
    href: "/elaborazioni/bonifica",
    title: "WhiteCompany Sync",
    description: "Avvio e monitor sync WhiteCompany.",
    icon: RefreshIcon,
  },
  {
    href: "/elaborazioni/new-single",
    title: "Visure",
    description: "Ingresso unico per visura singola e import batch.",
    icon: SearchIcon,
  },
  {
    href: "/elaborazioni/capacitas",
    title: "Pool operativo dedicato",
    description: "Capacitas e monitor del pool account operativo.",
    icon: UsersIcon,
  },
] as const;

type DashboardModalState = {
  href: string;
  title: string;
  description?: string | null;
};

type DashboardRunningOperation = {
  id: string;
  area: string;
  title: string;
  detail: string;
  startedAt: string | null;
  tone: "default" | "warning" | "success";
  kind: "batch" | "bonifica";
  bonifica?: {
    entity: string;
    records_synced: number | null;
    records_skipped: number | null;
    records_errors: number | null;
    error_detail: string | null;
    last_finished_at: string | null;
  };
};

export default function ElaborazioniPage() {
  const [batches, setBatches] = useState<ElaborazioneBatch[]>([]);
  const [credentialStatus, setCredentialStatus] = useState<ElaborazioneCredentialStatus | null>(null);
  const [captchaSummary, setCaptchaSummary] = useState<ElaborazioneCaptchaSummary | null>(null);
  const [capacitasCredentials, setCapacitasCredentials] = useState<CapacitasCredential[]>([]);
  const [bonificaCredentials, setBonificaCredentials] = useState<BonificaOristaneseCredential[]>([]);
  const [bonificaSyncStatus, setBonificaSyncStatus] = useState<BonificaSyncStatusResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [retryBusyId, setRetryBusyId] = useState<string | null>(null);
  const [modalState, setModalState] = useState<DashboardModalState | null>(null);

  const loadDashboard = useCallback(async (): Promise<void> => {
    const token = getStoredAccessToken();
    if (!token) return;

    try {
      const [credentialsResult, batchesResult, captchaSummaryResult, capacitasResult, bonificaResult, bonificaSyncResult] = await Promise.all([
        getElaborazioneCredentials(token),
        getElaborazioneBatches(token),
        getElaborazioneCaptchaSummary(token),
        listCapacitasCredentials(token),
        listBonificaOristaneseCredentials(token),
        getBonificaSyncStatus(token),
      ]);
      setCredentialStatus(credentialsResult);
      setBatches(batchesResult.slice(0, 6));
      setCaptchaSummary(captchaSummaryResult);
      setCapacitasCredentials(capacitasResult);
      setBonificaCredentials(bonificaResult);
      setBonificaSyncStatus(bonificaSyncResult);
      setError(null);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Errore caricamento dashboard Elaborazioni");
    }
  }, []);

  useEffect(() => {
    void loadDashboard();
  }, [loadDashboard]);

  useEffect(() => {
    function handleVisibilityChange(): void {
      if (document.visibilityState === "visible") {
        void loadDashboard();
      }
    }

    const intervalId = window.setInterval(() => {
      if (document.visibilityState === "visible") {
        void loadDashboard();
      }
    }, DASHBOARD_REFRESH_INTERVAL_MS);

    document.addEventListener("visibilitychange", handleVisibilityChange);

    return () => {
      window.clearInterval(intervalId);
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, [loadDashboard]);

  async function handleRetryBatch(batch: ElaborazioneBatch): Promise<void> {
    const token = getStoredAccessToken();
    if (!token) return;

    setRetryBusyId(batch.id);
    try {
      if (batch.status === "failed" && batch.failed_items > 0) {
        await retryFailedElaborazioneBatch(token, batch.id);
      }
      await startElaborazioneBatch(token, batch.id);
      await loadDashboard();
      setError(null);
    } catch (retryError) {
      setError(retryError instanceof Error ? retryError.message : "Errore riavvio batch");
    } finally {
      setRetryBusyId(null);
    }
  }

  const activeCapacitasCredentials = capacitasCredentials.filter((credential) => credential.active);
  const capacitasWarningCount = capacitasCredentials.filter((credential) => Boolean(credential.last_error)).length;
  const activeBonificaCredentials = bonificaCredentials.filter((credential) => credential.active);
  const bonificaWarningCount = bonificaCredentials.filter((credential) => Boolean(credential.last_error)).length;
  const activeSisterCredentials = credentialStatus?.credentials.filter((credential) => credential.active) ?? [];
  const latestCapacitasUsage = capacitasCredentials
    .map((credential) => credential.last_used_at)
    .filter((value): value is string => Boolean(value))
    .sort()
    .at(-1);
  const latestBonificaUsage = bonificaCredentials
    .map((credential) => credential.last_used_at)
    .filter((value): value is string => Boolean(value))
    .sort()
    .at(-1);
  const quickActions = useMemo(
    () =>
      QUICK_ACTIONS.map((action) => {
        if (action.title === "Pool operativo dedicato") {
          return {
            ...action,
            description:
              capacitasCredentials.length > 0
                ? `${activeCapacitasCredentials.length}/${capacitasCredentials.length} account attivi · ${capacitasWarningCount} warning`
                : "Nessun account Capacitas configurato.",
          };
        }
        if (action.title === "WhiteCompany Sync") {
          const runningCount = Object.values(bonificaSyncStatus?.entities ?? {}).filter((item) => item.status === "running").length;
          return {
            ...action,
            description:
              runningCount > 0
                ? `${runningCount} entity in esecuzione · ultimo uso ${latestBonificaUsage ? formatDateTime(latestBonificaUsage) : "assente"}`
                : `Ultimo uso ${latestBonificaUsage ? formatDateTime(latestBonificaUsage) : "assente"}`,
          };
        }
        if (action.title === "Visure") {
          return {
            ...action,
            description: credentialStatus?.configured
              ? `${activeSisterCredentials.length}/${credentialStatus.credentials.length} credenziali attive · singole e batch nello stesso workspace`
              : "Workspace unico per visure singole e import batch.",
          };
        }
        return action;
      }),
    [
      activeCapacitasCredentials.length,
      activeSisterCredentials.length,
      bonificaSyncStatus,
      capacitasCredentials.length,
      capacitasWarningCount,
      credentialStatus,
      latestBonificaUsage,
    ],
  );
  const runningOperations = useMemo<DashboardRunningOperation[]>(() => {
    const items: DashboardRunningOperation[] = [];

    for (const batch of batches) {
      if (!["pending", "processing"].includes(batch.status)) continue;
      items.push({
        id: `batch-${batch.id}`,
        area: "Batch runtime",
        title: batch.name ?? batch.id,
        detail: batch.current_operation ?? batch.status,
        startedAt: batch.started_at ?? batch.created_at,
        tone: batch.status === "processing" ? "warning" : "default",
        kind: "batch",
      });
    }

    for (const [entityKey, entity] of Object.entries(bonificaSyncStatus?.entities ?? {})) {
      if (entity.status !== "running") continue;
      items.push({
        id: `bonifica-${entityKey}`,
        area: "WhiteCompany Sync",
        title: entityKey,
        detail: "Sync entity in esecuzione",
        startedAt: entity.last_started_at,
        tone: "warning",
        kind: "bonifica",
        bonifica: {
          entity: entity.entity,
          records_synced: entity.records_synced,
          records_skipped: entity.records_skipped,
          records_errors: entity.records_errors,
          error_detail: entity.error_detail,
          last_finished_at: entity.last_finished_at,
        },
      });
    }

    return items.sort((left, right) => {
      const leftTime = left.startedAt ? Date.parse(left.startedAt) : 0;
      const rightTime = right.startedAt ? Date.parse(right.startedAt) : 0;
      return rightTime - leftTime;
    });
  }, [batches, bonificaSyncStatus]);

  function openWorkspaceModal(href: string, title: string, description?: string): void {
    setModalState({ href, title, description });
  }

  return (
    <ProtectedPage
      title="GAIA Elaborazioni"
      description="Workspace operativo per batch, richieste singole, CAPTCHA e monitoraggio esecuzioni del runtime catastale."
      breadcrumb="Elaborazioni"
      requiredModule="catasto"
    >
      <ElaborazioneHero
        badge={
          <>
            <LockIcon className="h-3.5 w-3.5" />
            Workspace Elaborazioni
          </>
        }
        title="Console operativa per richieste, batch, credenziali e pool Capacitas."
        description="Qui restano concentrati i flussi runtime: stato credenziali, attività recenti, CAPTCHA e accesso rapido alle azioni più usate."
        actions={
          error ? (
            <ElaborazioneNoticeCard title="Errore dashboard" description={error} tone="danger" />
          ) : (
            <ElaborazioneNoticeCard
              title="Refresh automatico attivo"
              description="Quando la pagina è in primo piano, i dati vengono ricaricati periodicamente per tenere allineati batch, pool e richieste CAPTCHA."
            />
          )
        }
      >
        <ModuleWorkspaceKpiRow>
          <ModuleWorkspaceKpiTile
            label="SISTER"
            variant="emerald"
            value={credentialStatus?.configured ? "Attivo" : "Setup"}
            hint={
              credentialStatus?.configured
                ? `${activeSisterCredentials.length}/${credentialStatus?.credentials.length ?? 0} attive · ${credentialStatus?.default_credential?.label ?? "default"}`
                : "non configurato"
            }
          />
          <ModuleWorkspaceKpiTile
            label="Capacitas"
            variant="amber"
            value={`${activeCapacitasCredentials.length}/${capacitasCredentials.length}`}
            hint={`${capacitasWarningCount} warning`}
          />
          <ModuleWorkspaceKpiTile
            label="WhiteCompany"
            variant="emerald"
            value={`${activeBonificaCredentials.length}/${bonificaCredentials.length}`}
            hint={`${bonificaWarningCount} warning`}
          />
          <ModuleWorkspaceKpiTile
            label="CAPTCHA"
            value={captchaSummary?.processed ?? 0}
            hint={`${captchaSummary?.correct ?? 0} ok · ${captchaSummary?.wrong ?? 0} ko`}
          />
          <ModuleWorkspaceKpiTile
            label="Ultimo uso"
            value={latestCapacitasUsage ? "Registrato" : "Assente"}
            hint={latestCapacitasUsage ? formatDateTime(latestCapacitasUsage) : "mai"}
          />
        </ModuleWorkspaceKpiRow>
      </ElaborazioneHero>

      <article className="overflow-hidden rounded-[28px] border border-[#d9dfd6] bg-white shadow-panel">
        <ElaborazionePanelHeader
          badge={
            <>
              <RefreshIcon className="h-3.5 w-3.5" />
              Azioni rapide
            </>
          }
          title="Flussi principali del runtime"
          description="Accessi diretti ai percorsi operativi più usati. La barra resta orizzontale per mantenere leggibile la mappa del modulo."
        />
        <div className="p-6">
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {quickActions.map((action) => {
              const Icon = action.icon;
              return (
                <button
                  key={action.href}
                  className="group rounded-2xl border border-gray-100 bg-gray-50 px-4 py-3 text-left transition hover:border-[#c8d8ce] hover:bg-white"
                  onClick={() => openWorkspaceModal(action.href, action.title, action.description)}
                  type="button"
                >
                  <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-white text-[#1D4E35] shadow-sm ring-1 ring-[#dfe8e2] transition group-hover:bg-[#edf5f0]">
                      <Icon className="h-4.5 w-4.5" />
                    </div>
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-gray-900">{action.title}</p>
                      <p className="mt-0.5 line-clamp-2 text-xs leading-5 text-gray-500">{action.description}</p>
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      </article>

      <article className="overflow-hidden rounded-[28px] border border-[#d9dfd6] bg-white shadow-panel">
        <ElaborazionePanelHeader
          badge={
            <>
              <RefreshIcon className="h-3.5 w-3.5" />
              Operazioni in corso
            </>
          }
          title="Esecuzioni attive aggregate"
          description="Vista unica delle operazioni attualmente in lavorazione: batch runtime e sync WhiteCompany ancora aperte."
        />
        <div className="p-6">
          {runningOperations.length === 0 ? (
            <EmptyState icon={RefreshIcon} title="Nessuna operazione attiva" description="Al momento non risultano batch in processing o sync WhiteCompany in esecuzione." />
          ) : (
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
              {runningOperations.map((operation) => (
                <article
                  key={operation.id}
                  className="flex h-full flex-col justify-between gap-4 rounded-3xl border border-gray-100 bg-gray-50 p-4"
                >
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div className="min-w-0">
                        <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-gray-400">{operation.area}</p>
                        <p className="mt-1 truncate text-sm font-medium text-gray-900">{operation.title}</p>
                      </div>
                      <span
                        className={`inline-flex shrink-0 rounded-full px-2 py-1 text-[11px] font-semibold ${
                          operation.tone === "warning"
                            ? "bg-amber-50 text-amber-700"
                            : operation.tone === "success"
                              ? "bg-emerald-50 text-emerald-700"
                              : "bg-gray-100 text-gray-700"
                        }`}
                      >
                        attiva
                      </span>
                    </div>

                    <p className="mt-2 line-clamp-2 text-sm text-gray-600">{operation.detail}</p>
                    <p className="mt-2 text-xs text-gray-500">Avvio: {formatDateTime(operation.startedAt)}</p>

                    {operation.kind === "bonifica" && operation.bonifica ? (
                      <div className="mt-4 grid gap-2 text-xs text-gray-600 sm:grid-cols-2">
                        <div className="rounded-2xl bg-white px-3 py-2 ring-1 ring-gray-100">
                          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-gray-400">Synced</p>
                          <p className="mt-1 text-sm font-semibold text-emerald-700">{operation.bonifica.records_synced ?? "—"}</p>
                        </div>
                        <div className="rounded-2xl bg-white px-3 py-2 ring-1 ring-gray-100">
                          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-gray-400">Errors</p>
                          <p className="mt-1 text-sm font-semibold text-red-700">{operation.bonifica.records_errors ?? "—"}</p>
                        </div>
                        <div className="rounded-2xl bg-white px-3 py-2 ring-1 ring-gray-100">
                          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-gray-400">Skipped</p>
                          <p className="mt-1 text-sm font-semibold text-slate-700">{operation.bonifica.records_skipped ?? "—"}</p>
                        </div>
                        <div className="rounded-2xl bg-white px-3 py-2 ring-1 ring-gray-100">
                          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-gray-400">Ultimo fine</p>
                          <p className="mt-1 text-sm font-semibold text-gray-900">
                            {operation.bonifica.last_finished_at ? formatDateTime(operation.bonifica.last_finished_at) : "—"}
                          </p>
                        </div>
                        {operation.bonifica.error_detail ? (
                          <div className="sm:col-span-2">
                            <div className="rounded-2xl border border-amber-100 bg-amber-50 px-3 py-2">
                              <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-amber-700">Errore</p>
                              <p className="mt-1 break-words text-sm text-amber-900">{operation.bonifica.error_detail}</p>
                            </div>
                          </div>
                        ) : null}
                      </div>
                    ) : null}
                  </div>
                </article>
              ))}
            </div>
          )}
        </div>
      </article>

      <article className="overflow-hidden rounded-[28px] border border-[#d9dfd6] bg-white p-0 shadow-panel">
        <ElaborazionePanelHeader
          badge={
            <>
              <FolderIcon className="h-3.5 w-3.5" />
              Batch recenti
            </>
          }
          title="Ultimi lotti creati dall'utente corrente"
          description="Sotto restano solo l'elenco batch e le azioni di retry, senza duplicare i pannelli operativi superiori."
        />
        {batches.length === 0 ? (
          <div className="p-5">
            <EmptyState icon={SearchIcon} title="Nessun batch presente" description="Apri /elaborazioni/new-batch per creare una richiesta o importare un lotto." />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Nome</th>
                  <th>Stato</th>
                  <th>Totale</th>
                  <th>Operazione</th>
                  <th>Creato</th>
                  <th>Azioni</th>
                </tr>
              </thead>
              <tbody>
                {batches.map((batch) => (
                  <tr key={batch.id}>
                    <td>
                      <button
                        className="font-medium text-[#1D4E35] transition hover:text-[#143726]"
                        onClick={() =>
                          openWorkspaceModal(
                            `/elaborazioni/batches/${batch.id}`,
                            batch.name ?? "Dettaglio batch",
                            "Dettaglio batch aperto in modale per consultare stato, richieste e CAPTCHA senza lasciare la dashboard.",
                          )
                        }
                        type="button"
                      >
                        {batch.name ?? batch.id}
                      </button>
                    </td>
                    <td>{batch.status}</td>
                    <td>{batch.total_items}</td>
                    <td><ElaborazioneOperationMessage value={batch.current_operation} /></td>
                    <td>{formatDateTime(batch.created_at)}</td>
                    <td>
                      {batch.current_operation === "Retry queued" || (batch.status === "failed" && batch.failed_items > 0) ? (
                        <button
                          className="text-sm text-[#1D4E35] transition hover:text-[#143726] disabled:cursor-not-allowed disabled:text-gray-300"
                          disabled={retryBusyId === batch.id}
                          onClick={() => void handleRetryBatch(batch)}
                          type="button"
                        >
                          {retryBusyId === batch.id ? "Riprovo..." : "Riprova"}
                        </button>
                      ) : (
                        "—"
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </article>
      <ElaborazioneWorkspaceModal
        description={modalState?.description}
        href={modalState?.href ?? null}
        onClose={() => setModalState(null)}
        open={modalState != null}
        title={modalState?.title ?? "Workspace"}
      />
    </ProtectedPage>
  );
}
