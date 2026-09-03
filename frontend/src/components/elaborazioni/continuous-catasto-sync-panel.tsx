"use client";

import { useEffect, useState } from "react";

import { AutoSyncActivityDashboard } from "@/components/elaborazioni/autosync-activity-dashboard";
import { AutoSyncErrorArtifactList } from "@/components/elaborazioni/autosync-error-artifacts";
import { ElaborazioneNoticeCard, ElaborazionePanelHeader } from "@/components/elaborazioni/module-chrome";
import { ElaborazioneStatusBadge } from "@/components/elaborazioni/status-badge";
import { RefreshIcon } from "@/components/ui/icons";
import { useAutoSyncCampaignItems } from "@/components/elaborazioni/use-autosync-campaign-items";
import {
  defaultSisterSchedule,
  SisterAvailabilityScheduleEditor,
} from "@/components/elaborazioni/sister-availability-schedule";
import {
  getElaborazioneCredentials,
  getElaborazioneRuoloAutoSyncStatus,
  refreshElaborazioneRuoloAutoSyncSource,

  runElaborazioneRuoloAutoSyncNow,
  updateElaborazioneRuoloAutoSyncConfig,
} from "@/lib/api";
import {
  retryElaborazioneRuoloAutoSyncCampaignFailures,
  type RoleCampaignScope,
} from "@/lib/autosync-campaign-api";
import { getStoredAccessToken } from "@/lib/auth";
import { formatDateTime } from "@/lib/presentation";
import type {
  CatastoPerpetualSyncItem,
  ElaborazioneCredential,
  ElaborazioneRuoloAutoSyncStatus,
} from "@/types/api";
import type { AutoSyncCredentialProfile } from "@/types/elaborazioni-continuous-sync";

