"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import {
  ModuleWorkspaceHero,
  ModuleWorkspaceKpiRow,
  ModuleWorkspaceKpiTile,
  ModuleWorkspaceNoticeCard,
} from "@/components/layout/module-workspace-hero";
import { DocumentIcon, FolderIcon } from "@/components/ui/icons";
import { getRiordinoDashboard } from "@/lib/riordino-api";
import type { RiordinoDashboardResponse } from "@/types/riordino";

const emptyDashboard: RiordinoDashboardResponse = {
  practices_by_status: {},
  practices_by_phase: {},
  blocking_issues_open: 0,
  recent_events: [],
};

export function RiordinoDashboardOverview({ token }: { token: string }) {
  const [dashboard, setDashboard] = useState<RiordinoDashboardResponse>(emptyDashboard);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      try {
        const response = await getRiordinoDashboard(token);
        setDashboard(response);
        setLoadError(null);
      } catch (error) {
        setLoadError(error instanceof Error ? error.message : "Errore nel caricamento dashboard");
      }
    }

    void loadData();
  }, [token]);

  return (
    <div className="page-stack">
      <ModuleWorkspaceHero
        badge={
          <>
            <DocumentIcon className="h-3.5 w-3.5" />
            Riordino catastale
          </>
        }
        title="Dashboard operativa per pratiche, fasi, anomalie e cronologia recente."
        description="Vista sintetica del modulo Riordino con accesso rapido all’elenco pratiche e agli ultimi eventi registrati."
        actions={
          <>
            {loadError ? (
              <ModuleWorkspaceNoticeCard title="Caricamento non riuscito" description={loadError} tone="danger" />
            ) : (
              <ModuleWorkspaceNoticeCard
                title="Stato backend"
                description="Le metriche riflettono i conteggi restituiti dalle API del modulo Riordino."
                tone="info"
              />
            )}
            <div className="flex flex-wrap gap-2">
              <Link className="btn-primary" href="/riordino/pratiche">
                <FolderIcon className="h-4 w-4" />
                Apri pratiche
              </Link>
            </div>
          </>
        }
      >
        <ModuleWorkspaceKpiRow>
          <ModuleWorkspaceKpiTile label="Pratiche aperte" value={dashboard.practices_by_status.open ?? 0} hint="stato open" variant="emerald" />
          <ModuleWorkspaceKpiTile label="Fase 1" value={dashboard.practices_by_phase.phase_1 ?? 0} hint="pratiche in fase 1" />
          <ModuleWorkspaceKpiTile label="Fase 2" value={dashboard.practices_by_phase.phase_2 ?? 0} hint="pratiche in fase 2" />
          <ModuleWorkspaceKpiTile label="Issue blocking" value={dashboard.blocking_issues_open} hint="anomalie aperte" variant="amber" />
        </ModuleWorkspaceKpiRow>
      </ModuleWorkspaceHero>

      <article className="panel-card">
        <p className="section-title">Ultimi eventi</p>
        <div className="mt-4 space-y-3">
          {dashboard.recent_events.length === 0 ? (
            <p className="text-sm text-gray-500">Nessun evento disponibile.</p>
          ) : (
            dashboard.recent_events.slice(0, 10).map((event) => (
              <div key={event.id} className="rounded-xl border border-gray-100 px-4 py-3">
                <p className="text-sm font-medium text-gray-900">{event.event_type}</p>
                <p className="mt-1 text-xs text-gray-500">{new Date(event.created_at).toLocaleString("it-IT")}</p>
              </div>
            ))
          )}
        </div>
      </article>
    </div>
  );
}
