"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { ProtectedPage } from "@/components/app/protected-page";
import {
  AlertTriangleIcon,
  CheckIcon,
  LockIcon,
  RefreshIcon,
  SearchIcon,
  ServerIcon,
  UsersIcon,
} from "@/components/ui/icons";
import {
  ApiError,
  createCapacitasCredential,
  createElaborazioneCredentialTestWebSocket,
  deleteCapacitasCredential,
  deleteElaborazioneCredentials,
  getElaborazioneCredentialTest,
  getElaborazioneCredentials,
  listCapacitasCredentials,
  saveElaborazioneCredentials,
  testCapacitasCredential,
  testElaborazioneCredentials,
  updateCapacitasCredential,
} from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import { formatDateTime } from "@/lib/presentation";
import type {
  CapacitasCredential,
  ElaborazioneCredentialStatus,
  ElaborazioneCredentialTestResult,
  ElaborazioneCredentialTestWebSocketEvent,
} from "@/types/api";

const DEFAULT_UFFICIO = "ORISTANO Territorio";

const DEFAULT_CAPACITAS_FORM = {
  id: null as number | null,
  label: "",
  username: "",
  password: "",
  active: true,
  allowed_hours_start: 0,
  allowed_hours_end: 23,
};

function normalizeIssueText(value: string | null | undefined): string {
  return (value ?? "")
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");
}

function summarizeCapacitasStatus(credential: CapacitasCredential): string {
  if (!credential.active) {
    return "Disattiva";
  }
  if (credential.last_error) {
    return "Attiva con warning";
  }
  if (credential.last_used_at) {
    return "Operativa";
  }
  return "Pronta";
}

function formatHour(value: number): string {
  return `${String(value).padStart(2, "0")}:00`;
}

function StatCard({
  eyebrow,
  value,
  description,
  tone = "default",
}: {
  eyebrow: string;
  value: string | number;
  description: string;
  tone?: "default" | "success" | "warning";
}) {
  const toneClasses =
    tone === "success"
      ? "border-emerald-200/70 bg-emerald-50/80"
      : tone === "warning"
        ? "border-amber-200/80 bg-amber-50/80"
        : "border-white/70 bg-white/75";

  return (
    <div className={`rounded-2xl border p-4 backdrop-blur ${toneClasses}`}>
      <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-gray-500">{eyebrow}</p>
      <p className="mt-3 text-2xl font-semibold text-gray-900">{value}</p>
      <p className="mt-2 text-sm leading-6 text-gray-600">{description}</p>
    </div>
  );
}

function StatusBanner({
  tone,
  title,
  description,
}: {
  tone: "danger" | "success" | "warning" | "info";
  title: string;
  description: string;
}) {
  const toneClasses =
    tone === "danger"
      ? "border-red-200 bg-red-50 text-red-800"
      : tone === "success"
        ? "border-emerald-200 bg-emerald-50 text-emerald-800"
        : tone === "warning"
          ? "border-amber-200 bg-amber-50 text-amber-900"
          : "border-sky-200 bg-sky-50 text-sky-800";

  return (
    <div className={`rounded-2xl border px-4 py-3 ${toneClasses}`}>
      <p className="text-sm font-semibold">{title}</p>
      <p className="mt-1 text-sm leading-6">{description}</p>
    </div>
  );
}

function DetailCard({ label, value }: { label: string; value: string | null | undefined }) {
  return (
    <div className="rounded-2xl border border-gray-200/80 bg-white/80 p-4">
      <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-gray-400">{label}</p>
      <p className="mt-3 text-sm font-medium text-gray-900">{value && value.trim().length > 0 ? value : "—"}</p>
    </div>
  );
}

type CapacitasTestDialogState = {
  open: boolean;
  phase: "idle" | "running" | "success" | "error";
  credential: CapacitasCredential | null;
  startedAt: string | null;
  finishedAt: string | null;
  statusCode: number | null;
  title: string;
  summary: string;
  backendDetail: string | null;
  tokenPreview: string | null;
  diagnosis: string | null;
};

