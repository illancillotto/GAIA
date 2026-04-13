"use client";

import { useCallback, useEffect, useState } from "react";

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
  listBonificaOristaneseCredentials,
  listCapacitasCredentials,
  retryFailedElaborazioneBatch,
  startElaborazioneBatch,
} from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import { formatDateTime } from "@/lib/presentation";
import type {
  BonificaOristaneseCredential,
  CapacitasCredential,
  ElaborazioneBatch,
  ElaborazioneCaptchaSummary,
  ElaborazioneCredentialStatus,
} from "@/types/api";

const DASHBOARD_REFRESH_INTERVAL_MS = 5000;

const QUICK_ACTIONS = [
  {
    href: "/elaborazioni/settings",
    title: "Credenziali",
    description: "Accesso e configurazione account operativi.",
    icon: LockIcon,
  },
  {
    href: "/elaborazioni/whitecompany",
    title: "WhiteCompany",
    description: "Console sync, credenziali e staging consorziati.",
    icon: RefreshIcon,
  },
  {
    href: "/elaborazioni/new-batch",
    title: "Import batch",
    description: "Upload CSV o XLSX con preview e avvio worker.",
    icon: FolderIcon,
  },
  {
    href: "/elaborazioni/new-single",
    title: "Visura singola",
    description: "Richiesta puntuale per immobile o soggetto.",
    icon: SearchIcon,
  },
  {
    href: "/elaborazioni/capacitas",
    title: "Capacitas",
    description: "Ricerca anagrafica e monitor pool account.",
    icon: UsersIcon,
  },
  {
    href: "/elaborazioni/batches",
    title: "Archivio batch",
    description: "Esiti, progress e retry dei lotti.",
    icon: DocumentIcon,
  },
  {
    href: "/catasto/archive?view=documents",
    title: "Archivio documenti",
    description: "Consultazione PDF e documenti acquisiti.",
    icon: DocumentIcon,
  },
] as const;

type DashboardModalState = {
  href: string;
  title: string;
  description?: string | null;
};

