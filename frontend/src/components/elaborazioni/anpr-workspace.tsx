"use client";

import { Fragment, useCallback, useEffect, useState } from "react";

import { ProtectedPage } from "@/components/app/protected-page";
import { ElaborazioneHero, ElaborazioneNoticeCard, ElaborazionePanelHeader } from "@/components/elaborazioni/module-chrome";
import { ModuleWorkspaceKpiRow, ModuleWorkspaceKpiTile } from "@/components/layout/module-workspace-hero";
import { EmptyState } from "@/components/ui/empty-state";
import { ChevronRightIcon, RefreshIcon, SearchIcon } from "@/components/ui/icons";
import { getElaborazioneAnprSummary } from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import { formatDateTime } from "@/lib/presentation";
import type { ElaborazioneAnprSummary } from "@/types/api";

function formatDateValue(value: string | null): string {
  if (!value) return "—";
  return value.slice(0, 10);
}

function formatRunRecordEsito(value: string): string {
  if (value === "alive") return "Vivo";
  if (value === "deceased") return "Deceduto";
  if (value === "not_found") return "Non trovato";
  if (value === "cancelled") return "Cancellato";
  if (value === "error") return "Errore";
  if (value === "anpr_id_found") return "idANPR trovato";
  return value;
}

export function ElaborazioniAnprWorkspace({ embedded = false }: { embedded?: boolean }) {
  const [summary, setSummary] = useState<ElaborazioneAnprSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [expandedRuns, setExpandedRuns] = useState<Record<string, boolean>>({});

  const loadSummary = useCallback(async () => {
    const token = getStoredAccessToken();
    if (!token) return;

    try {
      const response = await getElaborazioneAnprSummary(token);
      setSummary(response);
      setError(null);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Errore caricamento monitor ANPR");
    }
  }, []);

  useEffect(() => {
    void loadSummary();
  }, [loadSummary]);

  const content = (
    <>
      <ElaborazioneHero
        compact={embedded}
        badge={
          <>
            <RefreshIcon className="h-3.5 w-3.5" />
            ANPR batch a ruolo
          </>
        }
        title="Monitor operativo delle verifiche ANPR schedulate."
        description="Qui restano visibili consumo giornaliero chiamate, ultimo anno ruolo selezionato e storico sintetico dei batch eseguiti."
        actions={
          error ? (
            <ElaborazioneNoticeCard title="Errore monitor" description={error} tone="danger" compact={embedded} />
          ) : (
            <ElaborazioneNoticeCard
              title="Finestra controllata"
              description="Il job lavora solo nella finestra oraria consentita e non supera mai il cap giornaliero effettivo."
              compact={embedded}
            />
          )
        }
      >
        <ModuleWorkspaceKpiRow compact={embedded}>
          <ModuleWorkspaceKpiTile
            compact={embedded}
            label="Chiamate oggi"
            variant={summary && summary.calls_today >= summary.effective_daily_limit ? "amber" : "default"}
            value={summary?.calls_today ?? 0}
            hint={`cap ${summary?.effective_daily_limit ?? 0}`}
          />
          <ModuleWorkspaceKpiTile
            compact={embedded}
            label="Limite config"
            value={summary?.configured_daily_limit ?? 0}
            hint={`hard ${summary?.hard_daily_limit ?? 0}`}
          />
          <ModuleWorkspaceKpiTile
            compact={embedded}
            label="Batch size"
            value={summary?.batch_size ?? 0}
            hint={`ruolo ${summary?.ruolo_year ?? "auto"}`}
          />
          <ModuleWorkspaceKpiTile
            compact={embedded}
            label="Operazioni totali"
            value={summary?.total_calls_used ?? 0}
            hint={`${summary?.total_subjects_processed ?? 0} utenze processate`}
          />
          <ModuleWorkspaceKpiTile
            compact={embedded}
            label="Utenze selezionate"
            value={summary?.total_subjects_selected ?? 0}
            hint="totale storico job"
          />
          <ModuleWorkspaceKpiTile
            compact={embedded}
            label="Deceduti trovati"
            variant={(summary?.total_deceased_found ?? 0) > 0 ? "amber" : "default"}
            value={summary?.total_deceased_found ?? 0}
            hint="totale verifiche ANPR"
          />
          <ModuleWorkspaceKpiTile
            compact={embedded}
            label="Errori totali"
            variant={(summary?.total_errors ?? 0) > 0 ? "amber" : "default"}
            value={summary?.total_errors ?? 0}
            hint="storico operazioni"
          />
          <ModuleWorkspaceKpiTile
            compact={embedded}
            label="Run registrati"
            value={summary?.total_runs ?? 0}
            hint={summary?.recent_runs[0] ? summary.recent_runs[0].status : "nessuno"}
          />
          <ModuleWorkspaceKpiTile
            compact={embedded}
            label="Da verificare"
            variant={(summary?.total_error_subjects ?? 0) > 0 ? "amber" : "default"}
            value={summary?.total_error_subjects ?? 0}
            hint="utenze in errore aperte"
          />
        </ModuleWorkspaceKpiRow>
      </ElaborazioneHero>

      <article className="overflow-hidden rounded-[28px] border border-[#d9dfd6] bg-white shadow-panel">
        <ElaborazionePanelHeader
          badge={
            <>
              <SearchIcon className="h-3.5 w-3.5" />
              Storico run
            </>
          }
          title="Ultime esecuzioni ANPR"
          description="Ogni riga rappresenta un batch schedulato con budget prima/dopo, soggetti processati ed esito sintetico."
        />
        <div className="p-6">
          {!summary?.recent_runs.length ? (
            <EmptyState icon={SearchIcon} title="Nessun run disponibile" description="Il monitor si popolerà appena il job ANPR inizierà a registrare esecuzioni." />
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-100 text-sm">
                <thead>
                  <tr className="text-left text-[11px] uppercase tracking-[0.18em] text-gray-400">
                    <th className="w-12 px-3 py-3 font-semibold">Dettaglio</th>
                    <th className="px-3 py-3 font-semibold">Avvio</th>
                    <th className="px-3 py-3 font-semibold">Stato</th>
                    <th className="px-3 py-3 font-semibold">Ruolo</th>
                    <th className="px-3 py-3 font-semibold">Chiamate</th>
                    <th className="px-3 py-3 font-semibold">Soggetti</th>
                    <th className="px-3 py-3 font-semibold">Deceduti</th>
                    <th className="px-3 py-3 font-semibold">Errori</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {summary.recent_runs.map((run) => {
                    const isExpanded = Boolean(expandedRuns[run.id]);
                    return (
                      <Fragment key={run.id}>
                        <tr key={run.id} className="text-gray-700">
                          <td className="px-3 py-3">
                            <button
                              type="button"
                              className="inline-flex h-8 w-8 items-center justify-center rounded-full border border-[#d9dfd6] bg-[#f7faf7] text-gray-600 transition hover:border-[#1D4E35] hover:text-[#1D4E35]"
                              onClick={() => setExpandedRuns((current) => ({ ...current, [run.id]: !current[run.id] }))}
                              aria-label={isExpanded ? "Chiudi dettaglio batch ANPR" : "Apri dettaglio batch ANPR"}
                            >
                              <ChevronRightIcon className={["h-4 w-4 transition-transform", isExpanded ? "rotate-90" : ""].join(" ")} />
                            </button>
                          </td>
                          <td className="px-3 py-3">{formatDateTime(run.started_at)}</td>
                          <td className="px-3 py-3">
                            <span className="rounded-full bg-gray-100 px-2 py-1 text-[11px] font-semibold text-gray-700">{run.status}</span>
                          </td>
                          <td className="px-3 py-3">{run.ruolo_year}</td>
                          <td className="px-3 py-3">{run.daily_calls_before} → {run.daily_calls_after} ({run.calls_used})</td>
                          <td className="px-3 py-3">{run.subjects_processed}/{run.subjects_selected}</td>
                          <td className="px-3 py-3">{run.deceased_found}</td>
                          <td className="px-3 py-3">{run.errors}</td>
                        </tr>
                        {isExpanded ? (
                          <tr className="bg-[#fafcf9]">
                            <td className="px-3 py-4" colSpan={8}>
                              {!run.records.length ? (
                                <div className="rounded-2xl border border-dashed border-[#d9dfd6] bg-white px-4 py-3 text-sm text-gray-500">
                                  Nessun record elaborato registrato per questo batch.
                                </div>
                              ) : (
                                <div className="overflow-x-auto rounded-2xl border border-[#e3e9e0] bg-white">
                                  <table className="min-w-full divide-y divide-gray-100 text-sm">
                                    <thead>
                                      <tr className="text-left text-[11px] uppercase tracking-[0.18em] text-gray-400">
                                        <th className="px-3 py-3 font-semibold">Soggetto</th>
                                        <th className="px-3 py-3 font-semibold">CF</th>
                                        <th className="px-3 py-3 font-semibold">Ultimo evento</th>
                                        <th className="px-3 py-3 font-semibold">Esito</th>
                                        <th className="px-3 py-3 font-semibold">Chiamate</th>
                                        <th className="px-3 py-3 font-semibold">Tipi</th>
                                        <th className="px-3 py-3 font-semibold">Errore</th>
                                      </tr>
                                    </thead>
                                    <tbody className="divide-y divide-gray-100">
                                      {run.records.map((record) => (
                                        <tr key={record.id} className="align-top text-gray-700">
                                          <td className="px-3 py-3">
                                            <div className="font-medium text-gray-900">{record.display_name}</div>
                                            <div className="mt-1 text-xs text-gray-500">{formatDateValue(record.data_nascita)}</div>
                                          </td>
                                          <td className="px-3 py-3 font-mono text-xs">{record.codice_fiscale}</td>
                                          <td className="px-3 py-3">{formatDateTime(record.last_event_at)}</td>
                                          <td className="px-3 py-3">
                                            <span
                                              className={[
                                                "rounded-full px-2 py-1 text-[11px] font-semibold",
                                                record.final_esito === "error" ? "bg-red-50 text-red-700" : "bg-gray-100 text-gray-700",
                                              ].join(" ")}
                                            >
                                              {formatRunRecordEsito(record.final_esito)}
                                            </span>
                                          </td>
                                          <td className="px-3 py-3">{record.calls_made}</td>
                                          <td className="px-3 py-3 text-xs text-gray-500">{record.call_types.join(", ")}</td>
                                          <td className="max-w-md px-3 py-3 text-xs leading-5 text-gray-600">
                                            {record.error_detail || "—"}
                                          </td>
                                        </tr>
                                      ))}
                                    </tbody>
                                  </table>
                                </div>
                              )}
                            </td>
                          </tr>
                        ) : null}
                      </Fragment>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </article>

      <article className="overflow-hidden rounded-[28px] border border-[#d9dfd6] bg-white shadow-panel">
        <ElaborazionePanelHeader
          badge={
            <>
              <SearchIcon className="h-3.5 w-3.5" />
              Verifica manuale
            </>
          }
          title="Utenze ANPR in errore"
          description="Soggetti del ruolo corrente ancora in stato errore, con ultimo dettaglio disponibile e accesso diretto alla scheda utente."
        />
        <div className="p-6">
          {!summary?.error_subjects.length ? (
            <EmptyState
              icon={SearchIcon}
              title="Nessuna utenza in errore"
              description="Quando il batch incontra errori sui soggetti a ruolo, la lista apparirà qui per la verifica manuale."
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-100 text-sm">
                <thead>
                  <tr className="text-left text-[11px] uppercase tracking-[0.18em] text-gray-400">
                    <th className="px-3 py-3 font-semibold">Soggetto</th>
                    <th className="px-3 py-3 font-semibold">CF</th>
                    <th className="px-3 py-3 font-semibold">Nascita</th>
                    <th className="px-3 py-3 font-semibold">Ultimo check</th>
                    <th className="px-3 py-3 font-semibold">Capacitas</th>
                    <th className="px-3 py-3 font-semibold">Dettaglio errore</th>
                    <th className="px-3 py-3 font-semibold">Azione</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {summary.error_subjects.map((item) => (
                    <tr key={item.subject_id} className="align-top text-gray-700">
                      <td className="px-3 py-3">
                        <div className="font-medium text-gray-900">{item.display_name}</div>
                        <div className="mt-1 text-xs text-gray-500">{item.stato_anpr}</div>
                      </td>
                      <td className="px-3 py-3 font-mono text-xs">{item.codice_fiscale}</td>
                      <td className="px-3 py-3">{formatDateValue(item.data_nascita)}</td>
                      <td className="px-3 py-3">
                        <div>{formatDateTime(item.last_anpr_check_at)}</div>
                        <div className="mt-1 text-xs text-gray-500">{formatDateTime(item.latest_error_at)}</div>
                      </td>
                      <td className="px-3 py-3">
                        <span
                          className={[
                            "rounded-full px-2 py-1 text-[11px] font-semibold",
                            item.capacitas_deceduto ? "bg-amber-50 text-amber-700" : "bg-gray-100 text-gray-700",
                          ].join(" ")}
                        >
                          {item.capacitas_deceduto ? "deceduto" : "non marcato"}
                        </span>
                      </td>
                      <td className="max-w-md px-3 py-3 text-xs leading-5 text-gray-600">
                        {item.latest_error_detail || "Errore ANPR senza dettaglio strutturato."}
                      </td>
                      <td className="px-3 py-3">
                        <a
                          className="inline-flex rounded-full border border-[#cfe0d5] bg-[#f3f8f4] px-3 py-1.5 text-xs font-semibold text-[#1D4E35] transition hover:border-[#1D4E35] hover:bg-[#e8f2eb]"
                          href={`/utenze/${item.subject_id}`}
                          target={embedded ? "_blank" : undefined}
                          rel={embedded ? "noreferrer" : undefined}
                        >
                          Apri scheda
                        </a>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </article>
    </>
  );

  if (embedded) {
    return <div className="space-y-6">{content}</div>;
  }

  return (
    <ProtectedPage
      title="GAIA Elaborazioni · ANPR"
      description="Monitor dedicato ai batch ANPR schedulati sui soggetti a ruolo."
      breadcrumb="Elaborazioni / ANPR"
      requiredModule="catasto"
    >
      <div className="space-y-6">{content}</div>
    </ProtectedPage>
  );
}
