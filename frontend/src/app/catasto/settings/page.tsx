"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { ProtectedPage } from "@/components/app/protected-page";
import {
  createCatastoCredentialTestWebSocket,
  deleteCatastoCredentials,
  getCatastoCredentialTest,
  getCatastoCredentials,
  saveCatastoCredentials,
  testCatastoCredentials,
} from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import { formatDateTime } from "@/lib/presentation";
import type {
  CatastoCredentialStatus,
  CatastoCredentialTestResult,
  CatastoCredentialTestWebSocketEvent,
} from "@/types/api";

const DEFAULT_UFFICIO = "ORISTANO Territorio";

function normalizeIssueText(value: string | null | undefined): string {
  return (value ?? "")
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");
}

export default function CatastoSettingsPage() {
  const [credentialStatus, setCredentialStatus] = useState<CatastoCredentialStatus | null>(null);
  const [formState, setFormState] = useState({
    sister_username: "",
    sister_password: "",
    convenzione: "",
    codice_richiesta: "",
    ufficio_provinciale: DEFAULT_UFFICIO,
  });
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [testBusy, setTestBusy] = useState(false);
  const [testResult, setTestResult] = useState<CatastoCredentialTestResult | null>(null);
  const testSocketRef = useRef<WebSocket | null>(null);
  const activeTestId = testResult?.id ?? null;
  const activeTestStatus = testResult?.status ?? null;

  useEffect(() => {
    void loadCredentials();
  }, []);

  async function loadCredentials(): Promise<void> {
    const token = getStoredAccessToken();
    if (!token) return;

    try {
      const result = await getCatastoCredentials(token);
      setCredentialStatus(result);
      setFormState((current) => ({
        ...current,
        sister_username: result.credential?.sister_username ?? current.sister_username,
        convenzione: result.credential?.convenzione ?? "",
        codice_richiesta: result.credential?.codice_richiesta ?? "",
        ufficio_provinciale: result.credential?.ufficio_provinciale ?? DEFAULT_UFFICIO,
      }));
      setError(null);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Errore caricamento credenziali");
    }
  }

  async function handleSave(): Promise<void> {
    const token = getStoredAccessToken();
    if (!token) return;

    setBusy(true);
    try {
      await saveCatastoCredentials(token, formState);
      await loadCredentials();
      setFormState((current) => ({ ...current, sister_password: "" }));
      setStatusMessage("Credenziali SISTER salvate nel vault cifrato.");
      setError(null);
      setTestResult(null);
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Errore salvataggio credenziali");
      setStatusMessage(null);
    } finally {
      setBusy(false);
    }
  }

  async function handleDelete(): Promise<void> {
    const token = getStoredAccessToken();
    if (!token) return;

    setBusy(true);
    try {
      await deleteCatastoCredentials(token);
      await loadCredentials();
      setFormState({
        sister_username: "",
        sister_password: "",
        convenzione: "",
        codice_richiesta: "",
        ufficio_provinciale: DEFAULT_UFFICIO,
      });
      setStatusMessage("Credenziali SISTER rimosse.");
      setError(null);
      setTestResult(null);
    } catch (deleteError) {
      setError(deleteError instanceof Error ? deleteError.message : "Errore eliminazione credenziali");
      setStatusMessage(null);
    } finally {
      setBusy(false);
    }
  }

  async function handleTestConnection(): Promise<void> {
    const token = getStoredAccessToken();
    if (!token) return;

    const hasTransientCredentials = Boolean(formState.sister_username.trim() && formState.sister_password.trim());
    setTestBusy(true);
    try {
      const result = await testCatastoCredentials(
        token,
        hasTransientCredentials
          ? {
              sister_username: formState.sister_username,
              sister_password: formState.sister_password,
              convenzione: formState.convenzione || undefined,
              codice_richiesta: formState.codice_richiesta || undefined,
              ufficio_provinciale: formState.ufficio_provinciale,
            }
          : undefined,
      );
      setTestResult(result);
      setTestBusy(["pending", "processing"].includes(result.status));
      setStatusMessage(null);
      setError(null);
    } catch (testError) {
      setError(testError instanceof Error ? testError.message : "Errore test connessione SISTER");
      setStatusMessage(null);
      setTestResult(null);
      setTestBusy(false);
    } finally {
      if (!hasTransientCredentials) {
        void loadCredentials();
      }
    }
  }

  const refreshConnectionTest = useCallback(async (token: string, testId: string): Promise<void> => {
    try {
      const result = await getCatastoCredentialTest(token, testId);
      setTestResult(result);
      setTestBusy(["pending", "processing"].includes(result.status));
      setError(null);
      if (result.verified_at) {
        setCredentialStatus((current) =>
          current && current.credential
            ? {
                ...current,
                credential: {
                  ...current.credential,
                  verified_at: result.verified_at,
                },
              }
            : current,
        );
      }
      if (!["pending", "processing"].includes(result.status)) {
        void loadCredentials();
      }
    } catch (refreshError) {
      setError(refreshError instanceof Error ? refreshError.message : "Errore refresh test connessione SISTER");
      setTestBusy(false);
    }
  }, []);

  useEffect(() => {
    const token = getStoredAccessToken();
    if (!token || !activeTestId || !activeTestStatus || !["pending", "processing"].includes(activeTestStatus)) {
      if (testSocketRef.current) {
        testSocketRef.current.close();
        testSocketRef.current = null;
      }
      return;
    }

    const socket = createCatastoCredentialTestWebSocket(activeTestId, token);
    if (!socket) return;
    testSocketRef.current = socket;

    socket.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data) as CatastoCredentialTestWebSocketEvent;
        if (payload.type !== "credentials_test") {
          return;
        }

        const nextResult = payload.test;
        setTestResult(nextResult);
        setTestBusy(["pending", "processing"].includes(nextResult.status));
        setError(null);
        if (nextResult.verified_at) {
          setCredentialStatus((current) =>
            current && current.credential
              ? {
                  ...current,
                  credential: {
                    ...current.credential,
                    verified_at: nextResult.verified_at,
                  },
                }
              : current,
          );
        }
        if (!["pending", "processing"].includes(nextResult.status)) {
          void loadCredentials();
        }
      } catch (socketError) {
        setError(socketError instanceof Error ? socketError.message : "Errore parsing aggiornamento realtime");
      }
    };

    socket.onerror = () => {
      void refreshConnectionTest(token, activeTestId);
    };

    return () => {
      socket.close();
      if (testSocketRef.current === socket) {
        testSocketRef.current = null;
      }
    };
  }, [activeTestId, activeTestStatus, refreshConnectionTest]);

  const canTestConnection = Boolean(
    (!busy && credentialStatus?.configured) || (formState.sister_username.trim() && formState.sister_password.trim()),
  );
  const normalizedTestMessage = normalizeIssueText(testResult?.message);
  const hasExistingSessionIssue =
    normalizedTestMessage.includes("gia' in sessione") ||
    normalizedTestMessage.includes("gia in sessione") ||
    normalizedTestMessage.includes("altra postazione") ||
    normalizedTestMessage.includes("un'altra postazione") ||
    normalizedTestMessage.includes("altro browser");
  const testResultToneClassName =
    testResult == null
      ? null
      : ["pending", "processing"].includes(testResult.status)
        ? "border-sky-200 bg-sky-50 text-sky-800"
      : hasExistingSessionIssue
        ? "border-amber-200 bg-amber-50 text-amber-900"
      : testResult.authenticated
        ? "border-emerald-200 bg-emerald-50 text-emerald-800"
        : testResult.success
          ? "border-amber-200 bg-amber-50 text-amber-800"
          : "border-red-200 bg-red-50 text-red-800";

  return (
    <ProtectedPage
      title="Impostazioni Catasto"
      description="Gestione del vault credenziali SISTER condiviso tra backend e worker Playwright."
      breadcrumb="Catasto / Impostazioni"
    >
      {error ? <p className="text-sm text-red-600">{error}</p> : null}
      {statusMessage ? <p className="text-sm text-emerald-700">{statusMessage}</p> : null}

      <article className="panel-card">
        <div className="grid gap-4 md:grid-cols-2">
          <label className="space-y-2">
            <span className="label-caption">Username SISTER</span>
            <input
              className="form-control"
              onChange={(event) => setFormState((current) => ({ ...current, sister_username: event.target.value }))}
              placeholder="Codice fiscale / username"
              value={formState.sister_username}
            />
          </label>
          <label className="space-y-2">
            <span className="label-caption">Password SISTER</span>
            <input
              className="form-control"
              onChange={(event) => setFormState((current) => ({ ...current, sister_password: event.target.value }))}
              placeholder="Password SISTER"
              type="password"
              value={formState.sister_password}
            />
          </label>
          <label className="space-y-2">
            <span className="label-caption">Convenzione</span>
            <input
              className="form-control"
              onChange={(event) => setFormState((current) => ({ ...current, convenzione: event.target.value }))}
              placeholder="CONSORZIO DI BONIFICA DELL'ORISTANESE"
              value={formState.convenzione}
            />
          </label>
          <label className="space-y-2">
            <span className="label-caption">Codice richiesta</span>
            <input
              className="form-control"
              onChange={(event) => setFormState((current) => ({ ...current, codice_richiesta: event.target.value }))}
              placeholder="C00024602008"
              value={formState.codice_richiesta}
            />
          </label>
          <label className="space-y-2 md:col-span-2">
            <span className="label-caption">Ufficio provinciale</span>
            <input
              className="form-control"
              onChange={(event) => setFormState((current) => ({ ...current, ufficio_provinciale: event.target.value }))}
              value={formState.ufficio_provinciale}
            />
          </label>
        </div>

        <div className="mt-5 flex flex-wrap items-center gap-3">
          <button
            className="btn-primary"
            disabled={busy || !formState.sister_username || !formState.sister_password}
            onClick={() => void handleSave()}
            type="button"
          >
            {busy ? "Salvataggio..." : credentialStatus?.configured ? "Aggiorna credenziali" : "Salva credenziali"}
          </button>
          <button
            className="btn-secondary"
            disabled={busy || !credentialStatus?.configured}
            onClick={() => void handleDelete()}
            type="button"
          >
            Elimina
          </button>
          <button
            className="btn-secondary"
            disabled={busy || testBusy || !canTestConnection}
            onClick={() => void handleTestConnection()}
            type="button"
          >
            {testBusy ? "Test in corso..." : "Testa connessione"}
          </button>
          <span className="text-xs text-gray-400">
            Se la password e&apos; valorizzata viene testato il form corrente; altrimenti vengono usate le credenziali gia&apos; salvate.
          </span>
        </div>

        {testResult && testResultToneClassName ? (
          <div className={`mt-5 rounded-xl border px-4 py-3 ${testResultToneClassName}`}>
            <p className="text-sm font-medium">
              {["pending", "processing"].includes(testResult.status)
                ? "Test in lavorazione"
                : hasExistingSessionIssue
                ? "Sessione SISTER gia' attiva"
                : testResult.authenticated
                ? "Autenticazione confermata"
                : testResult.success
                  ? "Portale raggiungibile"
                  : "Test connessione fallito"}
            </p>
            <p className="mt-1 text-sm">{testResult.message ?? "Richiesta inoltrata al worker Catasto."}</p>
            <p className="mt-2 text-xs uppercase tracking-[0.18em]">
              Stato: {testResult.status} · Modalita&apos;: {testResult.mode ?? "worker"} · Reachable: {testResult.reachable == null ? "n/d" : testResult.reachable ? "si" : "no"} · Auth: {testResult.authenticated == null ? "n/d" : testResult.authenticated ? "si" : "no"}
            </p>
            {hasExistingSessionIssue ? (
              <div className="mt-3 rounded-lg border border-amber-200/80 bg-white/65 px-3 py-3 text-sm leading-6 text-amber-950">
                <p className="font-medium">SISTER segnala che l&apos;utenza risulta gia&apos; aperta altrove.</p>
                <p className="mt-1">
                  Chiudi eventuali sessioni SISTER lasciate aperte in altri browser o postazioni, usa il pulsante
                  <span className="font-medium"> Esci</span> se disponibile, attendi qualche minuto e poi ripeti il test.
                </p>
              </div>
            ) : null}
          </div>
        ) : null}
      </article>

      <article className="panel-card">
        <p className="section-title">Stato vault</p>
        <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <div className="rounded-lg border border-gray-100 bg-gray-50 p-4">
            <p className="label-caption">Configurazione</p>
            <p className="mt-2 text-sm font-medium text-gray-900">
              {credentialStatus?.configured ? "Credenziali presenti" : "Nessuna credenziale salvata"}
            </p>
          </div>
          <div className="rounded-lg border border-gray-100 bg-gray-50 p-4">
            <p className="label-caption">Username</p>
            <p className="mt-2 text-sm font-medium text-gray-900">{credentialStatus?.credential?.sister_username ?? "—"}</p>
          </div>
          <div className="rounded-lg border border-gray-100 bg-gray-50 p-4">
            <p className="label-caption">Ultima verifica</p>
            <p className="mt-2 text-sm font-medium text-gray-900">{formatDateTime(credentialStatus?.credential?.verified_at ?? null)}</p>
          </div>
          <div className="rounded-lg border border-gray-100 bg-gray-50 p-4">
            <p className="label-caption">Ultimo update</p>
            <p className="mt-2 text-sm font-medium text-gray-900">{formatDateTime(credentialStatus?.credential?.updated_at ?? null)}</p>
          </div>
        </div>
      </article>
    </ProtectedPage>
  );
}