type SyncDraft = {
  credentialProfiles: Record<string, AutoSyncCredentialProfile>;
  primaryEnabled: boolean;
  secondaryEnabled: boolean;
  roleParcelHours: number;
  roleSubjectHours: number;
  consortiumParcelHours: number;
  registrySubjectHours: number;
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

function selectedCredentialIds(draft: SyncDraft | null): string[] {
  if (!draft) return [];
  return Object.entries(draft.credentialProfiles)
    .filter(([, profile]) => profile.enabled)
    .map(([credentialId]) => credentialId);
}

function draftFromStatus(
  status: ElaborazioneRuoloAutoSyncStatus,
  credentials: ElaborazioneCredential[],
): SyncDraft {
  const config = status.config;
  const selected = new Set(config.credential_ids ?? (config.credential_id ? [config.credential_id] : []));
  const configuredProfiles = config.credential_profiles ?? {};
  const credentialProfiles = Object.fromEntries(credentials.filter((credential) => credential.active).map((credential) => [
    credential.id,
    configuredProfiles[credential.id] ?? {
      enabled: selected.has(credential.id),
      schedule_enabled: false,
      availability_schedule: defaultSisterSchedule(),
    },
  ]));
  return {
    credentialProfiles,
    primaryEnabled: config.primary_enabled,
    secondaryEnabled: config.secondary_enabled,
    roleParcelHours: config.role_parcel_refresh_hours,
    roleSubjectHours: config.role_subject_refresh_hours,
    consortiumParcelHours: config.consortium_parcel_refresh_hours,
    registrySubjectHours: config.registry_subject_refresh_hours,
  };
}

function itemLabel(item: CatastoPerpetualSyncItem): string {
  if (item.search_mode === "soggetto") {
    return `${item.intestazione ?? item.subject_kind ?? "Soggetto"} · ${item.subject_identifier ?? "identificativo mancante"}`;
  }
  return `${item.comune ?? "Comune non risolto"} · Fg. ${item.foglio ?? "-"} · Part. ${item.particella ?? "-"}`;
}

async function retryCampaignAction(
  scope: RoleCampaignScope,
  setState: React.Dispatch<React.SetStateAction<SyncState>>,
  reload: () => Promise<void>,
): Promise<void> {
  const token = getStoredAccessToken();
  if (!token) return;
  setState((current) => ({ ...current, busy: true }));
  try {
    const result = await retryElaborazioneRuoloAutoSyncCampaignFailures(token, scope);
    await reload();
    setState((current) => ({ ...current, info: result.message, error: null }));
  } catch (error) {
    setState((current) => ({ ...current, error: error instanceof Error ? error.message : "Errore retry AutoSync" }));
  } finally {
    setState((current) => ({ ...current, busy: false }));
  }
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
      draft: current.draft ?? draftFromStatus(status, credentialStatus.credentials),
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
        await updateElaborazioneRuoloAutoSyncConfig(token, { enabled, credential_id: null, credential_profiles: draft.credentialProfiles, primary_enabled: draft.primaryEnabled, secondary_enabled: draft.secondaryEnabled, role_parcel_refresh_hours: draft.roleParcelHours, role_subject_refresh_hours: draft.roleSubjectHours, consortium_parcel_refresh_hours: draft.consortiumParcelHours, registry_subject_refresh_hours: draft.registrySubjectHours });
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

  const setDraft = (patch: Partial<SyncDraft>) => setState((current) => ({
    ...current,
    draft: { ...current.draft!, ...patch },
  }));
  return {
    state,
    setState,
    setDraft,
    execute,
    retryCampaign: (scope: RoleCampaignScope) => retryCampaignAction(scope, setState, reload),
  };
}

function CredentialPool({ state, setState }: { state: SyncState; setState: React.Dispatch<React.SetStateAction<SyncState>> }) {
  const profiles = state.draft!.credentialProfiles;
  const selectedIds = selectedCredentialIds(state.draft);
  const availableIds = state.status!.available_credential_ids;
  const activeCredentials = state.credentials.filter((credential) => credential.active);
  const updateProfiles = (next: Record<string, AutoSyncCredentialProfile>) => setState((current) => ({
    ...current, draft: { ...current.draft!, credentialProfiles: next },
  }));
  const setAll = (enabled: boolean) => updateProfiles(Object.fromEntries(activeCredentials.map((credential) => {
    return [credential.id, { ...profiles[credential.id]!, enabled }];
  })));
  return (
    <fieldset className="space-y-3" disabled={state.busy || !state.draft}>
      <legend className="sr-only">Pool credenziali SISTER</legend>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className="label-caption">Pool credenziali SISTER</p>
          <p className="mt-1 text-xs text-gray-500">{selectedIds.length} di {activeCredentials.length} selezionate</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button className="btn-secondary px-3 py-2 text-xs" disabled={state.busy || selectedIds.length === activeCredentials.length} onClick={() => setAll(true)} type="button">Attiva tutte</button>
          <button className="btn-secondary px-3 py-2 text-xs" disabled={state.busy || selectedIds.length === 0} onClick={() => setAll(false)} type="button">Disattiva tutte</button>
        </div>
      </div>
      <div className="grid gap-2 sm:grid-cols-2">
        {activeCredentials.map((credential) => {
          const profile = profiles[credential.id]!;
          const selected = profile.enabled;
          const available = availableIds.includes(credential.id);
          const updateProfile = (patch: Partial<AutoSyncCredentialProfile>) => updateProfiles({
            ...profiles, [credential.id]: { ...profile, ...patch },
          });
          return (
            <div className={`rounded-[18px] border p-3 transition-colors ${selected ? "border-[#80a98b] bg-white ring-1 ring-[#d7e6da]" : "border-gray-200 bg-gray-50"}`} key={credential.id}>
              <label className="flex min-h-10 cursor-pointer items-center gap-3">
                <input checked={selected} className="h-5 w-5 shrink-0 accent-[#477a55]" disabled={state.busy} onChange={(event) => updateProfile({ enabled: event.target.checked })} type="checkbox" />
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-sm font-semibold text-gray-900">{credential.label}</span>
                  <span className="mt-0.5 block truncate text-xs text-gray-500">{credential.sister_username}</span>
                </span>
                <span className={`shrink-0 rounded-full px-2 py-1 text-[11px] font-medium ${selected ? "bg-emerald-100 text-emerald-800" : "bg-gray-100 text-gray-600"}`}>AutoSync {selected ? "ON" : "OFF"}</span>
                {selected ? <span className={`shrink-0 rounded-full px-2 py-1 text-[11px] font-medium ${available ? "bg-emerald-100 text-emerald-800" : "bg-amber-100 text-amber-800"}`}>{available ? "Disponibile" : "Fuori fascia / occupata"}</span> : null}
              </label>
              {selected ? <div className="mt-3 border-t border-gray-100 pt-3"><SisterAvailabilityScheduleEditor enabled={profile.schedule_enabled} onEnabledChange={(schedule_enabled) => updateProfile({ schedule_enabled })} onScheduleChange={(availability_schedule) => updateProfile({ availability_schedule })} schedule={profile.availability_schedule ?? defaultSisterSchedule()} /></div> : null}
            </div>
          );
        })}
      </div>
    </fieldset>
  );
}

const ROLE_CAMPAIGNS: Array<[string, RoleCampaignScope]> = [
  ["Particelle a ruolo", "ruolo_particella"],
  ["Anagrafiche a ruolo", "ruolo_soggetto"],
];

function CampaignLists({ state, pages, loadMore, retryCampaign }: {
  state: SyncState;
  pages: ReturnType<typeof useAutoSyncCampaignItems>["pages"];
  loadMore: (scope: RoleCampaignScope) => Promise<void>;
  retryCampaign: (scope: RoleCampaignScope) => Promise<void>;
}) {
  return <section aria-labelledby="autosync-campaigns-title" className="space-y-3"><div><h2 className="text-lg font-semibold text-gray-950" id="autosync-campaigns-title">Campagna AutoSync a ruolo</h2><p className="mt-1 text-sm text-gray-500">Un&apos;unica campagna permanente in due fasi: prima vengono completate le particelle, poi le anagrafiche deduplicate per CF/P.IVA.</p></div><div className="grid grid-cols-2 gap-2 sm:gap-3" data-testid="autosync-scope-coverage">{ROLE_CAMPAIGNS.map(([label, scope]) => {
    const counts = state.status?.scope_counts[scope] ?? {};
    const total = Object.values(counts).reduce((sum, value) => sum + value, 0);
    const failed = counts.failed ?? 0;
    const completed = counts.completed ?? 0;
    const progress = Math.min(100, Math.round((completed / Math.max(total, 1)) * 100));
    const page = pages[scope];
    return <article className="rounded-[24px] border border-gray-100 bg-gray-50 p-4" data-testid={`autosync-campaign-${scope}`} key={scope}><div className="flex flex-wrap items-start justify-between gap-3"><div><h3 className="text-base font-semibold text-gray-950">{label}</h3><p className="mt-1 text-2xl font-semibold text-gray-900">{completed} <span className="text-sm font-normal text-gray-400">/ {total}</span></p></div><span className="rounded-full bg-white px-3 py-1 text-xs font-semibold text-gray-700">{progress}%</span></div><div className="mt-3 h-2 overflow-hidden rounded-full bg-gray-200"><div className="h-full rounded-full bg-[#477a55]" style={{ width: `${progress}%` }} /></div><p className="mt-2 text-xs text-gray-500">{counts.processing ?? 0} in corso · {(counts.pending ?? 0) + (counts.queued ?? 0)} in attesa · {failed} fallite</p>{failed > 0 ? <button className="btn-secondary mt-3 w-full justify-center sm:w-auto" disabled={state.busy} onClick={() => void retryCampaign(scope)} type="button">Riprova {failed} {failed === 1 ? "fallita" : "fallite"}</button> : null}<SyncItemList items={page.items} />{page.error ? <p className="mt-3 text-sm text-red-700">{page.error}</p> : null}{page.hasMore ? <button className="btn-secondary mt-3 w-full justify-center" disabled={page.loading} onClick={() => void loadMore(scope)} type="button">{page.loading ? "Caricamento…" : "Carica altri"}</button> : null}<p className="mt-2 text-xs text-gray-500">Mostrati {page.items.length} di {page.total}</p></article>;
  })}</div></section>;
}

function SyncItemList({ items }: { items: CatastoPerpetualSyncItem[] }) {
  if (!items.length) return <p className="text-sm text-gray-500">Nessun elemento da mostrare.</p>;
  return <div className="mt-3 space-y-3">{items.map((item) => <div className="rounded-[18px] border border-gray-100 bg-gray-50 px-4 py-3" key={item.id}><div className="flex items-start justify-between gap-3"><div><p className="text-sm font-medium text-gray-900">{itemLabel(item)}</p><p className="mt-1 text-xs text-gray-500">tentativi {item.attempt_count} · prossimo ciclo {formatDateTime(item.next_due_at)}</p>{item.last_error_message ? <p className="mt-1 text-sm text-red-700">{item.last_error_message}</p> : null}</div><span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-700">{item.status}</span></div></div>)}</div>;
}

function SyncNotice({ state }: { state: SyncState }) {
  if (state.error) return <ElaborazioneNoticeCard title="Errore sincronizzazione" description={state.error} tone="danger" />;
  if (state.info) return <ElaborazioneNoticeCard title="Sincronizzazione catastale" description={state.info} tone="success" />;
  return null;
}

function RunningBatch({ status }: { status: ElaborazioneRuoloAutoSyncStatus | null }) {
  const batch = status?.running_batch;
  if (!batch) return null;
  return <div className="rounded-[24px] border border-[#d9dfd6] bg-[#eef6f0] p-4"><div className="flex justify-between gap-3"><div><p className="text-sm font-semibold">{batch.name ?? "Elaborazione AutoSync attiva"}</p><p className="mt-1 text-sm text-gray-600">{batch.current_operation ?? "In lavorazione"}</p></div><ElaborazioneStatusBadge status={batch.status} /></div></div>;
}

function RefreshIntervalFields({ draft, disabled, setDraft }: {
  draft: SyncDraft;
  disabled: boolean;
  setDraft: (patch: Partial<SyncDraft>) => void;
}) {
  return <section className="space-y-3" aria-labelledby="refresh-intervals-title"><div><h3 className="text-sm font-semibold text-gray-900" id="refresh-intervals-title">Intervalli di aggiornamento</h3><p className="mt-1 text-xs text-gray-500">Questi valori indicano la frequenza del nuovo controllo, non il numero di particelle o soggetti.</p></div><div className="grid gap-3 sm:grid-cols-2">{REFRESH_FIELDS.map(([label, field]) => <div className="space-y-1 rounded-[18px] border border-gray-100 bg-white p-3" key={field}><label className="block text-xs font-medium text-gray-600" htmlFor={`refresh-${field}`}>{label}</label><input aria-describedby={`refresh-${field}-description`} className="form-control" disabled={disabled} id={`refresh-${field}`} min="1" onChange={(event) => setDraft({ [field]: Math.max(1, Number(event.target.value) || 1) })} type="number" value={draft[field] as number} /><span className="block text-xs text-gray-500" id={`refresh-${field}-description`}>{refreshIntervalDescription(draft[field] as number)}</span></div>)}</div></section>;
}

function SyncConfiguration({ state, setState, setDraft, execute }: {
  state: SyncState;
  setState: React.Dispatch<React.SetStateAction<SyncState>>;
  setDraft: (patch: Partial<SyncDraft>) => void;
  execute: (action: SyncAction) => Promise<void>;
}) {
  const draft = state.draft;
  const configurationInputsDisabled = state.busy || !draft;
  const canRun = selectedCredentialIds(draft).length > 0;
  const prioritiesDisabled = state.busy || !draft || !(draft.primaryEnabled || draft.secondaryEnabled);
  const enabled = state.status?.config.enabled ?? false;
  return <><div className="grid grid-cols-2 gap-2 sm:flex sm:flex-wrap sm:gap-3" data-testid="autosync-actions"><button className="btn-primary w-full justify-center sm:w-auto" disabled={prioritiesDisabled} onClick={() => void execute("toggle")} type="button">{enabled ? "Metti su OFF" : "Metti su ON"}</button>{enabled ? <button className="btn-secondary w-full justify-center sm:w-auto" disabled={state.busy} onClick={() => void execute("save")} type="button">Salva configurazione</button> : null}<button className="btn-secondary w-full justify-center sm:w-auto" disabled={state.busy} onClick={() => void execute("refresh")} type="button">Aggiorna sorgente</button><button className="btn-secondary w-full justify-center sm:w-auto" disabled={state.busy || !canRun} onClick={() => void execute("run")} type="button">Esegui adesso</button></div><p className="text-xs text-gray-500">Stato: {enabled ? "ON" : "OFF"}{state.status?.config.last_source_refresh_at ? ` · sorgente ${formatDateTime(state.status.config.last_source_refresh_at)}` : ""}</p>{enabled && draft ? <><CredentialPool state={state} setState={setState} /><div className="grid grid-cols-2 gap-2 sm:gap-3"><label className="rounded-[18px] border bg-white p-3 text-sm"><input checked={draft.primaryEnabled} className="mr-2" disabled={configurationInputsDisabled} onChange={(event) => setDraft({ primaryEnabled: event.target.checked })} type="checkbox" />Priorità 1: ruolo</label><label className="rounded-[18px] border bg-white p-3 text-sm"><input checked={draft.secondaryEnabled} className="mr-2" disabled={configurationInputsDisabled} onChange={(event) => setDraft({ secondaryEnabled: event.target.checked })} type="checkbox" />Priorità 2: consorzio e anagrafe</label></div><div className="rounded-[18px] border border-[#d9dfd6] bg-[#eef6f0] p-3 text-sm text-gray-700"><strong>Campagna AutoSync:</strong> prima completa la fase Particelle a ruolo, poi prosegue con Anagrafiche a ruolo. Lo stato viene ripreso dopo ogni pausa.</div><RefreshIntervalFields disabled={configurationInputsDisabled} draft={draft} setDraft={setDraft} /></> : <p className="rounded-[18px] border border-gray-200 bg-gray-50 p-4 text-sm text-gray-600">Attiva AutoSync per scegliere le credenziali e impostare gli orari dedicati.</p>}</>;
}

export function ContinuousCatastoSyncPanel() {
  const { state, setState, setDraft, execute, retryCampaign } = useContinuousSyncState();
  const campaigns = useAutoSyncCampaignItems();
  const retryAndRefresh = async (scope: RoleCampaignScope) => {
    await retryCampaign(scope);
    await campaigns.refresh(scope);
  };
  return (
    <div className="space-y-4">
      <SyncNotice state={state} />
      <article className="overflow-hidden rounded-[28px] border border-[#d9dfd6] bg-white shadow-panel">
        <ElaborazionePanelHeader badge={<><RefreshIcon className="h-3.5 w-3.5" />Sync continua</>} title="Sincronizzazione catastale continua" description="Un'unica campagna permanente in due fasi: prima tutte le particelle a ruolo, poi le anagrafiche a ruolo." />
        <div className="space-y-5 p-4 md:space-y-6 md:p-6" data-testid="autosync-configuration-content">
          <section aria-labelledby="autosync-configuration-title" className="space-y-4">
            <div><h2 className="text-lg font-semibold text-gray-950" id="autosync-configuration-title">Configurazione AutoSync</h2><p className="mt-1 text-sm text-gray-500">Credenziali e intervalli di aggiornamento della campagna a ruolo.</p></div>
          <div className="grid gap-4 lg:grid-cols-[1.2fr,1fr]">
            <div className="space-y-4 rounded-[24px] border border-gray-100 bg-gray-50 p-4">
              <SyncConfiguration execute={execute} setDraft={setDraft} setState={setState} state={state} />
            </div>
            <div className="rounded-[24px] border border-gray-100 bg-gray-50 p-4"><p className="text-sm font-semibold text-gray-900">Ordine di esecuzione</p><ol className="mt-3 space-y-2 text-sm text-gray-600"><li><strong>1.</strong> Particelle a ruolo</li><li><strong>2.</strong> Anagrafiche a ruolo</li></ol><p className="mt-3 text-xs text-gray-500">Gli elementi completati tornano in coda soltanto se risultano nuovi o modificati.</p></div>
          </div>
          </section>
          <RunningBatch status={state.status} />
          <div className="rounded-[24px] border border-gray-100 p-4"><p className="text-sm font-semibold">Errori recenti</p><AutoSyncErrorArtifactList items={state.status?.perpetual_error_items ?? []} /></div>
        </div>
      </article>
      <AutoSyncActivityDashboard credentials={state.credentials} status={state.status} />
      <CampaignLists loadMore={campaigns.loadMore} pages={campaigns.pages} retryCampaign={retryAndRefresh} state={state} />
    </div>
  );
}
