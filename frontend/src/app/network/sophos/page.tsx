"use client";

import { useEffect, useMemo, useState } from "react";

import { NetworkModulePage } from "@/components/network/network-module-page";
import { getNetworkSophosConfig, updateNetworkSophosConfig } from "@/lib/api";
import { formatDateTime } from "@/lib/presentation";
import type { CurrentUser, NetworkSophosConfig, NetworkSophosConfigUpdateInput } from "@/types/api";

type SophosFormState = {
  syslog_enabled: boolean;
  snmp_enabled: boolean;
  operation_window_enabled: boolean;
  operation_start_hour: number;
  operation_end_hour: number;
  operation_timezone: string;
};

const HOUR_OPTIONS = Array.from({ length: 24 }, (_, hour) => hour);

function buildFormState(config: NetworkSophosConfig): SophosFormState {
  return {
    syslog_enabled: config.syslog_enabled,
    snmp_enabled: config.snmp_enabled,
    operation_window_enabled: config.operation_window_enabled,
    operation_start_hour: config.operation_start_hour,
    operation_end_hour: config.operation_end_hour,
    operation_timezone: config.operation_timezone,
  };
}

function isAdminRole(role: string): boolean {
  return role === "admin" || role === "super_admin";
}

function formatHour(value: number): string {
  return `${String(value).padStart(2, "0")}:00`;
}