export default function ElaborazioniPage() {
  const [batches, setBatches] = useState<ElaborazioneBatch[]>([]);
  const [credentialStatus, setCredentialStatus] = useState<ElaborazioneCredentialStatus | null>(null);
  const [captchaSummary, setCaptchaSummary] = useState<ElaborazioneCaptchaSummary | null>(null);
  const [capacitasCredentials, setCapacitasCredentials] = useState<CapacitasCredential[]>([]);
  const [bonificaCredentials, setBonificaCredentials] = useState<BonificaOristaneseCredential[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [retryBusyId, setRetryBusyId] = useState<string | null>(null);
  const [modalState, setModalState] = useState<DashboardModalState | null>(null);

  const loadDashboard = useCallback(async (): Promise<void> => {
    const token = getStoredAccessToken();
    if (!token) return;

    try {
      const [credentialsResult, batchesResult, captchaSummaryResult, capacitasResult, bonificaResult] = await Promise.all([
        getElaborazioneCredentials(token),
        getElaborazioneBatches(token),
        getElaborazioneCaptchaSummary(token),
        listCapacitasCredentials(token),
        listBonificaOristaneseCredentials(token),
      ]);
      setCredentialStatus(credentialsResult);
      setBatches(batchesResult.slice(0, 6));
      setCaptchaSummary(captchaSummaryResult);
      setCapacitasCredentials(capacitasResult);
      setBonificaCredentials(bonificaResult);
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
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-6">
            {QUICK_ACTIONS.map((action) => {
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

      <div className="grid gap-6 xl:grid-cols-2">
        <article className="overflow-hidden rounded-[28px] border border-[#d9dfd6] bg-white shadow-panel">
          <ElaborazionePanelHeader
            badge={
              <>
                <LockIcon className="h-3.5 w-3.5" />
                Agenzia delle Entrate
              </>
            }
            title="Area SISTER"
            description="Raggruppa credenziali, visure, batch, archivio documenti e riepilogo CAPTCHA del flusso catastale."
          />
          <div className="space-y-5 p-6">
            <div className="rounded-xl border border-gray-100 bg-gray-50 p-4">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="label-caption">Credenziali SISTER</p>
                  <p className="mt-2 text-sm font-medium text-gray-900">
                    {credentialStatus?.configured ? "Configurate e pronte all'uso" : "Configurazione richiesta"}
                  </p>
                  <p className="mt-1 text-sm text-gray-500">
                    {credentialStatus?.default_credential
                      ? `${credentialStatus.default_credential.label} · ${credentialStatus.default_credential.sister_username}`
                      : "Apri le credenziali per configurare l'accesso Agenzia delle Entrate."}
                  </p>
                </div>
                <button
                  className="btn-secondary"
                  onClick={() =>
                    openWorkspaceModal(
                      "/elaborazioni/settings",
                      "Credenziali",
                      "Gestione accessi SISTER e account operativi senza lasciare la dashboard.",
                    )
                  }
                  type="button"
                >
                  Apri credenziali
                </button>
              </div>
            </div>

            <div className="grid gap-3 md:grid-cols-2">
              <button
                className="rounded-xl border border-gray-100 bg-gray-50 p-4 text-left transition hover:border-gray-200 hover:bg-white"
                onClick={() =>
                  openWorkspaceModal(
                    "/elaborazioni/new-single",
                    "Visura singola",
                    "Avvio diretto di una richiesta per immobile o soggetto in una modale operativa.",
                  )
                }
                type="button"
              >
                <SearchIcon className="h-5 w-5 text-[#1D4E35]" />
                <p className="mt-3 text-sm font-medium text-gray-900">Visura singola</p>
                <p className="mt-1 text-sm text-gray-500">Avvio diretto delle ricerche per immobile o soggetto.</p>
              </button>
              <button
                className="rounded-xl border border-gray-100 bg-gray-50 p-4 text-left transition hover:border-gray-200 hover:bg-white"
                onClick={() =>
                  openWorkspaceModal(
                    "/elaborazioni/new-batch",
                    "Import batch",
                    "Importazione lotto con preview e avvio worker senza cambiare pagina.",
                  )
                }
                type="button"
              >
                <FolderIcon className="h-5 w-5 text-[#1D4E35]" />
                <p className="mt-3 text-sm font-medium text-gray-900">Import batch</p>
                <p className="mt-1 text-sm text-gray-500">Caricamento lotti e preview dei record prima dell&apos;esecuzione.</p>
              </button>
              <button
                className="rounded-xl border border-gray-100 bg-gray-50 p-4 text-left transition hover:border-gray-200 hover:bg-white"
                onClick={() =>
                  openWorkspaceModal(
                    "/elaborazioni/batches",
                    "Archivio batch",
                    "Storico lotti, esiti, report e retry direttamente dentro la dashboard.",
                  )
                }
                type="button"
              >
                <DocumentIcon className="h-5 w-5 text-[#1D4E35]" />
                <p className="mt-3 text-sm font-medium text-gray-900">Archivio batch</p>
                <p className="mt-1 text-sm text-gray-500">Monitoraggio stato, retry, report e richieste CAPTCHA.</p>
              </button>
              <button
                className="rounded-xl border border-gray-100 bg-gray-50 p-4 text-left transition hover:border-gray-200 hover:bg-white"
                onClick={() =>
                  openWorkspaceModal(
                    "/catasto/archive?view=documents",
                    "Archivio documenti",
                    "Consultazione dei documenti estratti senza uscire dal cruscotto operativo.",
                  )
                }
                type="button"
              >
                <DocumentIcon className="h-5 w-5 text-[#1D4E35]" />
                <p className="mt-3 text-sm font-medium text-gray-900">Archivio documenti</p>
                <p className="mt-1 text-sm text-gray-500">Consultazione dei PDF estratti dal portale catastale.</p>
              </button>
            </div>

            <div>
              <div className="mb-3">
                <p className="label-caption">CAPTCHA manuali</p>
                <p className="mt-1 text-sm text-gray-500">Esito degli inserimenti manuali richiesti durante i flussi SISTER.</p>
              </div>
              {(captchaSummary?.processed ?? 0) === 0 ? (
                <EmptyState icon={SearchIcon} title="Nessun CAPTCHA elaborato" description="Non risultano ancora CAPTCHA elaborati o inserimenti registrati." />
              ) : (
                <div className="grid gap-3 md:grid-cols-3">
                  <div className="rounded-lg border border-gray-100 bg-gray-50 p-4">
                    <p className="label-caption">Elaborati</p>
                    <p className="mt-2 text-2xl font-semibold text-gray-900">{captchaSummary?.processed ?? 0}</p>
                  </div>
                  <div className="rounded-lg border border-emerald-100 bg-emerald-50 p-4">
                    <p className="label-caption text-emerald-700">Inseriti corretti</p>
                    <p className="mt-2 text-2xl font-semibold text-emerald-800">{captchaSummary?.correct ?? 0}</p>
                  </div>
                  <div className="rounded-lg border border-amber-100 bg-amber-50 p-4">
                    <p className="label-caption text-amber-700">Inseriti sbagliati</p>
                    <p className="mt-2 text-2xl font-semibold text-amber-800">{captchaSummary?.wrong ?? 0}</p>
                  </div>
                </div>
              )}
            </div>
          </div>
        </article>

        <article className="overflow-hidden rounded-[28px] border border-[#d9dfd6] bg-white shadow-panel">
          <ElaborazionePanelHeader
            badge={
              <>
                <UsersIcon className="h-3.5 w-3.5" />
                Capacitas
              </>
            }
            title="Pool operativo dedicato"
            description="Colonna separata per account, utilizzo e anomalie del servizio Capacitas. Altri servizi esterni potranno essere aggiunti con lo stesso schema."
          />
          <div className="space-y-5 p-6">
            <div className="rounded-xl border border-gray-100 bg-gray-50 p-4">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="label-caption">Pool Capacitas</p>
                  <p className="mt-2 text-sm font-medium text-gray-900">
                    {capacitasCredentials.length > 0
                      ? `${activeCapacitasCredentials.length} account attivi su ${capacitasCredentials.length}`
                      : "Nessun account Capacitas configurato"}
                  </p>
                  <p className="mt-1 text-sm text-gray-500">
                    {latestCapacitasUsage
                      ? `Ultimo utilizzo ${formatDateTime(latestCapacitasUsage)}`
                      : "Nessun utilizzo registrato al momento"}
                  </p>
                </div>
                <button
                  className="btn-secondary"
                  onClick={() =>
                    openWorkspaceModal(
                      "/elaborazioni/capacitas",
                      "Capacitas",
                      "Ricerca anagrafica e monitor operativo del pool account in una modale dedicata.",
                    )
                  }
                  type="button"
                >
                  Apri Capacitas
                </button>
              </div>
              {capacitasWarningCount > 0 ? (
                <p className="mt-3 text-sm text-amber-700">
                  {capacitasWarningCount} account Capacitas presentano errori recenti o richiedono verifica.
                </p>
              ) : null}
            </div>

            <div className="grid gap-3 md:grid-cols-2">
              <div className="rounded-xl border border-emerald-100 bg-emerald-50 p-4">
                <p className="label-caption text-emerald-700">Account attivi</p>
                <p className="mt-2 text-2xl font-semibold text-emerald-800">{activeCapacitasCredentials.length}</p>
                <p className="mt-1 text-sm text-emerald-700">Disponibili per ricerche e lavorazioni Capacitas.</p>
              </div>
              <div className="rounded-xl border border-amber-100 bg-amber-50 p-4">
                <p className="label-caption text-amber-700">Warning recenti</p>
                <p className="mt-2 text-2xl font-semibold text-amber-800">{capacitasWarningCount}</p>
                <p className="mt-1 text-sm text-amber-700">Account da verificare prima di nuove esecuzioni.</p>
              </div>
            </div>

            <div className="rounded-2xl border border-[#dfe7dd] bg-[#f8faf8] p-4">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="label-caption">Bonifica Oristanese</p>
                  <p className="mt-2 text-sm font-medium text-gray-900">
                    {bonificaCredentials.length > 0
                      ? `${activeBonificaCredentials.length} account attivi su ${bonificaCredentials.length}`
                      : "Nessun account Bonifica configurato"}
                  </p>
                  <p className="mt-1 text-sm text-gray-500">
                    {latestBonificaUsage
                      ? `Ultimo test o utilizzo ${formatDateTime(latestBonificaUsage)}`
                      : "Solo gestione credenziali e test login disponibili al momento"}
                  </p>
                </div>
                <button
                  className="btn-secondary"
                  onClick={() =>
                    openWorkspaceModal(
                      "/elaborazioni/settings",
                      "Credenziali",
                      "Gestione Bonifica Oristanese nello stesso workspace di SISTER e Capacitas.",
                    )
                  }
                  type="button"
                >
                  Apri credenziali
                </button>
              </div>
              {bonificaWarningCount > 0 ? (
                <p className="mt-3 text-sm text-amber-700">
                  {bonificaWarningCount} account Bonifica presentano errori recenti o richiedono verifica.
                </p>
              ) : null}
            </div>
          </div>
        </article>
      </div>

      <article className="overflow-hidden rounded-[28px] border border-[#d9dfd6] bg-white p-0 shadow-panel">
        <ElaborazionePanelHeader
          badge={
            <>
              <FolderIcon className="h-3.5 w-3.5" />
              Batch recenti
            </>
          }
          title="Ultimi lotti creati dall'utente corrente"
          description="I retry disponibili restano accessibili direttamente dalla tabella."
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