function CapacitasTestDialog({
  state,
  onClose,
}: {
  state: CapacitasTestDialogState;
  onClose: () => void;
}) {
  if (!state.open) {
    return null;
  }

  const toneClasses =
    state.phase === "success"
      ? "border-emerald-200 bg-emerald-50 text-emerald-800"
      : state.phase === "error"
        ? "border-red-200 bg-red-50 text-red-800"
        : "border-sky-200 bg-sky-50 text-sky-800";

  return (
    <div className="fixed inset-0 z-[80] flex items-center justify-center bg-black/45 px-4 py-6 backdrop-blur-sm">
      <div className="w-full max-w-3xl rounded-[28px] border border-gray-200 bg-white p-6 shadow-2xl">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="section-title">Test credenziale Capacitas</p>
            <p className="section-copy">
              Verifica di login SSO verso `sso.servizicapacitas.com` con diagnostica completa lato utente.
            </p>
          </div>
          <button className="btn-secondary" onClick={onClose} type="button">
            Chiudi
          </button>
        </div>

        <div className={`mt-5 rounded-2xl border px-4 py-4 ${toneClasses}`}>
          <p className="text-sm font-semibold">{state.title}</p>
          <p className="mt-1 text-sm leading-6">{state.summary}</p>
        </div>

        <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <DetailCard label="Credenziale" value={state.credential?.label ?? "—"} />
          <DetailCard label="Username" value={state.credential?.username ?? "—"} />
          <DetailCard
            label="Fascia oraria"
            value={
              state.credential
                ? `${formatHour(state.credential.allowed_hours_start)} - ${formatHour(state.credential.allowed_hours_end)}`
                : "—"
            }
          />
          <DetailCard label="HTTP status" value={state.statusCode != null ? String(state.statusCode) : "—"} />
          <DetailCard label="Avviato" value={formatDateTime(state.startedAt)} />
          <DetailCard label="Concluso" value={formatDateTime(state.finishedAt)} />
          <DetailCard label="Ultimo uso noto" value={formatDateTime(state.credential?.last_used_at ?? null)} />
          <DetailCard label="Token preview" value={state.tokenPreview ?? "—"} />
        </div>

        <div className="mt-5 grid gap-4 lg:grid-cols-2">
          <div className="rounded-2xl border border-gray-200/80 bg-gray-50 p-4">
            <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-gray-400">Dettaglio backend</p>
            <p className="mt-3 whitespace-pre-wrap text-sm leading-6 text-gray-700">
              {state.backendDetail ?? "Nessun dettaglio aggiuntivo restituito dal backend."}
            </p>
          </div>
          <div className="rounded-2xl border border-gray-200/80 bg-gray-50 p-4">
            <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-gray-400">Diagnosi operativa</p>
            <p className="mt-3 whitespace-pre-wrap text-sm leading-6 text-gray-700">
              {state.diagnosis ?? "Nessuna diagnosi aggiuntiva disponibile."}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

export function ElaborazioniSettingsWorkspace({ embedded = false }: { embedded?: boolean }) {
  const [credentialStatus, setCredentialStatus] = useState<ElaborazioneCredentialStatus | null>(null);
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
  const [testResult, setTestResult] = useState<ElaborazioneCredentialTestResult | null>(null);
  const testSocketRef = useRef<WebSocket | null>(null);
  const activeTestId = testResult?.id ?? null;
  const activeTestStatus = testResult?.status ?? null;

  const [capacitasCredentials, setCapacitasCredentials] = useState<CapacitasCredential[]>([]);
  const [capacitasForm, setCapacitasForm] = useState(DEFAULT_CAPACITAS_FORM);
  const [capacitasBusy, setCapacitasBusy] = useState(false);
  const [capacitasLoading, setCapacitasLoading] = useState(false);
  const [capacitasTestingId, setCapacitasTestingId] = useState<number | null>(null);
  const [capacitasStatusMessage, setCapacitasStatusMessage] = useState<string | null>(null);
  const [capacitasError, setCapacitasError] = useState<string | null>(null);
  const [capacitasTestDialog, setCapacitasTestDialog] = useState<CapacitasTestDialogState>({
    open: false,
    phase: "idle",
    credential: null,
    startedAt: null,
    finishedAt: null,
    statusCode: null,
    title: "Test Capacitas",
    summary: "Nessun test avviato.",
    backendDetail: null,
    tokenPreview: null,
    diagnosis: null,
  });

  useEffect(() => {
    void Promise.all([loadCredentials(), loadCapacitasCredentials()]);
  }, []);

  async function loadCredentials(): Promise<void> {
    const token = getStoredAccessToken();
    if (!token) return;

    try {
      const result = await getElaborazioneCredentials(token);
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

  async function loadCapacitasCredentials(): Promise<void> {
    const token = getStoredAccessToken();
    if (!token) return;

    setCapacitasLoading(true);
    try {
      const result = await listCapacitasCredentials(token);
      setCapacitasCredentials(result);
      setCapacitasError(null);
    } catch (loadError) {
      setCapacitasError(loadError instanceof Error ? loadError.message : "Errore caricamento credenziali Capacitas");
    } finally {
      setCapacitasLoading(false);
    }
  }

  function resetCapacitasForm(): void {
    setCapacitasForm(DEFAULT_CAPACITAS_FORM);
  }

  function buildCapacitasDiagnosis(detail: string | null, statusCode: number | null): string | null {
    const normalized = normalizeIssueText(detail);

    if (normalized.includes("token non trovato")) {
      return "Il login HTTP risponde 200 ma il backend non riesce a estrarre il token di sessione. Di solito significa login rifiutato senza redirect, markup del form cambiato, oppure cookie AUTH_COOKIE non impostato dal portale.";
    }
    if (normalized.includes("viewstate")) {
      return "La pagina SSO sembra aver cambiato i campi ASP.NET richiesti. Va verificato il parsing di __VIEWSTATE / __EVENTVALIDATION nel backend.";
    }
    if (statusCode === 502) {
      return "Il frontend raggiunge correttamente il backend, ma il backend non completa la negoziazione con il portale esterno. Il punto da verificare e il parser di login Capacitas o la risposta HTML reale post-login.";
    }
    return null;
  }

  async function handleSave(): Promise<void> {
    const token = getStoredAccessToken();
    if (!token) return;

    setBusy(true);
    try {
      await saveElaborazioneCredentials(token, formState);
      await loadCredentials();
      setFormState((current) => ({ ...current, sister_password: "" }));
      setStatusMessage("Credenziali SISTER salvate nella pagina unificata del modulo elaborazioni.");
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
      await deleteElaborazioneCredentials(token);
      await loadCredentials();
      setFormState({
        sister_username: "",
        sister_password: "",
        convenzione: "",
        codice_richiesta: "",
        ufficio_provinciale: DEFAULT_UFFICIO,
      });
      setStatusMessage("Credenziali SISTER rimosse dalla configurazione elaborazioni.");
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
      const result = await testElaborazioneCredentials(
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

  async function handleSaveCapacitas(): Promise<void> {
    const token = getStoredAccessToken();
    if (!token) return;

    setCapacitasBusy(true);
    try {
      if (capacitasForm.id == null) {
        await createCapacitasCredential(token, {
          label: capacitasForm.label.trim(),
          username: capacitasForm.username.trim(),
          password: capacitasForm.password,
          active: capacitasForm.active,
          allowed_hours_start: capacitasForm.allowed_hours_start,
          allowed_hours_end: capacitasForm.allowed_hours_end,
        });
        setCapacitasStatusMessage("Credenziale Capacitas creata.");
      } else {
        await updateCapacitasCredential(token, capacitasForm.id, {
          label: capacitasForm.label.trim(),
          username: capacitasForm.username.trim(),
          password: capacitasForm.password.trim().length > 0 ? capacitasForm.password : undefined,
          active: capacitasForm.active,
          allowed_hours_start: capacitasForm.allowed_hours_start,
          allowed_hours_end: capacitasForm.allowed_hours_end,
        });
        setCapacitasStatusMessage("Credenziale Capacitas aggiornata.");
      }
      await loadCapacitasCredentials();
      resetCapacitasForm();
      setCapacitasError(null);
    } catch (saveError) {
      setCapacitasError(saveError instanceof Error ? saveError.message : "Errore salvataggio credenziale Capacitas");
      setCapacitasStatusMessage(null);
    } finally {
      setCapacitasBusy(false);
    }
  }

  async function handleDeleteCapacitas(credentialId: number): Promise<void> {
    const token = getStoredAccessToken();
    if (!token) return;

    setCapacitasBusy(true);
    try {
      await deleteCapacitasCredential(token, credentialId);
      await loadCapacitasCredentials();
      if (capacitasForm.id === credentialId) {
        resetCapacitasForm();
      }
      setCapacitasStatusMessage("Credenziale Capacitas rimossa.");
      setCapacitasError(null);
    } catch (deleteError) {
      setCapacitasError(deleteError instanceof Error ? deleteError.message : "Errore eliminazione credenziale Capacitas");
      setCapacitasStatusMessage(null);
    } finally {
      setCapacitasBusy(false);
    }
  }

  async function handleTestCapacitas(credentialId: number): Promise<void> {
    const token = getStoredAccessToken();
    if (!token) return;

    const credential = capacitasCredentials.find((item) => item.id === credentialId) ?? null;
    const startedAt = new Date().toISOString();
    setCapacitasTestingId(credentialId);
    setCapacitasTestDialog({
      open: true,
      phase: "running",
      credential,
      startedAt,
      finishedAt: null,
      statusCode: null,
      title: "Test Capacitas in corso",
      summary: "Sto verificando il login SSO e l'estrazione della sessione del portale esterno.",
      backendDetail: null,
      tokenPreview: null,
      diagnosis: null,
    });
    try {
      const result = await testCapacitasCredential(token, credentialId);
      await loadCapacitasCredentials();
      if (result.ok) {
        setCapacitasStatusMessage(`Connessione Capacitas confermata${result.token ? ` · token ${result.token}` : ""}.`);
        setCapacitasError(null);
        setCapacitasTestDialog((current) => ({
          ...current,
          phase: "success",
          finishedAt: new Date().toISOString(),
          statusCode: 200,
          title: "Test Capacitas completato",
          summary: "Autenticazione completata con successo e sessione rilevata dal backend.",
          backendDetail: result.error ?? "Login completato senza errori.",
          tokenPreview: result.token,
          diagnosis: "Il backend ha ottenuto una sessione valida. Puoi usare questa credenziale per ricerca e diagnostica inVOLTURE.",
        }));
      } else {
        setCapacitasError(result.error ?? "Test Capacitas fallito");
        setCapacitasStatusMessage(null);
        setCapacitasTestDialog((current) => ({
          ...current,
          phase: "error",
          finishedAt: new Date().toISOString(),
          statusCode: 200,
          title: "Test Capacitas fallito",
          summary: "Il backend ha risposto, ma il test non ha restituito una sessione valida.",
          backendDetail: result.error ?? null,
          tokenPreview: result.token,
          diagnosis: buildCapacitasDiagnosis(result.error ?? null, 200),
        }));
      }
    } catch (testError) {
      const message = testError instanceof Error ? testError.message : "Errore test credenziale Capacitas";
      const statusCode = testError instanceof ApiError ? testError.status ?? null : null;
      const backendDetail =
        testError instanceof ApiError
          ? typeof testError.detailData === "string"
            ? testError.detailData
            : testError.detailData != null
              ? JSON.stringify(testError.detailData, null, 2)
              : message
          : message;

      setCapacitasError(message);
      setCapacitasStatusMessage(null);
      setCapacitasTestDialog((current) => ({
        ...current,
        phase: "error",
        finishedAt: new Date().toISOString(),
        statusCode,
        title: "Test Capacitas interrotto",
        summary: "Il backend ha restituito un errore durante il tentativo di login verso il portale esterno.",
        backendDetail,
        tokenPreview: null,
        diagnosis: buildCapacitasDiagnosis(backendDetail, statusCode),
      }));
    } finally {
      setCapacitasTestingId(null);
    }
  }

  const refreshConnectionTest = useCallback(async (token: string, testId: string): Promise<void> => {
    try {
      const result = await getElaborazioneCredentialTest(token, testId);
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

    const socket = createElaborazioneCredentialTestWebSocket(activeTestId, token);
    if (!socket) return;
    testSocketRef.current = socket;

    socket.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data) as ElaborazioneCredentialTestWebSocketEvent;
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
  const isEditingCapacitas = capacitasForm.id != null;
  const canSaveCapacitas = Boolean(
    capacitasForm.label.trim() &&
      capacitasForm.username.trim() &&
      (isEditingCapacitas || capacitasForm.password.trim()),
  );

  const hasSisterCredentials = Boolean(credentialStatus?.configured);
  const activeCapacitasCount = capacitasCredentials.filter((credential) => credential.active).length;
  const capacitasWarningCount = capacitasCredentials.filter((credential) => Boolean(credential.last_error)).length;
  const latestCapacitasUsage = capacitasCredentials
    .map((credential) => credential.last_used_at)
    .filter((value): value is string => Boolean(value))
    .sort()
    .at(-1);
  const sisterStateLabel = hasSisterCredentials ? "Operativo" : "Non configurato";
  const sisterStateDescription = hasSisterCredentials
    ? credentialStatus?.credential?.sister_username ?? "Credenziali presenti nel vault"
    : "Salva username e password per attivare il worker visure";

  const content = (
    <>
      <CapacitasTestDialog
        state={capacitasTestDialog}
        onClose={() =>
          setCapacitasTestDialog((current) => ({
            ...current,
            open: false,
          }))
        }
      />

      <section className="overflow-hidden rounded-[28px] border border-[#d8dfd3] bg-[radial-gradient(circle_at_top_left,_rgba(212,231,220,0.95),_rgba(248,246,238,0.92)_55%,_rgba(255,255,255,0.98)_100%)] p-6 shadow-panel">
        <div className="grid gap-6 xl:grid-cols-[1.15fr,0.85fr]">
          <div>
            <div className="inline-flex items-center gap-2 rounded-full border border-white/80 bg-white/70 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.22em] text-[#1D4E35]">
              <LockIcon className="h-3.5 w-3.5" />
              Stitch-style workspace
            </div>
            <h3 className="mt-4 max-w-2xl text-3xl font-semibold tracking-tight text-[#183325]">
              Credenziali elaborazioni ripensate come console unica per accesso, verifica e rotazione operativa.
            </h3>
            <p className="mt-4 max-w-2xl text-sm leading-7 text-gray-600">
              La pagina ora separa meglio il canale SISTER dal pool Capacitas, mette in evidenza lo stato reale del modulo e
              concentra i controlli frequenti nella parte alta della schermata.
            </p>

            <div className="mt-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
              <StatCard
                eyebrow="SISTER"
                value={sisterStateLabel}
                description={sisterStateDescription}
                tone={hasSisterCredentials ? "success" : "default"}
              />
              <StatCard
                eyebrow="Pool Capacitas"
                value={`${activeCapacitasCount}/${capacitasCredentials.length}`}
                description={
                  capacitasCredentials.length > 0
                    ? `${capacitasWarningCount} account con warning recenti`
                    : "Nessun account ancora configurato"
                }
                tone={capacitasWarningCount > 0 ? "warning" : activeCapacitasCount > 0 ? "success" : "default"}
              />
              <StatCard
                eyebrow="Ultima attivita"
                value={latestCapacitasUsage ? formatDateTime(latestCapacitasUsage) : "Nessun uso"}
                description="Ultimo utilizzo registrato dal pool inVOLTURE."
              />
            </div>
          </div>

          <div className="grid gap-3 self-start">
            {error ? <StatusBanner tone="danger" title="Errore sezione SISTER" description={error} /> : null}
            {statusMessage ? <StatusBanner tone="success" title="Aggiornamento SISTER" description={statusMessage} /> : null}
            {capacitasError ? <StatusBanner tone="danger" title="Errore sezione Capacitas" description={capacitasError} /> : null}
            {capacitasStatusMessage ? (
              <StatusBanner tone="success" title="Aggiornamento Capacitas" description={capacitasStatusMessage} />
            ) : null}
            {!error && !statusMessage && !capacitasError && !capacitasStatusMessage ? (
              <div className="rounded-2xl border border-white/80 bg-white/70 p-4 text-sm leading-6 text-gray-600">
                Nessun alert aperto. Puoi aggiornare le credenziali, lanciare un test di connessione o gestire il pool
                Capacitas da questa stessa schermata.
              </div>
            ) : null}
          </div>
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-[1.3fr,0.7fr]">
        <article className="overflow-hidden rounded-[28px] border border-[#d9dfd6] bg-white shadow-panel">
          <div className="border-b border-[#edf1eb] bg-[linear-gradient(135deg,_rgba(29,78,53,0.06),_rgba(255,255,255,0.92))] px-6 py-5">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <div className="inline-flex items-center gap-2 rounded-full bg-[#e8f2ec] px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.2em] text-[#1D4E35]">
                  <LockIcon className="h-3.5 w-3.5" />
                  SISTER
                </div>
                <p className="mt-3 text-lg font-semibold text-gray-900">Credenziali e test realtime del canale visure</p>
                <p className="mt-2 max-w-2xl text-sm leading-6 text-gray-600">
                  Vault cifrato condiviso tra backend e worker Playwright. Se la password e valorizzata il test usa il form
                  corrente, altrimenti prova il profilo gia salvato.
                </p>
              </div>
              <div className="rounded-2xl border border-white/80 bg-white/80 px-4 py-3 text-right">
                <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-gray-400">Ultima verifica</p>
                <p className="mt-2 text-sm font-semibold text-gray-900">
                  {formatDateTime(credentialStatus?.credential?.verified_at ?? null)}
                </p>
              </div>
            </div>
          </div>

          <div className="grid gap-6 p-6 lg:grid-cols-[1.25fr,0.75fr]">
            <div className="space-y-5">
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

              <div className="flex flex-wrap items-center gap-3">
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
              </div>
            </div>

            <div className="space-y-4">
              <div className="rounded-[24px] border border-[#e1e8df] bg-[#f7faf7] p-5">
                <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-gray-400">Stato rapido</p>
                <div className="mt-4 space-y-3">
                  <div className="flex items-start gap-3 rounded-2xl border border-white bg-white/90 p-3">
                    <div className="rounded-xl bg-[#e8f2ec] p-2 text-[#1D4E35]">
                      <ServerIcon className="h-4 w-4" />
                    </div>
                    <div>
                      <p className="text-sm font-semibold text-gray-900">{hasSisterCredentials ? "Vault pronto" : "Configurazione assente"}</p>
                      <p className="mt-1 text-sm leading-6 text-gray-500">
                        {hasSisterCredentials
                          ? "Il backend dispone gia di una credenziale persistente per il worker."
                          : "Inserisci le credenziali per attivare batch e visure singole."}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-start gap-3 rounded-2xl border border-white bg-white/90 p-3">
                    <div className="rounded-xl bg-[#eef3ff] p-2 text-[#3056d3]">
                      <RefreshIcon className="h-4 w-4" />
                    </div>
                    <div>
                      <p className="text-sm font-semibold text-gray-900">Ufficio corrente</p>
                      <p className="mt-1 text-sm leading-6 text-gray-500">{formState.ufficio_provinciale || DEFAULT_UFFICIO}</p>
                    </div>
                  </div>
                </div>
              </div>

              {testResult && testResultToneClassName ? (
                <div className={`rounded-[24px] border px-4 py-4 ${testResultToneClassName}`}>
                  <p className="text-sm font-semibold">
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
                  <p className="mt-2 text-sm leading-6">{testResult.message ?? "Richiesta inoltrata al worker elaborazioni."}</p>
                  <p className="mt-3 text-[11px] uppercase tracking-[0.18em]">
                    Stato: {testResult.status} · Modalita&apos;: {testResult.mode ?? "worker"} · Reachable:{" "}
                    {testResult.reachable == null ? "n/d" : testResult.reachable ? "si" : "no"} · Auth:{" "}
                    {testResult.authenticated == null ? "n/d" : testResult.authenticated ? "si" : "no"}
                  </p>
                  {hasExistingSessionIssue ? (
                    <div className="mt-3 rounded-2xl border border-amber-200/80 bg-white/75 px-3 py-3 text-sm leading-6 text-amber-950">
                      Chiudi eventuali sessioni SISTER aperte su altre postazioni, attendi qualche minuto e poi ripeti il test.
                    </div>
                  ) : null}
                </div>
              ) : (
                <div className="rounded-[24px] border border-dashed border-[#dce3da] bg-[#fbfcfa] px-4 py-4 text-sm leading-6 text-gray-500">
                  Nessun test recente visualizzato. Avvia un test per vedere qui autenticazione, raggiungibilita e feedback del
                  worker in tempo reale.
                </div>
              )}
            </div>
          </div>
        </article>

        <aside className="space-y-6">
          <article className="rounded-[28px] border border-[#d9dfd6] bg-white p-6 shadow-panel">
            <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-gray-400">Dettagli SISTER</p>
            <div className="mt-4 grid gap-3">
              <DetailCard label="Configurazione" value={hasSisterCredentials ? "Credenziali presenti" : "Nessuna credenziale salvata"} />
              <DetailCard label="Username" value={credentialStatus?.credential?.sister_username ?? "—"} />
              <DetailCard label="Ultima verifica" value={formatDateTime(credentialStatus?.credential?.verified_at ?? null)} />
              <DetailCard label="Ultimo update" value={formatDateTime(credentialStatus?.credential?.updated_at ?? null)} />
            </div>
          </article>

          <article className="rounded-[28px] border border-[#d9dfd6] bg-[#16261d] p-6 text-white shadow-panel">
            <div className="flex items-start gap-3">
              <div className="rounded-2xl bg-white/10 p-3">
                <CheckIcon className="h-5 w-5" />
              </div>
              <div>
                <p className="text-sm font-semibold">Flusso consigliato</p>
                <p className="mt-2 text-sm leading-6 text-white/70">
                  Salva le credenziali, lancia un test realtime, poi verifica che Capacitas abbia almeno un account attivo
                  senza warning prima di tornare ai batch.
                </p>
              </div>
            </div>
            <div className="mt-5 rounded-2xl border border-white/10 bg-white/5 p-4">
              <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-white/45">Test Capacitas</p>
              <p className="mt-2 text-sm leading-6 text-white/75">
                Il pulsante <span className="font-semibold text-white">Test</span> apre ora una modal con stato del test,
                codice HTTP, dettaglio backend e diagnosi operativa del fallimento.
              </p>
            </div>
          </article>
        </aside>
      </section>

      <section className="grid gap-6 xl:grid-cols-[0.95fr,1.05fr]">
        <article className="overflow-hidden rounded-[28px] border border-[#d9dfd6] bg-white shadow-panel">
          <div className="border-b border-[#edf1eb] bg-[linear-gradient(135deg,_rgba(22,38,29,0.04),_rgba(255,255,255,0.98))] px-6 py-5">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <div className="inline-flex items-center gap-2 rounded-full bg-[#eff3ff] px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.2em] text-[#3056d3]">
                  <UsersIcon className="h-3.5 w-3.5" />
                  Capacitas
                </div>
                <p className="mt-3 text-lg font-semibold text-gray-900">Gestione del pool account inVOLTURE</p>
                <p className="mt-2 max-w-xl text-sm leading-6 text-gray-600">
                  Ogni account puo avere finestra oraria dedicata, health check manuale e stato operativo indipendente.
                </p>
              </div>
              <div className="rounded-2xl border border-[#e4e9f6] bg-[#f6f8ff] px-4 py-3 text-right">
                <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[#5c6aa5]">Pool attivo</p>
                <p className="mt-2 text-sm font-semibold text-gray-900">
                  {activeCapacitasCount} attivi su {capacitasCredentials.length}
                </p>
              </div>
            </div>
          </div>

          <div className="space-y-5 p-6">
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              <label className="space-y-2 xl:col-span-2">
                <span className="label-caption">Label operativa</span>
                <input
                  className="form-control"
                  placeholder="Account principale"
                  value={capacitasForm.label}
                  onChange={(event) => setCapacitasForm((current) => ({ ...current, label: event.target.value }))}
                />
              </label>
              <label className="space-y-2">
                <span className="label-caption">Username</span>
                <input
                  className="form-control"
                  placeholder="capacitas-user"
                  value={capacitasForm.username}
                  onChange={(event) => setCapacitasForm((current) => ({ ...current, username: event.target.value }))}
                />
              </label>
              <label className="space-y-2">
                <span className="label-caption">{isEditingCapacitas ? "Nuova password" : "Password"}</span>
                <input
                  className="form-control"
                  placeholder={isEditingCapacitas ? "Lascia vuoto per non cambiarla" : "Password Capacitas"}
                  type="password"
                  value={capacitasForm.password}
                  onChange={(event) => setCapacitasForm((current) => ({ ...current, password: event.target.value }))}
                />
              </label>
              <label className="space-y-2">
                <span className="label-caption">Fascia da</span>
                <input
                  className="form-control"
                  max={23}
                  min={0}
                  type="number"
                  value={capacitasForm.allowed_hours_start}
                  onChange={(event) =>
                    setCapacitasForm((current) => ({
                      ...current,
                      allowed_hours_start: Number.parseInt(event.target.value || "0", 10),
                    }))
                  }
                />
              </label>
              <label className="space-y-2">
                <span className="label-caption">Fascia a</span>
                <input
                  className="form-control"
                  max={23}
                  min={0}
                  type="number"
                  value={capacitasForm.allowed_hours_end}
                  onChange={(event) =>
                    setCapacitasForm((current) => ({
                      ...current,
                      allowed_hours_end: Number.parseInt(event.target.value || "23", 10),
                    }))
                  }
                />
              </label>
              <label className="flex items-center gap-3 rounded-2xl border border-gray-200 bg-[#f8faf8] px-4 py-3 xl:col-span-2">
                <input
                  checked={capacitasForm.active}
                  className="h-4 w-4 accent-[#1D4E35]"
                  type="checkbox"
                  onChange={(event) => setCapacitasForm((current) => ({ ...current, active: event.target.checked }))}
                />
                <span className="text-sm text-gray-700">Credenziale attiva e disponibile per le ricerche</span>
              </label>
            </div>

            <div className="flex flex-wrap items-center gap-3">
              <button
                className="btn-primary"
                disabled={capacitasBusy || !canSaveCapacitas}
                onClick={() => void handleSaveCapacitas()}
                type="button"
              >
                {capacitasBusy ? "Salvataggio..." : isEditingCapacitas ? "Aggiorna account" : "Aggiungi account"}
              </button>
              <button className="btn-secondary" disabled={capacitasBusy} onClick={resetCapacitasForm} type="button">
                {isEditingCapacitas ? "Annulla modifica" : "Reset form"}
              </button>
              <span className="text-xs text-gray-400">
                Se la fascia attraversa la mezzanotte, il backend la interpreta come finestra notturna.
              </span>
            </div>
          </div>
        </article>

        <article className="rounded-[28px] border border-[#d9dfd6] bg-white p-6 shadow-panel">
          <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-gray-400">Monitor operativo</p>
          <div className="mt-4 grid gap-3">
            <div className="rounded-2xl border border-[#e4e9f6] bg-[#f6f8ff] p-4">
              <div className="flex items-start gap-3">
                <div className="rounded-xl bg-white p-2 text-[#3056d3]">
                  <UsersIcon className="h-4 w-4" />
                </div>
                <div>
                  <p className="text-sm font-semibold text-gray-900">Distribuzione account</p>
                  <p className="mt-1 text-sm leading-6 text-gray-600">
                    {capacitasCredentials.length > 0
                      ? `${activeCapacitasCount} account attivi, ${capacitasCredentials.length - activeCapacitasCount} disattivi.`
                      : "Nessun account disponibile nel pool."}
                  </p>
                </div>
              </div>
            </div>

            <div className="rounded-2xl border border-[#f1e0af] bg-[#fff9e8] p-4">
              <div className="flex items-start gap-3">
                <div className="rounded-xl bg-white p-2 text-[#a36900]">
                  <AlertTriangleIcon className="h-4 w-4" />
                </div>
                <div>
                  <p className="text-sm font-semibold text-gray-900">Warning recenti</p>
                  <p className="mt-1 text-sm leading-6 text-gray-600">
                    {capacitasWarningCount > 0
                      ? `${capacitasWarningCount} account richiedono controllo o nuovo test di connessione.`
                      : "Nessun errore recente registrato sul pool."}
                  </p>
                </div>
              </div>
            </div>

            <div className="rounded-2xl border border-[#dfe7dd] bg-[#f8faf8] p-4">
              <div className="flex items-start gap-3">
                <div className="rounded-xl bg-white p-2 text-[#1D4E35]">
                  <SearchIcon className="h-4 w-4" />
                </div>
                <div>
                  <p className="text-sm font-semibold text-gray-900">Ultimo utilizzo</p>
                  <p className="mt-1 text-sm leading-6 text-gray-600">
                    {latestCapacitasUsage
                      ? `Pool utilizzato l'ultima volta ${formatDateTime(latestCapacitasUsage)}.`
                      : "Nessun utilizzo registrato finora."}
                  </p>
                </div>
              </div>
            </div>
          </div>
        </article>
      </section>

      <article className="overflow-hidden rounded-[28px] border border-[#d9dfd6] bg-white p-0 shadow-panel">
        <div className="border-b border-[#edf1eb] px-6 py-5">
          <p className="text-lg font-semibold text-gray-900">Pool Capacitas</p>
          <p className="mt-2 text-sm leading-6 text-gray-500">
            Account disponibili per la ricerca anagrafica `inVOLTURE`, con visibilita immediata su fascia oraria, utilizzo e
            fallimenti consecutivi.
          </p>
        </div>
        {capacitasLoading ? (
          <div className="p-6 text-sm text-gray-500">Caricamento credenziali Capacitas.</div>
        ) : capacitasCredentials.length === 0 ? (
          <div className="p-6 text-sm text-gray-500">Nessuna credenziale Capacitas configurata.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Label</th>
                  <th>Username</th>
                  <th>Stato</th>
                  <th>Finestra</th>
                  <th>Ultimo uso</th>
                  <th>Fallimenti</th>
                  <th>Azioni</th>
                </tr>
              </thead>
              <tbody>
                {capacitasCredentials.map((credential) => (
                  <tr key={credential.id}>
                    <td className="font-medium text-gray-900">{credential.label}</td>
                    <td>{credential.username}</td>
                    <td>
                      <div className="space-y-1">
                        <p>{summarizeCapacitasStatus(credential)}</p>
                        {credential.last_error ? (
                          <p className="max-w-[34ch] truncate text-xs text-red-600" title={credential.last_error}>
                            {credential.last_error}
                          </p>
                        ) : null}
                      </div>
                    </td>
                    <td>
                      {formatHour(credential.allowed_hours_start)} - {formatHour(credential.allowed_hours_end)}
                    </td>
                    <td>{formatDateTime(credential.last_used_at)}</td>
                    <td>{credential.consecutive_failures}</td>
                    <td>
                      <div className="flex flex-wrap gap-3 text-sm">
                        <button
                          className="text-[#1D4E35] transition hover:text-[#143726] disabled:cursor-not-allowed disabled:text-gray-300"
                          disabled={capacitasBusy}
                          onClick={() =>
                            setCapacitasForm({
                              id: credential.id,
                              label: credential.label,
                              username: credential.username,
                              password: "",
                              active: credential.active,
                              allowed_hours_start: credential.allowed_hours_start,
                              allowed_hours_end: credential.allowed_hours_end,
                            })
                          }
                          type="button"
                        >
                          Modifica
                        </button>
                        <button
                          className="text-[#1D4E35] transition hover:text-[#143726] disabled:cursor-not-allowed disabled:text-gray-300"
                          disabled={capacitasTestingId === credential.id}
                          onClick={() => void handleTestCapacitas(credential.id)}
                          type="button"
                        >
                          {capacitasTestingId === credential.id ? "Test..." : "Test"}
                        </button>
                        <button
                          className="text-red-600 transition hover:text-red-700 disabled:cursor-not-allowed disabled:text-red-200"
                          disabled={capacitasBusy}
                          onClick={() => void handleDeleteCapacitas(credential.id)}
                          type="button"
                        >
                          Elimina
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </article>
    </>
  );

  if (embedded) {
    return <div className="space-y-6">{content}</div>;
  }

  return (
    <ProtectedPage
      title="Credenziali"
      description="Hub operativo del modulo elaborazioni per SISTER e Capacitas."
      breadcrumb="Elaborazioni / Credenziali"
    >
      {content}
    </ProtectedPage>
  );
}
