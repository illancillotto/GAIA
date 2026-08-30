"use client";

import { useEffect, useState } from "react";

import { AutoSyncActivityDashboard } from "@/components/elaborazioni/autosync-activity-dashboard";
import { ElaborazioneNoticeCard, ElaborazionePanelHeader } from "@/components/elaborazioni/module-chrome";
import { ElaborazioneStatusBadge } from "@/components/elaborazioni/status-badge";
import { RefreshIcon } from "@/components/ui/icons";
import {
  getElaborazioneCredentials,
  getElaborazioneRuoloAutoSyncStatus,
  refreshElaborazioneRuoloAutoSyncSource,
  runElaborazioneRuoloAutoSyncNow,
  updateElaborazioneRuoloAutoSyncConfig,
} from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import { formatDateTime } from "@/lib/presentation";
import type {
  CatastoPerpetualSyncItem,
  ElaborazioneCredential,
  ElaborazioneRuoloAutoSyncStatus,
} from "@/types/api";

type SyncDraft = {
  credentialIds: string[];
  primaryEnabled: boolean;
  secondaryEnabled: boolean;
  roleParcelHours: number;
  roleSubjectHours: number;
  consortiumParcelHours: number;
  registrySubjectHours: number;
  batchSize: number;
};

type SyncState = {
  credentials: ElaborazioneCredential[];
  status: ElaborazioneRuoloAutoSyncStatus | null;
  draft: SyncDraft | null;
  busy: boolean;
  error: string | null;
  info: string | null;
};

const INITIAL_STATE: SyncState = {
  credentials: [], status: null, draft: null, busy: false, error: null, info: null,
};

const REFRESH_FIELDS: Array<[string, keyof SyncDraft]> = [
  ["Aggiorna particelle Ruolo ogni (ore)", "roleParcelHours"],
  ["Aggiorna soggetti Ruolo ogni (ore)", "roleSubjectHours"],
  ["Aggiorna particelle consorzio ogni (ore)", "consortiumParcelHours"],
  ["Aggiorna soggetti anagrafe ogni (ore)", "registrySubjectHours"],
];

const ITALIAN_INTERVAL_NUMBER = new Intl.NumberFormat("it-IT", { maximumFractionDigits: 1 });

function refreshIntervalDescription(hours: number): string {
  const days = hours / 24;
  return `${hours} ${hours === 1 ? "ora" : "ore"} · ${ITALIAN_INTERVAL_NUMBER.format(days)} ${days === 1 ? "giorno" : "giorni"}`;
}

const SCOPES: Array<[string, string]> = [
  ["Particelle ruolo", "ruolo_particella"],
  ["Soggetti ruolo", "ruolo_soggetto"],
  ["Particelle consorzio", "consorzio_particella"],
  ["Soggetti anagrafe", "anagrafe_soggetto"],
];

type SyncAction = "save" | "toggle" | "refresh" | "run";

const REFRESH_TIMEOUT_MS = 30_000;
const REFRESH_TIMEOUT_MESSAGE = "Aggiornamento non completato entro il tempo massimo. Puoi riprovare.";

async function withRefreshTimeout<T>(operation: Promise<T>): Promise<T> {
  let timeoutId: number;
  const timeout = new Promise<never>((_resolve, reject) => {
    timeoutId = window.setTimeout(() => reject(new Error(REFRESH_TIMEOUT_MESSAGE)), REFRESH_TIMEOUT_MS);
  });
  try {
    return await Promise.race([operation, timeout]);
  } finally {
    window.clearTimeout(timeoutId!);
  }
}

function configActionEnabled(action: SyncAction, currentEnabled: boolean): boolean | null {
  if (action === "save") return currentEnabled;
  if (action === "toggle") return !currentEnabled;
  return null;
}

function configActionMessage(action: SyncAction, enabled: boolean): string {
  if (action === "save") return "Configurazione aggiornata";
  return enabled ? "Sincronizzazione continua attivata" : "Sincronizzazione continua disattivata";
}

