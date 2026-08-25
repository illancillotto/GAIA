"use client";

import { AlertTriangleIcon, CheckIcon, RefreshIcon } from "@/components/ui/icons";
import type { PoolRunStatus } from "@/components/elaborazioni/sister-credential-pool-controller";
import { formatDateTime } from "@/lib/presentation";
import {
  classifySisterCredentialTest,
  type SisterCredentialTestPhase,
  type SisterCredentialTestProgress,
} from "@/lib/sister-credential-tests";
import type { ElaborazioneCredential, ElaborazioneCredentialTestResult } from "@/types/api";

export type SisterCredentialPoolViewProps = {
  credentials: ElaborazioneCredential[];
  selectedCredentialId: string | null;
  currentTestResult: ElaborazioneCredentialTestResult | null;
  embedded: boolean;
  controlsDisabled: boolean;
  bulkRunning: boolean;
  runStatus: PoolRunStatus;
  progressById: Record<string, SisterCredentialTestProgress>;
  singleTestingId: string | null;
  releaseBusy: boolean;
  resumeReleasedBusy: boolean;
  releasedBatchesCount: number;
  onSelectCredential: (credential: ElaborazioneCredential) => void;
  onMakeDefault: (credential: ElaborazioneCredential) => Promise<void>;
  onDeleteCredential: (credential: ElaborazioneCredential) => void;
  onTestCredential: (credential: ElaborazioneCredential) => Promise<void>;
  onTestAll: () => Promise<void>;
  onCancel: () => void;
  onReleaseSessions: () => Promise<void>;
  onReleaseCredential: (credential: ElaborazioneCredential) => Promise<void>;
  onResumeReleasedBatch: () => Promise<void>;
};

type PhasePresentation = { label: string; className: string; dotClassName: string };
const TERMINAL_PHASES = new Set<SisterCredentialTestPhase>(["success", "warning", "error"]);

function isActiveCredential(credential: ElaborazioneCredential): boolean {
  return credential.active;
}

function isVerifiedCredential(credential: ElaborazioneCredential): boolean {
  return Boolean(credential.verified_at);
}

function phasePresentation(phase: SisterCredentialTestPhase): PhasePresentation {
  switch (phase) {
    case "queued": return { label: "In coda", className: "bg-gray-100 text-gray-600", dotClassName: "bg-gray-400" };
    case "running": return { label: "In verifica", className: "bg-sky-100 text-sky-800", dotClassName: "animate-pulse bg-sky-500" };
    case "success": return { label: "Autenticata", className: "bg-emerald-100 text-emerald-800", dotClassName: "bg-emerald-500" };
    case "warning": return { label: "Da controllare", className: "bg-amber-100 text-amber-900", dotClassName: "bg-amber-500" };
    case "error": return { label: "Fallita", className: "bg-red-100 text-red-800", dotClassName: "bg-red-500" };
    case "stopped": return { label: "Non eseguita", className: "bg-gray-100 text-gray-600", dotClassName: "bg-gray-400" };
  }
}

