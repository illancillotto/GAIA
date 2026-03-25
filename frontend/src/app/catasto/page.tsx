"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { ProtectedPage } from "@/components/app/protected-page";
import { MetricCard } from "@/components/ui/metric-card";
import { EmptyState } from "@/components/ui/empty-state";
import { DocumentIcon, FolderIcon, LockIcon, SearchIcon } from "@/components/ui/icons";
import { getCatastoBatches, getCatastoCredentials, getPendingCatastoCaptcha } from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import { formatDateTime } from "@/lib/presentation";
import type { CatastoBatch, CatastoCredentialStatus, CatastoVisuraRequest } from "@/types/api";

export default function CatastoDashboardPage() {
  const [batches, setBatches] = useState<CatastoBatch[]>([]);
  const [credentialStatus, setCredentialStatus] = useState<CatastoCredentialStatus | null>(null);
  const [pendingCaptcha, setPendingCaptcha] = useState<CatastoVisuraRequest[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadCatastoDashboard() {
      const token = getStoredAccessToken();
      if (!token) return;

      try {
        const [credentialsResult, batchesResult, captchaResult] = await Promise.all([
          getCatastoCredentials(token),
          getCatastoBatches(token),
          getPendingCatastoCaptcha(token),
        ]);
        setCredentialStatus(credentialsResult);
        setBatches(batchesResult.slice(0, 6));
        setPendingCaptcha(captchaResult);
        setError(null);
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : "Errore caricamento dashboard Catasto");
      }
    }

    void loadCatastoDashboard();
  }, []);

  const activeBatch = batches.find((batch) => batch.status === "processing");
  const completedToday = batches.filter((batch) => batch.status === "completed").length;

  return (
    <ProtectedPage
      title="GAIA Catasto"
      description="Controllo batch visure, credenziali SISTER e richieste CAPTCHA del modulo Agenzia delle Entrate."
      breadcrumb="Catasto"
    >
      {error ? <p className="text-sm text-red-600">{error}</p> : null}

      <div className="surface-grid">
        <MetricCard
          label="Credenziali SISTER"
          value={credentialStatus?.configured ? "Configurate" : "Assenti"}
          sub={credentialStatus?.credential?.sister_username ?? "Salva le credenziali per avviare le visure"}
          variant={credentialStatus?.configured ? "success" : "default"}
        />
        <MetricCard
          label="Batch recenti"
          value={batches.length}
          sub={activeBatch ? `Attivo: ${activeBatch.name ?? activeBatch.id}` : "Nessun batch in esecuzione"}
        />
        <MetricCard
          label="CAPTCHA pendenti"
          value={pendingCaptcha.length}
          sub={pendingCaptcha.length > 0 ? "Richieste in attesa di input manuale" : "Nessun intervento richiesto"}
          variant={pendingCaptcha.length > 0 ? "warning" : "success"}
        />
        <MetricCard
          label="Batch completati"
          value={completedToday}
          sub="Storico batch completati disponibili nel modulo"
        />
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.4fr,1fr]">
        <article className="panel-card">
          <div className="mb-4 flex items-center justify-between gap-3">
            <div>
              <p className="section-title">Azioni rapide</p>
              <p className="section-copy">Apri direttamente i flussi operativi del modulo Catasto.</p>
            </div>
          </div>
          <div className="grid gap-3 md:grid-cols-2">
            <Link className="rounded-xl border border-gray-100 bg-gray-50 p-4 transition hover:border-gray-200 hover:bg-white" href="/catasto/settings">
              <LockIcon className="h-5 w-5 text-[#1D4E35]" />
              <p className="mt-3 text-sm font-medium text-gray-900">Credenziali SISTER</p>
              <p className="mt-1 text-sm text-gray-500">Vault cifrato con master key in ambiente.</p>
            </Link>
            <Link className="rounded-xl border border-gray-100 bg-gray-50 p-4 transition hover:border-gray-200 hover:bg-white" href="/catasto/new-batch">
              <FolderIcon className="h-5 w-5 text-[#1D4E35]" />
              <p className="mt-3 text-sm font-medium text-gray-900">Nuovo batch</p>
              <p className="mt-1 text-sm text-gray-500">Upload CSV o XLSX, preview e avvio worker.</p>
            </Link>
            <Link className="rounded-xl border border-gray-100 bg-gray-50 p-4 transition hover:border-gray-200 hover:bg-white" href="/catasto/new-single">
              <SearchIcon className="h-5 w-5 text-[#1D4E35]" />
              <p className="mt-3 text-sm font-medium text-gray-900">Visura singola</p>
              <p className="mt-1 text-sm text-gray-500">Richiesta puntuale con selezione comune e avvio immediato.</p>
            </Link>
            <Link className="rounded-xl border border-gray-100 bg-gray-50 p-4 transition hover:border-gray-200 hover:bg-white" href="/catasto/batches">
              <DocumentIcon className="h-5 w-5 text-[#1D4E35]" />
              <p className="mt-3 text-sm font-medium text-gray-900">Storico batch</p>
              <p className="mt-1 text-sm text-gray-500">Consulta progress, esiti e CAPTCHA aperti.</p>
            </Link>
            <Link className="rounded-xl border border-gray-100 bg-gray-50 p-4 transition hover:border-gray-200 hover:bg-white" href="/catasto/documents">
              <DocumentIcon className="h-5 w-5 text-[#1D4E35]" />
              <p className="mt-3 text-sm font-medium text-gray-900">Archivio documenti</p>
              <p className="mt-1 text-sm text-gray-500">Ricerca per comune, foglio, particella e apertura PDF inline.</p>
            </Link>
          </div>
        </article>

        <article className="panel-card">
          <div className="mb-4">
            <p className="section-title">CAPTCHA in attesa</p>
            <p className="section-copy">Le richieste bloccate richiedono input manuale entro la scadenza.</p>
          </div>
          {pendingCaptcha.length === 0 ? (
            <EmptyState icon={SearchIcon} title="Nessun CAPTCHA aperto" description="Il worker non ha richiesto interventi manuali." />
          ) : (
            <div className="space-y-3">
              {pendingCaptcha.slice(0, 5).map((request) => (
                <Link
                  key={request.id}
                  href={`/catasto/batches/${request.batch_id}`}
                  className="block rounded-lg border border-amber-100 bg-amber-50 px-4 py-3 transition hover:bg-amber-100"
                >
                  <p className="text-sm font-medium text-amber-900">
                    {request.comune} · Fg.{request.foglio} Part.{request.particella}
                  </p>
                  <p className="mt-1 text-xs text-amber-700">
                    Richiesto {formatDateTime(request.captcha_requested_at)} · batch {request.batch_id.slice(0, 8)}
                  </p>
                </Link>
              ))}
            </div>
          )}
        </article>
      </div>

      <article className="panel-card overflow-hidden p-0">
        <div className="border-b border-gray-100 px-5 py-4">
          <p className="section-title">Batch recenti</p>
          <p className="section-copy">Ultimi lotti visure creati dall’utente corrente.</p>
        </div>
        {batches.length === 0 ? (
          <div className="p-5">
            <EmptyState icon={SearchIcon} title="Nessun batch presente" description="Carica un CSV da /catasto/new-batch per iniziare." />
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
                </tr>
              </thead>
              <tbody>
                {batches.map((batch) => (
                  <tr key={batch.id}>
                    <td>
                      <Link className="font-medium text-[#1D4E35]" href={`/catasto/batches/${batch.id}`}>
                        {batch.name ?? batch.id}
                      </Link>
                    </td>
                    <td>{batch.status}</td>
                    <td>{batch.total_items}</td>
                    <td>{batch.current_operation ?? "—"}</td>
                    <td>{formatDateTime(batch.created_at)}</td>
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