function draftHasSelectedCredentials(draft: SyncDraft | null): boolean {
  return Boolean(draft?.credentialIds?.length);
}

function draftFromStatus(status: ElaborazioneRuoloAutoSyncStatus): SyncDraft {
  const config = status.config;
  return {
    credentialIds: config.credential_ids ?? (config.credential_id ? [config.credential_id] : []),
    primaryEnabled: config.primary_enabled,
    secondaryEnabled: config.secondary_enabled,
    roleParcelHours: config.role_parcel_refresh_hours,
    roleSubjectHours: config.role_subject_refresh_hours,
    consortiumParcelHours: config.consortium_parcel_refresh_hours,
    registrySubjectHours: config.registry_subject_refresh_hours,
    batchSize: config.batch_size,
  };
}

function itemLabel(item: CatastoPerpetualSyncItem): string {
  if (item.search_mode === "soggetto") {
    return `${item.subject_kind ?? "Soggetto"} · ${item.subject_identifier ?? item.intestazione ?? "identificativo mancante"}`;
  }
  return `${item.comune ?? "Comune non risolto"} · Fg.${item.foglio ?? "-"} Part.${item.particella ?? "-"}`;
}

function useContinuousSyncState() {
  const [state, setState] = useState<SyncState>(INITIAL_STATE);

  async function reload(): Promise<void> {
    const token = getStoredAccessToken();
    if (!token) return;
    const [credentialStatus, status] = await Promise.all([
      getElaborazioneCredentials(token), getElaborazioneRuoloAutoSyncStatus(token),
    ]);
    setState((current) => ({
      ...current,
      credentials: credentialStatus.credentials,
      status,
      draft: current.draft ?? draftFromStatus(status),
      error: null,
    }));
  }

  useEffect(() => {
    let active = true;
    const load = () => reload().catch((error: unknown) => {
      if (active) setState((current) => ({ ...current, error: error instanceof Error ? error.message : "Errore caricamento sincronizzazione" }));
    });
    void load();
    const interval = window.setInterval(load, 15000);
    return () => { active = false; window.clearInterval(interval); };
  }, []);

  async function execute(action: SyncAction): Promise<void> {
    const token = getStoredAccessToken();
    const draft = state.draft;
    if (!token || !draft) return;
    setState((current) => ({ ...current, busy: true }));
    try {
      let message = "Configurazione aggiornata";
      const configEnabled = configActionEnabled(action, state.status!.config.enabled);
      if (configEnabled !== null) {
        const enabled = configEnabled;
        await updateElaborazioneRuoloAutoSyncConfig(token, { enabled, credential_id: null, credential_ids: draft.credentialIds, primary_enabled: draft.primaryEnabled, secondary_enabled: draft.secondaryEnabled, role_parcel_refresh_hours: draft.roleParcelHours, role_subject_refresh_hours: draft.roleSubjectHours, consortium_parcel_refresh_hours: draft.consortiumParcelHours, registry_subject_refresh_hours: draft.registrySubjectHours, batch_size: draft.batchSize });
        message = configActionMessage(action, enabled);
      } else {
        const result = action === "refresh" ? await withRefreshTimeout(refreshElaborazioneRuoloAutoSyncSource(token)) : await runElaborazioneRuoloAutoSyncNow(token);
        message = result.message;
      }
      await reload();
      setState((current) => ({ ...current, info: message, error: null }));
    } catch (error) {
      setState((current) => ({ ...current, error: error instanceof Error ? error.message : "Errore sincronizzazione" }));
    } finally {
      setState((current) => ({ ...current, busy: false }));
    }
  }

  const setDraft = (patch: Partial<SyncDraft>) => setState((current) => (
    current.draft ? { ...current, draft: { ...current.draft, ...patch } } : current
  ));
  return { state, setState, setDraft, execute };
}