function SophosSettingsContent({ token, currentUser }: { token: string; currentUser: CurrentUser }) {
  const [config, setConfig] = useState<NetworkSophosConfig | null>(null);
  const [formState, setFormState] = useState<SophosFormState | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);
  const isAdmin = isAdminRole(currentUser.role);

  useEffect(() => {
    async function loadConfig() {
      try {
        const nextConfig = await getNetworkSophosConfig(token);
        setConfig(nextConfig);
        setFormState(buildFormState(nextConfig));
        setError(null);
      } catch (currentError) {
        setError(currentError instanceof Error ? currentError.message : "Impossibile caricare la configurazione Sophos");
      } finally {
        setIsLoading(false);
      }
    }

    void loadConfig();
  }, [token]);

  const isDirty = useMemo(() => {
    if (!config || !formState) {
      return false;
    }
    return (
      config.syslog_enabled !== formState.syslog_enabled ||
      config.snmp_enabled !== formState.snmp_enabled ||
      config.operation_window_enabled !== formState.operation_window_enabled ||
      config.operation_start_hour !== formState.operation_start_hour ||
      config.operation_end_hour !== formState.operation_end_hour ||
      config.operation_timezone !== formState.operation_timezone
    );
  }, [config, formState]);

  async function handleSave() {
    if (!formState || !isAdmin) {
      return;
    }
    setIsSaving(true);
    setError(null);
    setSaveMessage(null);
    try {
      const payload: NetworkSophosConfigUpdateInput = {
        syslog_enabled: formState.syslog_enabled,
        snmp_enabled: formState.snmp_enabled,
        operation_window_enabled: formState.operation_window_enabled,
        operation_start_hour: formState.operation_start_hour,
        operation_end_hour: formState.operation_end_hour,
        operation_timezone: formState.operation_timezone.trim(),
      };
      const nextConfig = await updateNetworkSophosConfig(token, payload);
      setConfig(nextConfig);
      setFormState(buildFormState(nextConfig));
      setSaveMessage("Configurazione Sophos aggiornata.");
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "Impossibile salvare la configurazione Sophos");
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <>
      {error ? (
        <article className="panel-card border border-red-100 bg-red-50/60">
          <p className="text-sm font-medium text-red-700">Errore configurazione</p>
          <p className="mt-1 text-sm text-red-600">{error}</p>
        </article>
      ) : null}

      {saveMessage ? (
        <article className="panel-card border border-emerald-100 bg-emerald-50/70">
          <p className="text-sm font-medium text-emerald-800">{saveMessage}</p>
        </article>
      ) : null}

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1.15fr)_minmax(320px,0.85fr)]">
        <article className="panel-card">
          <div>
            <p className="section-title">Runtime Sophos</p>
            <p className="section-copy mt-1">
              Abilita o sospendi l&apos;ingestione `syslog` e il polling `SNMP`. Fuori finestra, i messaggi syslog vengono ignorati e SNMP non esegue polling.
            </p>
          </div>

          <div className="mt-5 grid gap-4 md:grid-cols-2">
            <label className="flex items-center gap-3 rounded-xl border border-[#d8e2d8] bg-[#f8fbf7] px-4 py-3 text-sm font-medium text-gray-700">
              <input
                type="checkbox"
                checked={formState?.syslog_enabled ?? false}
                onChange={(event) => setFormState((current) => (current ? { ...current, syslog_enabled: event.target.checked } : current))}
                disabled={isLoading || isSaving || !isAdmin}
              />
              Syslog abilitato
            </label>

            <label className="flex items-center gap-3 rounded-xl border border-[#d8e2d8] bg-[#f8fbf7] px-4 py-3 text-sm font-medium text-gray-700">
              <input
                type="checkbox"
                checked={formState?.snmp_enabled ?? false}
                onChange={(event) => setFormState((current) => (current ? { ...current, snmp_enabled: event.target.checked } : current))}
                disabled={isLoading || isSaving || !isAdmin}
              />
              SNMP abilitato
            </label>

            <label className="flex items-center gap-3 rounded-xl border border-[#d8e2d8] bg-[#f8fbf7] px-4 py-3 text-sm font-medium text-gray-700 md:col-span-2">
              <input
                type="checkbox"
                checked={formState?.operation_window_enabled ?? false}
                onChange={(event) =>
                  setFormState((current) => (current ? { ...current, operation_window_enabled: event.target.checked } : current))
                }
                disabled={isLoading || isSaving || !isAdmin}
              />
              Elabora solo nella finestra oraria configurata
            </label>

            <label className="block text-sm font-medium text-gray-700">
              Ora inizio
              <select
                className="form-control mt-1"
                value={formState?.operation_start_hour ?? 19}
                onChange={(event) =>
                  setFormState((current) =>
                    current ? { ...current, operation_start_hour: Number(event.target.value) } : current,
                  )
                }
                disabled={isLoading || isSaving || !isAdmin}
              >
                {HOUR_OPTIONS.map((hour) => (
                  <option key={hour} value={hour}>
                    {formatHour(hour)}
                  </option>
                ))}
              </select>
            </label>

            <label className="block text-sm font-medium text-gray-700">
              Ora fine
              <select
                className="form-control mt-1"
                value={formState?.operation_end_hour ?? 4}
                onChange={(event) =>
                  setFormState((current) =>
                    current ? { ...current, operation_end_hour: Number(event.target.value) } : current,
                  )
                }
                disabled={isLoading || isSaving || !isAdmin}
              >
                {HOUR_OPTIONS.map((hour) => (
                  <option key={hour} value={hour}>
                    {formatHour(hour)}
                  </option>
                ))}
              </select>
            </label>

            <label className="block text-sm font-medium text-gray-700 md:col-span-2">
              Timezone operativa
              <input
                className="form-control mt-1"
                type="text"
                value={formState?.operation_timezone ?? "Europe/Rome"}
                onChange={(event) =>
                  setFormState((current) =>
                    current ? { ...current, operation_timezone: event.target.value } : current,
                  )
                }
                disabled={isLoading || isSaving || !isAdmin}
              />
            </label>
          </div>

          <div className="mt-5 flex flex-wrap items-center gap-3">
            <button className="btn-primary" type="button" onClick={() => void handleSave()} disabled={!isAdmin || !isDirty || isSaving || isLoading}>
              {isSaving ? "Salvataggio..." : "Salva configurazione"}
            </button>
            {!isAdmin ? <p className="text-sm text-gray-500">Solo admin e super admin possono modificare questa configurazione.</p> : null}
          </div>
        </article>

        <article className="panel-card">
          <p className="section-title">Stato effettivo</p>
          <div className="mt-4 space-y-3">
            <div className="rounded-2xl border border-[#d8e2d8] bg-[#f8fbf7] p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#5E7A64]">Finestra attuale</p>
              <p className="mt-2 text-lg font-semibold text-[#163726]">
                {config?.operation_window_enabled
                  ? `${formatHour(config.operation_start_hour)}-${formatHour(config.operation_end_hour)} ${config.operation_timezone}`
                  : "Sempre attiva"}
              </p>
              <p className="mt-1 text-sm text-gray-600">
                {config?.operation_window_enabled
                  ? config?.is_within_window
                    ? "Siamo dentro la finestra: i servizi abilitati possono elaborare."
                    : "Siamo fuori finestra: syslog viene ignorato e SNMP non polla."
                  : "La finestra oraria e disabilitata: contano solo i toggle dei servizi."}
              </p>
            </div>

            <div className="grid gap-3 md:grid-cols-2">
              <div className="rounded-2xl border border-[#d8e2d8] bg-white p-4">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#5E7A64]">Syslog</p>
                <p className={`mt-2 text-lg font-semibold ${config?.syslog_effective_enabled ? "text-emerald-700" : "text-amber-700"}`}>
                  {config?.syslog_effective_enabled ? "Attivo" : "Sospeso"}
                </p>
                <p className="mt-1 text-sm text-gray-600">
                  {config?.syslog_enabled ? "Toggle acceso." : "Toggle spento."}
                </p>
              </div>

              <div className="rounded-2xl border border-[#d8e2d8] bg-white p-4">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#5E7A64]">SNMP</p>
                <p className={`mt-2 text-lg font-semibold ${config?.snmp_effective_enabled ? "text-emerald-700" : "text-amber-700"}`}>
                  {config?.snmp_effective_enabled ? "Attivo" : "Sospeso"}
                </p>
                <p className="mt-1 text-sm text-gray-600">
                  {config?.snmp_enabled ? "Toggle acceso." : "Toggle spento."}
                </p>
              </div>
            </div>

            <div className="rounded-2xl border border-dashed border-[#c9d7cc] bg-[#fcfdfb] p-4 text-sm text-gray-600">
              <p>
                Ultimo aggiornamento: {config?.updated_at ? formatDateTime(config.updated_at) : "configurazione iniziale non ancora modificata"}.
              </p>
              <p className="mt-2">
                Nota: questa configurazione governa l&apos;ingestione in tempo reale. Non effettua il recupero retroattivo dei log persi fuori finestra.
              </p>
            </div>
          </div>
        </article>
      </div>
    </>
  );
}

export default function NetworkSophosSettingsPage() {
  return (
    <NetworkModulePage
      title="Runtime Sophos"
      description="Controllo operativo di ingestione syslog e polling SNMP con finestra oraria persistita."
      breadcrumb="GAIA / Rete / Sophos"
    >
      {({ token, currentUser }) => <SophosSettingsContent token={token} currentUser={currentUser} />}
    </NetworkModulePage>
  );
}
