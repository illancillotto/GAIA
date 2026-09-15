import * as api from "@/lib/api";
import { ApiError } from "@/lib/api/core";
import { catastoGisGetLatestAdeWfsRunStatus } from "@/lib/api/catasto";
import { getVehicleAutodocSyncStatus } from "@/features/operazioni/api/client";
import { SYNC_JOB_SERVICES } from "./sync-dashboard-jobs";
import { jobSnapshot, type SyncService } from "./sync-dashboard-model";

export const SYNC_SERVICES: SyncService[] = [
  ...SYNC_JOB_SERVICES,
  {
    id: "whitecompany", title: "WhiteCompany", description: "Stato di ogni flusso anagrafico e operativo.", href: "/elaborazioni/bonifica",
    async load(token) {
      const result = await api.getBonificaSyncStatus(token);
      return Object.values(result.entities).map((item) => ({
        status: item.status, detail: item.entity, startedAt: item.last_started_at,
        finishedAt: item.last_finished_at, error: item.error_detail,
        metrics: [
          { label: "Sincronizzati", value: item.records_synced ?? "-" },
          { label: "Saltati", value: item.records_skipped ?? "-" },
          { label: "Errori", value: item.records_errors ?? "-" },
        ],
      }));
    },
  },
  {
    id: "autodoc", title: "AUTODOC mezzi", description: "Aggiornamento delle schede del parco mezzi.", href: "/elaborazioni/autodoc",
    async load() {
      const job = await getVehicleAutodocSyncStatus();
      if (!job) return [];
      return jobSnapshot({ ...job, created_at: job.started_at }, [
        { label: "Sincronizzati", value: job.records_synced ?? "-" },
        { label: "Saltati", value: job.records_skipped ?? "-" },
        { label: "Errori", value: job.records_errors ?? "-" },
      ]);
    },
  },
  {
    id: "mobile", title: "GAIA Mobile Sync", description: "Invio operatori e richieste al gateway pubblico.", href: "/elaborazioni/gaia-mobile-sync",
    async load(token) {
      const data = await api.getGateMobileSyncStatus(token);
      const run = data.last_run;
      const configurationError = data.gateway_configured && data.token_configured ? null : "Configurazione gateway o token incompleta";
      const metrics = [
        { label: "Invio automatico", value: data.sync_enabled ? "Attivo" : "Disattivato" },
        { label: "Configurazione", value: data.gateway_configured && data.token_configured ? "Completa" : "Incompleta" },
      ];
      if (!run) return [{ status: "idle", metrics, error: configurationError, detail: "Nessuna sincronizzazione registrata" }];
      return [{ status: run.status, startedAt: run.started_at, finishedAt: run.finished_at,
        error: run.error_message ?? configurationError, metrics: [...metrics,
          { label: "Operatori inviati", value: run.operators_pushed },
          { label: "Richieste", value: run.requested_tasks_count },
        ] }];
    },
  },
  {
    id: "autosync", title: "SISTER autosync", description: "Sincronizzazione continua di ruolo e comprensorio.", href: "/elaborazioni/autosync",
    async load(token) {
      const data = await api.getElaborazioneRuoloAutoSyncStatus(token);
      const snapshots = jobSnapshot(data.running_batch ?? data.last_batch ?? undefined);
      return [{ ...snapshots[0], status: snapshots[0]?.status ?? "idle",
        error: data.config.last_error_message,
        metrics: [
          { label: "Pianificazione", value: data.config.enabled ? "Attiva" : "Disattivata" },
          { label: "Ultimo planner", value: data.config.last_planner_at ?? "Mai eseguito" },
          { label: "Dimensione batch", value: data.config.batch_size },
        ] }];
    },
  },
  {
    id: "ade", title: "Allineamento AdE", description: "Acquisizione geometrie catastali e avanzamento territoriale.", href: "/elaborazioni/ade-alignment",
    async load(token) {
      try {
        const run = await catastoGisGetLatestAdeWfsRunStatus(token);
        return [{ status: run.status, startedAt: run.started_at, finishedAt: run.completed_at,
          error: run.error, detail: run.progress_message,
          metrics: [{ label: "Avanzamento (%)", value: run.progress_percent },
            { label: "Riquadri", value: `${run.tiles_completed} / ${run.tiles}` },
            { label: "Geometrie", value: run.with_geometry }] }];
      } catch (error) {
        if (error instanceof ApiError && error.status === 404) return [];
        throw error;
      }
    },
  },
  {
    id: "anpr", title: "ANPR", description: "Verifiche anagrafiche e consumo delle chiamate giornaliere.", href: "/elaborazioni/anpr",
    async load(token) {
      const data = await api.getElaborazioneAnprSummary(token);
      const run = [...data.recent_runs].sort((a, b) => Date.parse(b.started_at) - Date.parse(a.started_at))[0];
      return [{ status: run?.status ?? "idle", startedAt: run?.started_at, finishedAt: run?.completed_at,
        metrics: [{ label: "Chiamate oggi", value: `${data.calls_today} / ${data.effective_daily_limit}` },
          { label: "Soggetti ultimo run", value: run?.subjects_processed ?? "-" },
          { label: "Errori ultimo run", value: run?.errors ?? "-" }] }];
    },
  },
];
