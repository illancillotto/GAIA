"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { ProtectedPage } from "@/components/app/protected-page";
import { CatastoHero, CatastoMiniStat, CatastoNoticeCard, CatastoPanelHeader } from "@/components/catasto/module-chrome";
import { CatastoOperationMessage } from "@/components/catasto/operation-message";
import { MetricCard } from "@/components/ui/metric-card";
import { EmptyState } from "@/components/ui/empty-state";
import { DocumentIcon, FolderIcon, LockIcon, RefreshIcon, SearchIcon, UsersIcon } from "@/components/ui/icons";
import {
  getElaborazioneBatches,
  getElaborazioneCaptchaSummary,
  getElaborazioneCredentials,
  listCapacitasCredentials,
  retryFailedElaborazioneBatch,
  startElaborazioneBatch,
} from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import { formatDateTime } from "@/lib/presentation";
import type { CapacitasCredential, ElaborazioneBatch, ElaborazioneCaptchaSummary, ElaborazioneCredentialStatus } from "@/types/api";

const DASHBOARD_REFRESH_INTERVAL_MS = 5000;

export default function CatastoDashboardPage() {
  const [batches, setBatches] = useState<ElaborazioneBatch[]>([]);
  const [credentialStatus, setCredentialStatus] = useState<ElaborazioneCredentialStatus | null>(null);
  const [captchaSummary, setCaptchaSummary] = useState<ElaborazioneCaptchaSummary | null>(null);
  const [capacitasCredentials, setCapacitasCredentials] = useState<CapacitasCredential[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [retryBusyId, setRetryBusyId] = useState<string | null>(null);

  const loadCatastoDashboard = useCallback(async (): Promise<void> => {
    const token = getStoredAccessToken();
    if (!token) return;

    try {
      const [credentialsResult, batchesResult, captchaSummaryResult, capacitasResult] = await Promise.all([
        getElaborazioneCredentials(token),
        getElaborazioneBatches(token),
        getElaborazioneCaptchaSummary(token),
        listCapacitasCredentials(token),
      ]);
      setCredentialStatus(credentialsResult);
      setBatches(batchesResult.slice(0, 6));
      setCaptchaSummary(captchaSummaryResult);
      setCapacitasCredentials(capacitasResult);
      setError(null);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Errore caricamento dashboard Catasto");
    }
  }, []);

  useEffect(() => {
    void loadCatastoDashboard();
  }, [loadCatastoDashboard]);

  useEffect(() => {
    function handleVisibilityChange(): void {
      if (document.visibilityState === "visible") {
        void loadCatastoDashboard();
      }
    }

    const intervalId = window.setInterval(() => {
      if (document.visibilityState === "visible") {
        void loadCatastoDashboard();
      }
    }, DASHBOARD_REFRESH_INTERVAL_MS);

    document.addEventListener("visibilitychange", handleVisibilityChange);

    return () => {
      window.clearInterval(intervalId);
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, [loadCatastoDashboard]);

  async function handleRetryBatch(batch: ElaborazioneBatch): Promise<void> {
    const token = getStoredAccessToken();
    if (!token) return;

    setRetryBusyId(batch.id);
    try {
      if (batch.status === "failed" && batch.failed_items > 0) {
        await retryFailedElaborazioneBatch(token, batch.id);
      }
      await startElaborazioneBatch(token, batch.id);
      await loadCatastoDashboard();
      setError(null);
    } catch (retryError) {
      setError(retryError instanceof Error ? retryError.message : "Errore riavvio batch");
    } finally {
      setRetryBusyId(null);
    }
  }

  const completedToday = batches.filter((batch) => batch.status === "completed").length;
  const activeCapacitasCredentials = capacitasCredentials.filter((credential) => credential.active);
  const capacitasWarningCount = capacitasCredentials.filter((credential) => Boolean(credential.last_error)).length;
  const latestCapacitasUsage = capacitasCredentials
    .map((credential) => credential.last_used_at)
    .filter((value): value is string => Boolean(value))
    .sort()
    .at(-1);

  return (
    <ProtectedPage
      title="GAIA Catasto"
      description="Controllo batch visure, credenziali SISTER, operatività Capacitas e richieste CAPTCHA del modulo Agenzia delle Entrate."
      breadcrumb="Catasto"
    >
      <CatastoHero
        badge={
          <>
            <LockIcon className="h-3.5 w-3.5" />
            Workspace Catasto
          </>
        }
        title="Console operativa del modulo Catasto per visure, batch e pool Capacitas."
        description="La dashboard ora riassume stato credenziali, utilizzo del pool e attività recenti prima di entrare nei singoli flussi. Il refresh resta realtime quando la pagina è visibile."
        actions={
          error ? (
            <CatastoNoticeCard title="Errore dashboard" description={error} tone="danger" />
          ) : (
            <CatastoNoticeCard
              title="Refresh automatico attivo"
              description="Quando la pagina è in primo piano, i dati vengono ricaricati periodicamente per tenere allineati batch, pool e richieste CAPTCHA."
            />
          )
        }
      >
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <CatastoMiniStat
            eyebrow="SISTER"
            value={credentialStatus?.configured ? "Attivo" : "Da configurare"}
            description={credentialStatus?.credential?.sister_username ?? "Configura SISTER dalla pagina credenziali"}
            tone={credentialStatus?.configured ? "success" : "default"}
          />
          <CatastoMiniStat
            eyebrow="Capacitas"
            value={`${activeCapacitasCredentials.length}/${capacitasCredentials.length}`}
            description={
              capacitasCredentials.length > 0
                ? `${capacitasWarningCount} account con warning recenti`
                : "Nessun account Capacitas configurato"
            }
            tone={capacitasWarningCount > 0 ? "warning" : activeCapacitasCredentials.length > 0 ? "success" : "default"}
          />
          <CatastoMiniStat
            eyebrow="CAPTCHA"
            value={captchaSummary?.processed ?? 0}
            description="CAPTCHA manuali elaborati dal worker."
            tone={(captchaSummary?.processed ?? 0) > 0 ? "success" : "default"}
          />
          <CatastoMiniStat
            eyebrow="Ultimo utilizzo"
            value={latestCapacitasUsage ? formatDateTime(latestCapacitasUsage) : "Nessun uso"}
            description="Ultima attività registrata sul pool Capacitas."
          />
        </div>
      </CatastoHero>

      <div className="surface-grid">
        <MetricCard
          label="Credenziali"
          value={credentialStatus?.configured ? "SISTER attivo" : "Da configurare"}
          sub={credentialStatus?.credential?.sister_username ?? "Configura SISTER e Capacitas dalla pagina credenziali"}
          variant={credentialStatus?.configured ? "success" : "default"}
        />
        <MetricCard
          label="Capacitas"
          value={activeCapacitasCredentials.length}
          sub={
            capacitasCredentials.length > 0
              ? `${capacitasWarningCount} account con warning su ${capacitasCredentials.length}`
              : "Nessun account Capacitas configurato"
          }
          variant={capacitasWarningCount > 0 ? "warning" : activeCapacitasCredentials.length > 0 ? "success" : "default"}
        />
        <MetricCard
          label="CAPTCHA elaborati"
          value={captchaSummary?.processed ?? 0}
          sub={`${captchaSummary?.correct ?? 0} corretti · ${captchaSummary?.wrong ?? 0} sbagliati`}
          variant={(captchaSummary?.wrong ?? 0) > 0 ? "warning" : (captchaSummary?.processed ?? 0) > 0 ? "success" : "default"}
        />
        <MetricCard
          label="Batch completati"
          value={completedToday}
          sub="Storico batch completati disponibili nel modulo"
        />
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.4fr,1fr]">
        <article className="overflow-hidden rounded-[28px] border border-[#d9dfd6] bg-white shadow-panel">
          <CatastoPanelHeader
            badge={
              <>
                <RefreshIcon className="h-3.5 w-3.5" />
                Azioni rapide
              </>
            }
            title="Accesso diretto ai flussi principali"
            description="Le aree più usate del modulo sono raccolte qui con descrizioni più orientate all'operatività."
          />
          <div className="p-6">
          <div className="grid gap-3 md:grid-cols-2">
            <Link className="rounded-xl border border-gray-100 bg-gray-50 p-4 transition hover:border-gray-200 hover:bg-white" href="/elaborazioni/settings">
              <LockIcon className="h-5 w-5 text-[#1D4E35]" />
              <p className="mt-3 text-sm font-medium text-gray-900">Credenziali</p>
              <p className="mt-1 text-sm text-gray-500">SISTER e Capacitas nello stesso hub operativo.</p>
            </Link>
            <Link className="rounded-xl border border-gray-100 bg-gray-50 p-4 transition hover:border-gray-200 hover:bg-white" href="/elaborazioni/new-batch">
              <FolderIcon className="h-5 w-5 text-[#1D4E35]" />
              <p className="mt-3 text-sm font-medium text-gray-900">Import batch</p>
              <p className="mt-1 text-sm text-gray-500">Upload CSV o XLSX, preview e avvio worker.</p>
            </Link>
            <Link className="rounded-xl border border-gray-100 bg-gray-50 p-4 transition hover:border-gray-200 hover:bg-white" href="/elaborazioni/new-single">
              <SearchIcon className="h-5 w-5 text-[#1D4E35]" />
              <p className="mt-3 text-sm font-medium text-gray-900">Visura singola</p>
              <p className="mt-1 text-sm text-gray-500">Richiesta puntuale con selezione comune e avvio immediato.</p>
            </Link>
            <Link className="rounded-xl border border-gray-100 bg-gray-50 p-4 transition hover:border-gray-200 hover:bg-white" href="/catasto/capacitas">
              <UsersIcon className="h-5 w-5 text-[#1D4E35]" />
              <p className="mt-3 text-sm font-medium text-gray-900">Capacitas inVOLTURE</p>
              <p className="mt-1 text-sm text-gray-500">Ricerca anagrafica tramite pool account dedicato.</p>
            </Link>
            <Link className="rounded-xl border border-gray-100 bg-gray-50 p-4 transition hover:border-gray-200 hover:bg-white" href="/elaborazioni/batches">
              <DocumentIcon className="h-5 w-5 text-[#1D4E35]" />
              <p className="mt-3 text-sm font-medium text-gray-900">Archivio batch</p>
              <p className="mt-1 text-sm text-gray-500">Consulta progress, esiti e CAPTCHA aperti.</p>
            </Link>
            <Link className="rounded-xl border border-gray-100 bg-gray-50 p-4 transition hover:border-gray-200 hover:bg-white" href="/catasto/archive?view=documents">
              <DocumentIcon className="h-5 w-5 text-[#1D4E35]" />
              <p className="mt-3 text-sm font-medium text-gray-900">Archivio documenti</p>
              <p className="mt-1 text-sm text-gray-500">Ricerca per comune, foglio, particella e apertura PDF inline.</p>
            </Link>
          </div>
          </div>
        </article>

        <article className="overflow-hidden rounded-[28px] border border-[#d9dfd6] bg-white shadow-panel">
          <CatastoPanelHeader
            badge={
              <>
                <UsersIcon className="h-3.5 w-3.5" />
                Monitor operativo
              </>
            }
            title="Pool Capacitas e riepilogo CAPTCHA"
            description="Una vista laterale dedicata agli account attivi e ai risultati dei CAPTCHA manuali."
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
                <Link className="btn-secondary" href="/catasto/capacitas">
                  Apri Capacitas
                </Link>
              </div>
              {capacitasWarningCount > 0 ? (
                <p className="mt-3 text-sm text-amber-700">
                  {capacitasWarningCount} account Capacitas presentano errori recenti o richiedono verifica.
                </p>
              ) : null}
            </div>

            <div>
              <div className="mb-3">
                <p className="label-caption">CAPTCHA manuali</p>
                <p className="mt-1 text-sm text-gray-500">Dati dei CAPTCHA elaborati, inseriti corretti e inseriti sbagliati.</p>
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
      </div>

      <article className="overflow-hidden rounded-[28px] border border-[#d9dfd6] bg-white p-0 shadow-panel">
        <CatastoPanelHeader
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
                      <Link className="font-medium text-[#1D4E35]" href={`/elaborazioni/batches/${batch.id}`}>
                        {batch.name ?? batch.id}
                      </Link>
                    </td>
                    <td>{batch.status}</td>
                    <td>{batch.total_items}</td>
                    <td><CatastoOperationMessage value={batch.current_operation} /></td>
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
    </ProtectedPage>
  );
}
