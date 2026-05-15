"use client";

import { useCallback, useEffect, useState } from "react";

import { ProtectedPage } from "@/components/app/protected-page";
import { ElaborazioneHero, ElaborazioneNoticeCard, ElaborazionePanelHeader } from "@/components/elaborazioni/module-chrome";
import { ModuleWorkspaceKpiRow, ModuleWorkspaceKpiTile } from "@/components/layout/module-workspace-hero";
import { EmptyState } from "@/components/ui/empty-state";
import { RefreshIcon, SearchIcon } from "@/components/ui/icons";
import { getElaborazioneAnprSummary } from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import { formatDateTime } from "@/lib/presentation";
import type { ElaborazioneAnprSummary } from "@/types/api";

export function ElaborazioniAnprWorkspace({ embedded = false }: { embedded?: boolean }) {
  const [summary, setSummary] = useState<ElaborazioneAnprSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

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
            label="Run registrati"
            value={summary?.recent_runs.length ?? 0}
            hint={summary?.recent_runs[0] ? summary.recent_runs[0].status : "nessuno"}
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
                  {summary.recent_runs.map((run) => (
                    <tr key={run.id} className="text-gray-700">
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