function TestStateBadge({ progress }: { progress: SisterCredentialTestProgress | null }) {
  if (!progress) {
    return <span className="inline-flex items-center gap-1.5 rounded-full bg-gray-100 px-2.5 py-1 text-[11px] font-semibold text-gray-600"><span className="h-1.5 w-1.5 rounded-full bg-gray-400" />Da verificare</span>;
  }
  const presentation = phasePresentation(progress.phase);
  return <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-semibold ${presentation.className}`}><span className={`h-1.5 w-1.5 rounded-full ${presentation.dotClassName}`} />{presentation.label}</span>;
}

function resolveProgress(
  credential: ElaborazioneCredential,
  bulkProgress: SisterCredentialTestProgress | undefined,
  currentTest: ElaborazioneCredentialTestResult | null,
): SisterCredentialTestProgress | null {
  if (bulkProgress) return bulkProgress;
  if (currentTest?.credential_id === credential.id) return classifySisterCredentialTest(credential.id, currentTest);
  if (!credential.verified_at) return null;
  return { credentialId: credential.id, phase: "success", message: "Credenziale verificata in precedenza.", result: null };
}

function PoolProgress({
  status,
  credentials,
  progressById,
  onCancel,
}: Pick<SisterCredentialPoolViewProps, "credentials" | "progressById" | "onCancel"> & { status: PoolRunStatus }) {
  if (status === "idle") return null;
  let successCount = 0;
  let warningCount = 0;
  let errorCount = 0;
  for (const item of Object.values(progressById)) {
    if (item.phase === "success") successCount += 1;
    if (item.phase === "warning") warningCount += 1;
    if (item.phase === "error") errorCount += 1;
  }
  const testedCount = successCount + warningCount + errorCount;
  const percentage = credentials.length > 0 ? Math.round((testedCount / credentials.length) * 100) : 0;
  const runningCredential = credentials.find((credential) => progressById[credential.id]?.phase === "running");
  const title = status === "completed" ? "Verifica del pool completata" : status === "cancelled" ? "Verifica del pool interrotta" : status === "stopping" ? "Interruzione in corso" : "Verifica sequenziale in corso";

  return <div className="border-b border-[#dfe7dd] bg-[linear-gradient(110deg,_#f0f7f2,_#f8fbf8_55%,_#eef6f7)] px-4 py-4">
    <div className="flex flex-wrap items-start justify-between gap-3"><div><p className="text-sm font-semibold text-[#173d2a]">{title}</p><p className="mt-1 text-xs leading-5 text-gray-600">{runningCredential ? `Account corrente: ${runningCredential.label}. I test non vengono mai eseguiti in parallelo.` : `${testedCount} credenziali testate su ${credentials.length}.`}</p></div>
      {status === "running" || status === "stopping" ? <button className="rounded-xl border border-gray-300 bg-white px-3 py-1.5 text-xs font-semibold text-gray-700 transition hover:border-gray-400 disabled:cursor-wait disabled:opacity-60" disabled={status === "stopping"} onClick={onCancel} type="button">{status === "stopping" ? "Interruzione..." : "Interrompi"}</button> : null}
    </div>
    <div aria-label="Avanzamento test credenziali SISTER" aria-valuemax={credentials.length} aria-valuemin={0} aria-valuenow={testedCount} className="mt-3 h-2 overflow-hidden rounded-full bg-white/90" role="progressbar"><div className="h-full rounded-full bg-[#1D6B48] transition-[width] duration-500" style={{ width: `${percentage}%` }} /></div>
    <div className="mt-3 flex flex-wrap gap-2 text-[11px] font-semibold"><span className="rounded-full bg-white/90 px-2.5 py-1 text-gray-600">{testedCount}/{credentials.length} completati</span><span className="rounded-full bg-emerald-100 px-2.5 py-1 text-emerald-800">{successCount} autenticati</span><span className="rounded-full bg-amber-100 px-2.5 py-1 text-amber-900">{warningCount} da controllare</span><span className="rounded-full bg-red-100 px-2.5 py-1 text-red-800">{errorCount} falliti</span></div>
  </div>;
}

function PoolHeader(props: SisterCredentialPoolViewProps) {
  const activeCount = props.credentials.filter(isActiveCredential).length;
  const verifiedCount = props.credentials.filter(isVerifiedCredential).length;
  return <div className={`border-b border-[#e5ebe3] bg-white ${props.embedded ? "px-4 py-4" : "px-5 py-5"}`}><div className="flex flex-wrap items-start justify-between gap-4">
    <div className="max-w-2xl"><div className="flex flex-wrap items-center gap-2"><p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[#326447]">Pool credenziali SISTER</p><span className="rounded-full bg-[#eaf3ed] px-2.5 py-1 text-[10px] font-bold text-[#1D4E35]">{activeCount}/{props.credentials.length} attive</span><span className="rounded-full bg-sky-50 px-2.5 py-1 text-[10px] font-bold text-sky-800">{verifiedCount} verificate</span></div>
      <p className={`text-sm text-gray-600 ${props.embedded ? "mt-2 leading-5" : "mt-2 leading-6"}`}>Ogni profilo mostra configurazione, stato e ultimo test senza scorrimento orizzontale. Il test completo include anche gli account disattivati, ma il worker usa soltanto quelli attivi.</p>
      <p className={`text-xs ${props.releasedBatchesCount > 0 ? "text-amber-700" : "text-gray-500"} ${props.embedded ? "mt-2" : "mt-3"}`}>{props.releasedBatchesCount > 0 ? `${props.releasedBatchesCount} batch in pausa dopo il rilascio delle sessioni SISTER.` : "Nessun batch in pausa da rilascio sessioni disponibile per la ripartenza."}</p>
    </div>
    <PoolActions {...props} />
  </div></div>;
}

function PoolActions(props: SisterCredentialPoolViewProps) {
  return <div className="flex flex-wrap items-center gap-2">
    {props.bulkRunning ? <button className="btn-secondary" disabled type="button"><RefreshIcon className="mr-2 inline h-4 w-4 animate-spin" />Test {props.runStatus === "stopping" ? "in arresto" : "in corso"}</button> : <button className="rounded-2xl bg-[#1D4E35] px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-[#143726] disabled:cursor-not-allowed disabled:bg-gray-300" disabled={props.controlsDisabled || props.credentials.length === 0} onClick={() => void props.onTestAll()} type="button"><CheckIcon className="mr-2 inline h-4 w-4" />Testa tutte{props.credentials.length > 0 ? ` (${props.credentials.length})` : ""}</button>}
    <button className="btn-secondary" disabled={props.controlsDisabled || props.resumeReleasedBusy || props.releasedBatchesCount === 0} onClick={() => void props.onResumeReleasedBatch()} type="button">{props.resumeReleasedBusy ? "Ripresa..." : props.releasedBatchesCount > 0 ? `Riprendi batch${props.releasedBatchesCount > 1 ? ` (${props.releasedBatchesCount})` : ""}` : "Nessun batch in pausa"}</button>
    <button className="btn-secondary" disabled={props.controlsDisabled || props.releaseBusy} onClick={() => void props.onReleaseSessions()} type="button">{props.releaseBusy ? "Pausa..." : "Pausa e libera sessioni"}</button>
  </div>;
}

function CredentialDetails({ credential }: { credential: ElaborazioneCredential }) {
  return <dl className="mt-4 grid grid-cols-2 gap-x-4 gap-y-3 border-y border-gray-100 py-3 text-xs">
    <div className="min-w-0"><dt className="font-semibold uppercase tracking-[0.12em] text-[9px] text-gray-400">Convenzione</dt><dd className="mt-1 truncate text-gray-700" title={credential.convenzione ?? undefined}>{credential.convenzione || "Non indicata"}</dd></div>
    <div className="min-w-0"><dt className="font-semibold uppercase tracking-[0.12em] text-[9px] text-gray-400">Codice richiesta</dt><dd className="mt-1 truncate font-mono text-gray-700">{credential.codice_richiesta || "Non indicato"}</dd></div>
    <div className="min-w-0"><dt className="font-semibold uppercase tracking-[0.12em] text-[9px] text-gray-400">Ufficio</dt><dd className="mt-1 truncate text-gray-700">{credential.ufficio_provinciale}</dd></div>
    <div className="min-w-0"><dt className="font-semibold uppercase tracking-[0.12em] text-[9px] text-gray-400">Ultima verifica</dt><dd className="mt-1 truncate text-gray-700">{formatDateTime(credential.verified_at)}</dd></div>
  </dl>;
}

function CredentialActions(props: SisterCredentialPoolViewProps & { credential: ElaborazioneCredential; isTesting: boolean }) {
  return <div className="mt-4 grid grid-cols-2 gap-2 sm:flex sm:flex-wrap">
    <button className="rounded-xl border border-gray-200 px-3 py-1.5 text-xs font-semibold text-gray-700 transition hover:border-[#8eab97] hover:text-[#1D4E35] disabled:opacity-50" disabled={props.controlsDisabled} onClick={() => props.onSelectCredential(props.credential)} type="button">Modifica</button>
    {!props.credential.is_default ? <button className="rounded-xl border border-gray-200 px-3 py-1.5 text-xs font-semibold text-gray-700 transition hover:border-amber-300 hover:text-amber-800 disabled:opacity-50" disabled={props.controlsDisabled} onClick={() => void props.onMakeDefault(props.credential)} type="button">Rendi default</button> : null}
    <button className="rounded-xl border border-sky-200 bg-sky-50 px-3 py-1.5 text-xs font-semibold text-sky-800 transition hover:border-sky-300 hover:bg-sky-100 disabled:opacity-50" disabled={props.controlsDisabled} onClick={() => void props.onTestCredential(props.credential)} type="button">{props.isTesting ? "Test in corso" : "Testa"}</button>
    <button className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-1.5 text-xs font-semibold text-amber-900 transition hover:border-amber-300 hover:bg-amber-100 disabled:opacity-50" disabled={props.controlsDisabled || props.releaseBusy || !props.credential.active} onClick={() => void props.onReleaseCredential(props.credential)} type="button">{props.credential.active ? "Pausa e libera" : "Sessione in pausa"}</button>
    <button className="rounded-xl border border-red-100 px-3 py-1.5 text-xs font-semibold text-red-600 transition hover:border-red-200 hover:bg-red-50 disabled:opacity-50" disabled={props.controlsDisabled} onClick={() => props.onDeleteCredential(props.credential)} type="button">Elimina</button>
  </div>;
}

function CredentialCard(props: SisterCredentialPoolViewProps & { credential: ElaborazioneCredential }) {
  const progress = resolveProgress(props.credential, props.progressById[props.credential.id], props.currentTestResult);
  const isTesting = props.singleTestingId === props.credential.id || progress?.phase === "running";
  const terminal = progress && TERMINAL_PHASES.has(progress.phase) ? progress : null;
  return <article className={`relative overflow-hidden rounded-[22px] border bg-white p-4 transition ${props.selectedCredentialId === props.credential.id ? "border-[#5b8b6d] shadow-[0_12px_30px_-24px_rgba(29,78,53,0.9)]" : "border-[#e1e8df] hover:border-[#b9cbbd]"} ${props.credential.active ? "" : "opacity-75"}`}>
    <div className={`absolute inset-y-0 left-0 w-1 ${props.credential.is_default ? "bg-[#d9a628]" : props.credential.active ? "bg-[#4c8a64]" : "bg-gray-300"}`} />
    <div className="flex items-start justify-between gap-3 pl-1"><div className="min-w-0"><div className="flex flex-wrap items-center gap-2"><h3 className="truncate text-sm font-semibold text-gray-950">{props.credential.label}</h3>{props.credential.is_default ? <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-amber-900">Default</span> : null}<span className={`rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide ${props.credential.active ? "bg-emerald-50 text-emerald-800" : "bg-gray-100 text-gray-600"}`}>{props.credential.active ? "Attiva" : "Disattiva"}</span></div><p className="mt-1.5 truncate font-mono text-xs text-gray-500">{props.credential.sister_username}</p></div><TestStateBadge progress={progress} /></div>
    <CredentialDetails credential={props.credential} />
    {terminal ? <p className={`mt-3 line-clamp-2 rounded-xl px-3 py-2 text-xs leading-5 ${terminal.phase === "success" ? "bg-emerald-50 text-emerald-800" : terminal.phase === "warning" ? "bg-amber-50 text-amber-900" : "bg-red-50 text-red-800"}`} title={terminal.message}>{terminal.message}</p> : null}
    <CredentialActions {...props} credential={props.credential} isTesting={isTesting} />
  </article>;
}

function CredentialGrid(props: SisterCredentialPoolViewProps) {
  if (props.credentials.length === 0) return <div className={`${props.embedded ? "px-4 py-5" : "px-5 py-7"} text-center`}><div className="mx-auto flex h-10 w-10 items-center justify-center rounded-2xl bg-gray-100 text-gray-500"><AlertTriangleIcon className="h-5 w-5" /></div><p className="mt-3 text-sm font-semibold text-gray-800">Nessuna credenziale SISTER configurata</p><p className="mt-1 text-xs text-gray-500">Compila il form qui sopra per aggiungere il primo profilo operativo.</p></div>;
  return <div className={`grid ${props.embedded ? "gap-3 p-3 md:grid-cols-2" : "gap-4 p-4 md:grid-cols-2"}`}>{props.credentials.map((credential) => <CredentialCard {...props} credential={credential} key={credential.id} />)}</div>;
}

export function SisterCredentialPoolView(props: SisterCredentialPoolViewProps) {
  return <div className="overflow-hidden rounded-[24px] border border-[#d8e2d7] bg-[#fbfcfa] shadow-[0_16px_45px_-36px_rgba(22,55,37,0.7)]"><PoolHeader {...props} /><PoolProgress status={props.runStatus} credentials={props.credentials} progressById={props.progressById} onCancel={props.onCancel} /><CredentialGrid {...props} /></div>;
}