function CredentialPool({ state, setState }: { state: SyncState; setState: React.Dispatch<React.SetStateAction<SyncState>> }) {
  const selectedIds = state.draft?.credentialIds ?? [];
  const availableIds = state.status?.available_credential_ids ?? [];
  const activeCredentials = state.credentials.filter((credential) => credential.active);
  const setCredentialIds = (credentialIds: string[]) => setState((current) => ({
    ...current,
    draft: { ...current.draft!, credentialIds },
  }));
  return (
    <fieldset className="space-y-3" disabled={state.busy || !state.draft}>
      <legend className="sr-only">Pool credenziali SISTER</legend>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className="label-caption">Pool credenziali SISTER</p>
          <p className="mt-1 text-xs text-gray-500">{selectedIds.length} di {activeCredentials.length} selezionate</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button className="btn-secondary px-3 py-2 text-xs" disabled={state.busy || selectedIds.length === activeCredentials.length} onClick={() => setCredentialIds(activeCredentials.map((credential) => credential.id))} type="button">Seleziona tutte</button>
          <button className="btn-secondary px-3 py-2 text-xs" disabled={state.busy || selectedIds.length === 0} onClick={() => setCredentialIds([])} type="button">Deseleziona tutte</button>
        </div>
      </div>
      <div className="grid gap-2 sm:grid-cols-2">
        {activeCredentials.map((credential) => {
          const selected = selectedIds.includes(credential.id);
          const available = availableIds.includes(credential.id);
          const toggle = () => setCredentialIds(selected ? selectedIds.filter((id) => id !== credential.id) : [...selectedIds, credential.id]);
          return (
            <label className={`min-h-16 cursor-pointer rounded-[18px] border p-3 transition-colors ${selected ? "border-[#80a98b] bg-white ring-1 ring-[#d7e6da]" : "border-gray-200 bg-gray-50"}`} key={credential.id}>
              <span className="flex items-center gap-3">
                <input checked={selected} className="h-5 w-5 shrink-0 accent-[#477a55]" disabled={state.busy} onChange={toggle} type="checkbox" />
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-sm font-semibold text-gray-900">{credential.label}</span>
                  <span className="mt-0.5 block truncate text-xs text-gray-500">{credential.sister_username}</span>
                </span>
                <span className={`shrink-0 rounded-full px-2 py-1 text-[11px] font-medium ${available ? "bg-emerald-100 text-emerald-800" : "bg-amber-100 text-amber-800"}`}>{available ? "Disponibile" : "Non disponibile"}</span>
              </span>
            </label>
          );
        })}
      </div>
    </fieldset>
  );
}

function ScopeCoverage({ status }: { status: ElaborazioneRuoloAutoSyncStatus | null }) {
  return <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-1">{SCOPES.map(([label, scope]) => {
    const counts = status?.scope_counts[scope] ?? {};
    const total = Object.values(counts).reduce((sum, value) => sum + value, 0);
    return <div className="rounded-[20px] border border-gray-100 bg-white p-4" key={scope}><p className="label-caption">{label}</p><p className="mt-2 text-2xl font-semibold text-gray-900">{counts.completed ?? 0}<span className="text-sm font-normal text-gray-400"> / {total}</span></p><p className="mt-1 text-sm text-gray-500">{counts.processing ?? 0} in corso · {(counts.pending ?? 0) + (counts.queued ?? 0)} in attesa</p></div>;
  })}</div>;
}

