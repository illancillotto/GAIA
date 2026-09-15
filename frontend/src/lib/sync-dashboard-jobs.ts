import * as api from "@/lib/api";
import { jobSnapshot, latestSync, resultMetrics, type SyncService } from "./sync-dashboard-model";

export const SYNC_JOB_SERVICES: SyncService[] = [
  {
    id: "domande-irrigue", title: "Capacitas domande irrigue", description: "Ultimo sync delle domande irrigue.", href: "/catasto/domande-irrigue",
    async load(token) {
      const job = latestSync(await api.listCapacitasDomandeIrrigueSyncJobs(token));
      return jobSnapshot(job, resultMetrics(job?.result_json));
    },
  },
  {
    id: "capacitas-storico", title: "Capacitas anagrafica", description: "Ultimo import dello storico anagrafico.", href: "/elaborazioni/capacitas?section=storico",
    async load(token) {
      const job = latestSync(await api.listCapacitasAnagraficaHistoryJobs(token));
      return jobSnapshot(job, resultMetrics(job?.result_json));
    },
  },
  {
    id: "capacitas-terreni", title: "Capacitas terreni", description: "Ultimo batch di terreni e certificati.", href: "/elaborazioni/capacitas?section=terreni",
    async load(token) {
      const job = latestSync(await api.listCapacitasTerreniJobs(token));
      return jobSnapshot(job, resultMetrics(job?.result_json));
    },
  },
  {
    id: "capacitas", title: "Capacitas particelle", description: "Ultimo sync delle particelle catastali.", href: "/elaborazioni/capacitas",
    async load(token) {
      const job = latestSync(await api.listCapacitasParticelleSyncJobs(token));
      return jobSnapshot(job, resultMetrics(job?.result_json));
    },
  },
  {
    id: "incass", title: "Capacitas inCass", description: "Solo l'ultimo sync di avvisi e partitario.", href: "/elaborazioni/capacitas?section=incass",
    async load(token) {
      const job = latestSync(await api.listCapacitasInCassSyncJobs(token, { limit: 1 }));
      return jobSnapshot(job, resultMetrics(job?.result_json));
    },
  },
  {
    id: "posta", title: "Poste Online", description: "Sincronizzazione raccomandate e documenti.", href: "/elaborazioni/posta-online",
    async load(token) {
      const job = latestSync(await api.listPostaOnlineRegisteredMailJobs(token));
      return jobSnapshot(job, resultMetrics(job?.result_json));
    },
  },
  {
    id: "presenze", title: "Presenze INAZ", description: "Import delle presenze e dei cartellini.", href: "/elaborazioni/presenze-sync",
    async load(token) {
      const job = latestSync(await api.listPresenzeSyncJobs(token, { limit: 1 }));
      if (!job) return [];
      return jobSnapshot(job, [
        { label: "Periodo", value: `${job.period_start} / ${job.period_end}` },
        { label: "Importati", value: job.records_imported },
        { label: "Saltati", value: job.records_skipped },
        { label: "Errori", value: job.records_errors },
      ]);
    },
  },
  {
    id: "visure", title: "SISTER visure", description: "Batch di richieste catastali e relativo avanzamento.", href: "/elaborazioni/visure",
    async load(token) {
      const job = latestSync(await api.getElaborazioneBatches(token));
      if (!job) return [];
      return jobSnapshot(job, [
        { label: "Richieste", value: job.total_items }, { label: "Completate", value: job.completed_items },
        { label: "Fallite", value: job.failed_items }, { label: "Operazione", value: job.current_operation ?? "In attesa" },
      ]);
    },
  },
  {
    id: "nas", title: "NAS e directory", description: "Utenti, gruppi, condivisioni e permessi.", href: "/nas-control/sync",
    async load(token) {
      const job = latestSync(await api.getSyncJobs(token));
      if (!job) return [];
      return jobSnapshot(job, [
        { label: "Utenti", value: job.persisted_users }, { label: "Gruppi", value: job.persisted_groups },
        { label: "Condivisioni", value: job.persisted_shares }, { label: "Permessi", value: job.persisted_permission_entries },
      ]);
    },
  },
];
