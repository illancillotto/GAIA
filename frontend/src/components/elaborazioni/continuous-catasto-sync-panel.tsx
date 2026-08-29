"use client";

import { useEffect, useState } from "react";

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

const SLA_FIELDS: Array<[string, keyof SyncDraft]> = [
  ["Particelle a ruolo", "roleParcelHours"],
  ["Soggetti a ruolo", "roleSubjectHours"],
  ["Particelle consorzio", "consortiumParcelHours"],
  ["Soggetti anagrafe", "registrySubjectHours"],
  ["Righe per micro-batch", "batchSize"],
];

const SCOPES: Array<[string, string]> = [
  ["Particelle ruolo", "ruolo_particella"],
  ["Soggetti ruolo", "ruolo_soggetto"],
  ["Particelle consorzio", "consorzio_particella"],
  ["Soggetti anagrafe", "anagrafe_soggetto"],
];

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

  async function execute(action: "save" | "refresh" | "run"): Promise<void> {
    const token = getStoredAccessToken();
    const draft = state.draft;
    if (!token || !draft) return;
    setState((current) => ({ ...current, busy: true }));
    try {
      let message = "Configurazione aggiornata";
      if (action === "save") {
        const enabled = !state.status!.config.enabled;
        await updateElaborazioneRuoloAutoSyncConfig(token, { enabled, credential_id: null, credential_ids: draft.credentialIds, primary_enabled: draft.primaryEnabled, secondary_enabled: draft.secondaryEnabled, role_parcel_refresh_hours: draft.roleParcelHours, role_subject_refresh_hours: draft.roleSubjectHours, consortium_parcel_refresh_hours: draft.consortiumParcelHours, registry_subject_refresh_hours: draft.registrySubjectHours, batch_size: draft.batchSize });
        message = enabled ? "Sincronizzazione continua attivata" : "Sincronizzazione continua disattivata";
      } else {
        const result = action === "refresh" ? await refreshElaborazioneRuoloAutoSyncSource(token) : await runElaborazioneRuoloAutoSyncNow(token);
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

  const setDraft = (patch: Partial<SyncDraft>) => setState((current) => ({ ...current, draft: { ...current.draft!, ...patch } }));
  return { state, setState, setDraft, execute };
}

function CredentialPool({ state, setState }: { state: SyncState; setState: React.Dispatch<React.SetStateAction<SyncState>> }) {
  const selectedIds = state.draft?.credentialIds ?? [];
  const availableIds = state.status?.available_credential_ids ?? [];
  return (
    <div className="space-y-2">
      <span className="label-caption">Pool credenziali SISTER</span>
      <div className="grid gap-2 sm:grid-cols-2">
        {state.credentials.filter((credential) => credential.active).map((credential) => {
          const selected = selectedIds.includes(credential.id);
          const available = availableIds.includes(credential.id);
          const toggle = () => setState((current) => ({ ...current, draft: { ...current.draft!, credentialIds: selected ? selectedIds.filter((id) => id !== credential.id) : [...selectedIds, credential.id] } }));
          return (
            <label className={`rounded-[18px] border p-3 ${selected ? "border-[#80a98b] bg-white" : "border-gray-200 bg-gray-50"}`} key={credential.id}>
              <span className="flex items-start gap-3">
                <input checked={selected} disabled={state.busy} onChange={toggle} type="checkbox" />
                <span><span className="block text-sm font-semibold text-gray-900">{credential.label}</span><span className="block text-xs text-gray-500">{credential.sister_username} · {available ? "disponibile ora" : "occupata o fuori orario"}</span></span>
              </span>
            </label>
          );
        })}
      </div>
    </div>
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

function SyncConfiguration({ state, setState, setDraft, execute }: {
  state: SyncState;
  setState: React.Dispatch<React.SetStateAction<SyncState>>;
  setDraft: (patch: Partial<SyncDraft>) => void;
  execute: (action: "save" | "refresh" | "run") => Promise<void>;
}) {
  const draft = state.draft;
  const canRun = Boolean(draft?.credentialIds.length);
  return <><CredentialPool state={state} setState={setState} /><div className="grid gap-3 sm:grid-cols-2"><label className="rounded-[18px] border bg-white p-3 text-sm"><input checked={draft?.primaryEnabled ?? false} className="mr-2" onChange={(event) => setDraft({ primaryEnabled: event.target.checked })} type="checkbox" />Priorità 1: ruolo</label><label className="rounded-[18px] border bg-white p-3 text-sm"><input checked={draft?.secondaryEnabled ?? false} className="mr-2" onChange={(event) => setDraft({ secondaryEnabled: event.target.checked })} type="checkbox" />Priorità 2: consorzio e anagrafe</label></div><div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">{SLA_FIELDS.map(([label, field]) => <label className="space-y-1" key={field}><span className="text-xs font-medium text-gray-600">{label}</span><input className="form-control" min="1" onChange={(event) => setDraft({ [field]: Math.max(1, Number(event.target.value) || 1) })} type="number" value={(draft?.[field] as number) ?? 1} /></label>)}</div><div className="flex flex-wrap gap-3"><button className="btn-primary" disabled={state.busy || !canRun || !(draft?.primaryEnabled || draft?.secondaryEnabled)} onClick={() => void execute("save")} type="button">{state.status?.config.enabled ? "Metti su OFF" : "Metti su ON"}</button><button className="btn-secondary" disabled={state.busy} onClick={() => void execute("refresh")} type="button">Aggiorna sorgente</button><button className="btn-secondary" disabled={state.busy || !canRun} onClick={() => void execute("run")} type="button">Esegui adesso</button></div><p className="text-xs text-gray-500">Stato: {state.status?.config.enabled ? "ON" : "OFF"}{state.status?.config.last_source_refresh_at ? ` · sorgente ${formatDateTime(state.status.config.last_source_refresh_at)}` : ""}</p></>;
}

export function ContinuousCatastoSyncPanel() {
  const { state, setState, setDraft, execute } = useContinuousSyncState();
  return (
    <div className="space-y-4">
      <SyncNotice state={state} />
      <article className="overflow-hidden rounded-[28px] border border-[#d9dfd6] bg-white shadow-panel">
        <ElaborazionePanelHeader badge={<><RefreshIcon className="h-3.5 w-3.5" />Sync continua</>} title="Sincronizzazione catastale continua" description="Micro-batch perpetui: prima ruolo, poi patrimonio consortile e anagrafe. Il planner usa solo credenziali libere e nelle finestre operative." />
        <div className="space-y-6 p-6">
          <div className="grid gap-4 lg:grid-cols-[1.2fr,1fr]">
            <div className="space-y-4 rounded-[24px] border border-gray-100 bg-gray-50 p-4">
              <SyncConfiguration execute={execute} setDraft={setDraft} setState={setState} state={state} />
            </div>
            <ScopeCoverage status={state.status} />
          </div>
          <RunningBatch status={state.status} />
          <div className="grid gap-4 xl:grid-cols-2"><div className="rounded-[24px] border border-gray-100 p-4"><p className="text-sm font-semibold">Errori e retry</p><SyncItemList errorList items={state.status?.perpetual_error_items ?? []} /></div><div className="rounded-[24px] border border-gray-100 p-4"><p className="text-sm font-semibold">Coda recente</p><SyncItemList items={state.status?.perpetual_recent_items ?? []} /></div></div>
        </div>
      </article>
    </div>
  );
}