function SyncItemList({ items, errorList }: { items: CatastoPerpetualSyncItem[]; errorList?: boolean }) {
  if (!items.length) return <p className="text-sm text-gray-500">Nessun elemento da mostrare.</p>;
  return <div className="mt-3 space-y-3">{items.map((item) => <div className={`rounded-[18px] border px-4 py-3 ${errorList ? "border-red-100 bg-red-50" : "border-gray-100 bg-gray-50"}`} key={item.id}><div className="flex items-start justify-between gap-3"><div><p className="text-sm font-medium text-gray-900">{itemLabel(item)}</p><p className="mt-1 text-xs text-gray-500">tentativi {item.attempt_count} · prossimo ciclo {formatDateTime(item.next_due_at)}</p>{item.last_error_message ? <p className="mt-1 text-sm text-red-700">{item.last_error_message}</p> : null}</div><span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-700">{item.status}</span></div></div>)}</div>;
}

function SyncNotice({ state }: { state: SyncState }) {
  if (state.error) return <ElaborazioneNoticeCard title="Errore sincronizzazione" description={state.error} tone="danger" />;
  if (state.info) return <ElaborazioneNoticeCard title="Sincronizzazione catastale" description={state.info} tone="success" />;
  return null;
}

function RunningBatch({ status }: { status: ElaborazioneRuoloAutoSyncStatus | null }) {
  const batch = status?.running_batch;
  if (!batch) return null;
  return <div className="rounded-[24px] border border-[#d9dfd6] bg-[#eef6f0] p-4"><div className="flex justify-between gap-3"><div><p className="text-sm font-semibold">{batch.name ?? "Micro-batch attivo"}</p><p className="mt-1 text-sm text-gray-600">{batch.current_operation ?? "In lavorazione"}</p></div><ElaborazioneStatusBadge status={batch.status} /></div></div>;
}

function RefreshIntervalFields({ draft, disabled, setDraft }: {
  draft: SyncDraft | null;
  disabled: boolean;
  setDraft: (patch: Partial<SyncDraft>) => void;
}) {
  return <section className="space-y-3" aria-labelledby="refresh-intervals-title"><div><h3 className="text-sm font-semibold text-gray-900" id="refresh-intervals-title">Intervalli di aggiornamento</h3><p className="mt-1 text-xs text-gray-500">Questi valori indicano la frequenza del nuovo controllo, non il numero di particelle o soggetti.</p></div><div className="grid gap-3 sm:grid-cols-2">{REFRESH_FIELDS.map(([label, field]) => <div className="space-y-1 rounded-[18px] border border-gray-100 bg-white p-3" key={field}><label className="block text-xs font-medium text-gray-600" htmlFor={`refresh-${field}`}>{label}</label><input aria-describedby={`refresh-${field}-description`} className="form-control" disabled={disabled} id={`refresh-${field}`} min="1" onChange={(event) => setDraft({ [field]: Math.max(1, Number(event.target.value) || 1) })} type="number" value={(draft?.[field] as number) ?? 1} /><span className="block text-xs text-gray-500" id={`refresh-${field}-description`}>{refreshIntervalDescription((draft?.[field] as number) ?? 1)}</span></div>)}</div></section>;
}

function BatchSizeField({ draft, disabled, setDraft }: {
  draft: SyncDraft | null;
  disabled: boolean;
  setDraft: (patch: Partial<SyncDraft>) => void;
}) {
  return <div className="space-y-1"><label className="block text-xs font-medium text-gray-600" htmlFor="autosync-batch-size">Righe per micro-batch</label><input aria-describedby="autosync-batch-size-description" className="form-control sm:max-w-xs" disabled={disabled} id="autosync-batch-size" min="1" onChange={(event) => setDraft({ batchSize: Math.max(1, Number(event.target.value) || 1) })} type="number" value={draft?.batchSize ?? 1} /><span className="block text-xs text-gray-500" id="autosync-batch-size-description">Quantità massima elaborata in ogni micro-batch.</span></div>;
}

function SyncConfiguration({ state, setState, setDraft, execute }: {
  state: SyncState;
  setState: React.Dispatch<React.SetStateAction<SyncState>>;
  setDraft: (patch: Partial<SyncDraft>) => void;
  execute: (action: SyncAction) => Promise<void>;
}) {
  const draft = state.draft;
  const configurationInputsDisabled = state.busy || !draft;
  const canRun = draftHasSelectedCredentials(draft);
  const configurationDisabled = state.busy || !canRun || !(draft?.primaryEnabled || draft?.secondaryEnabled);
  return <><CredentialPool state={state} setState={setState} /><div className="grid gap-3 sm:grid-cols-2"><label className="rounded-[18px] border bg-white p-3 text-sm"><input checked={draft?.primaryEnabled ?? false} className="mr-2" disabled={configurationInputsDisabled} onChange={(event) => setDraft({ primaryEnabled: event.target.checked })} type="checkbox" />Priorità 1: ruolo</label><label className="rounded-[18px] border bg-white p-3 text-sm"><input checked={draft?.secondaryEnabled ?? false} className="mr-2" disabled={configurationInputsDisabled} onChange={(event) => setDraft({ secondaryEnabled: event.target.checked })} type="checkbox" />Priorità 2: consorzio e anagrafe</label></div><RefreshIntervalFields disabled={configurationInputsDisabled} draft={draft} setDraft={setDraft} /><BatchSizeField disabled={configurationInputsDisabled} draft={draft} setDraft={setDraft} /><div className="flex flex-wrap gap-3"><button className="btn-primary" disabled={configurationDisabled} onClick={() => void execute("toggle")} type="button">{state.status?.config.enabled ? "Metti su OFF" : "Metti su ON"}</button><button className="btn-secondary" disabled={configurationDisabled} onClick={() => void execute("save")} type="button">Salva configurazione</button><button className="btn-secondary" disabled={state.busy} onClick={() => void execute("refresh")} type="button">Aggiorna sorgente</button><button className="btn-secondary" disabled={state.busy || !canRun} onClick={() => void execute("run")} type="button">Esegui adesso</button></div><p className="text-xs text-gray-500">Stato: {state.status?.config.enabled ? "ON" : "OFF"}{state.status?.config.last_source_refresh_at ? ` · sorgente ${formatDateTime(state.status.config.last_source_refresh_at)}` : ""}</p></>;
}

export function ContinuousCatastoSyncPanel() {
  const { state, setState, setDraft, execute } = useContinuousSyncState();
  return (
    <div className="space-y-4">
      <SyncNotice state={state} />
      <AutoSyncActivityDashboard credentials={state.credentials} status={state.status} />
      <article className="overflow-hidden rounded-[28px] border border-[#d9dfd6] bg-white shadow-panel">
        <ElaborazionePanelHeader badge={<><RefreshIcon className="h-3.5 w-3.5" />Sync continua</>} title="Sincronizzazione catastale continua" description="Micro-batch perpetui: prima ruolo, poi patrimonio consortile e anagrafe. Il planner usa solo credenziali libere e nelle finestre operative." />
        <div className="space-y-6 p-6">
          <section aria-labelledby="autosync-configuration-title" className="space-y-4">
            <div><h2 className="text-lg font-semibold text-gray-950" id="autosync-configuration-title">Configurazione AutoSync</h2><p className="mt-1 text-sm text-gray-500">Credenziali, priorità, intervalli e dimensione dei micro-batch.</p></div>
          <div className="grid gap-4 lg:grid-cols-[1.2fr,1fr]">
            <div className="space-y-4 rounded-[24px] border border-gray-100 bg-gray-50 p-4">
              <SyncConfiguration execute={execute} setDraft={setDraft} setState={setState} state={state} />
            </div>
            <ScopeCoverage status={state.status} />
          </div>
          </section>
          <RunningBatch status={state.status} />
          <div className="grid gap-4 xl:grid-cols-2"><div className="rounded-[24px] border border-gray-100 p-4"><p className="text-sm font-semibold">Errori e retry</p><SyncItemList errorList items={state.status?.perpetual_error_items ?? []} /></div><div className="rounded-[24px] border border-gray-100 p-4"><p className="text-sm font-semibold">Coda recente</p><SyncItemList items={state.status?.perpetual_recent_items ?? []} /></div></div>
        </div>
      </article>
    </div>
  );
}
