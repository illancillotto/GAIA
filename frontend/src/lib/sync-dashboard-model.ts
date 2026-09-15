export type SyncMetric = { label: string; value: string | number };
export type SyncSnapshot = {
  status: string;
  startedAt?: string | null;
  finishedAt?: string | null;
  error?: string | null;
  detail?: string | null;
  metrics: SyncMetric[];
};
export type SyncService = {
  id: string;
  title: string;
  description: string;
  href: string;
  load: (token: string) => Promise<SyncSnapshot[]>;
};
export type SyncServiceState = {
  snapshots: SyncSnapshot[];
  updatedAt: string | null;
  error: string | null;
};

const ACTIVE = new Set(["pending", "queued", "processing", "running", "queued_resume"]);
const ATTENTION = new Set(["failed", "error", "partial", "completed_with_errors", "skipped"]);
const LABELS: Record<string, string> = {
  pending: "In coda", queued: "In coda", processing: "In corso", running: "In corso",
  queued_resume: "In ripresa", completed: "Completato", success: "Completato", succeeded: "Completato",
  failed: "Fallito", error: "Errore", partial: "Parziale", completed_with_errors: "Con errori",
  skipped: "Saltato", cancelled: "Annullato", idle: "In attesa", enabled: "Attivo", disabled: "Disattivato",
};

export function syncStatus(status: string): { label: string; tone: string } {
  if (ACTIVE.has(status)) return { label: LABELS[status], tone: "bg-sky-100 text-sky-800" };
  if (ATTENTION.has(status)) return { label: LABELS[status], tone: "bg-amber-100 text-amber-900" };
  return { label: LABELS[status] ?? status, tone: "bg-stone-100 text-stone-700" };
}

export function syncCounts(states: Record<string, SyncServiceState>): { active: number; attention: number } {
  const values = Object.values(states);
  return {
    active: values.filter((value) => value.snapshots.some((item) => ACTIVE.has(item.status))).length,
    attention: values.filter((value) => value.error || value.snapshots.some((item) => item.error || ATTENTION.has(item.status))).length,
  };
}

export type SyncFilter = "all" | "attention" | "active";

export function matchesSyncFilter(state: SyncServiceState | undefined, filter: SyncFilter): boolean {
  if (filter === "all") return true;
  if (!state) return false;
  return syncCounts({ service: state })[filter] > 0;
}

export function syncSummary(state?: SyncServiceState): { label: string; tone: string; lastStarted?: string } {
  if (!state) return { label: "Caricamento stato...", tone: "bg-stone-100 text-stone-600" };
  const lastStarted = state.snapshots.map((snapshot) => snapshot.startedAt).filter((date): date is string => Boolean(date))
    .sort((a, b) => Date.parse(b) - Date.parse(a))[0];
  const counts = syncCounts({ service: state });
  if (counts.attention) return { label: "Da verificare", tone: "bg-amber-100 text-amber-900", lastStarted };
  if (counts.active) return { label: "In corso / in coda", tone: "bg-sky-100 text-sky-800", lastStarted };
  if (!state.snapshots.length) return { label: "Nessuna esecuzione", tone: "bg-stone-100 text-stone-600" };
  if (state.snapshots.length > 1) return { label: "Nessun flusso attivo", tone: "bg-stone-100 text-stone-700", lastStarted };
  return { ...syncStatus(state.snapshots[0].status), lastStarted };
}

type Job = {
  status: string;
  created_at: string;
  started_at?: string | null;
  completed_at?: string | null;
  finished_at?: string | null;
  error_detail?: string | null;
};

export function latestSync<T extends Job>(jobs: T[]): T | undefined {
  return [...jobs].sort((a, b) => Date.parse(b.created_at) - Date.parse(a.created_at))[0];
}

export function jobSnapshot(job: Job | undefined, metrics: SyncMetric[] = []): SyncSnapshot[] {
  if (!job) return [];
  return [{ status: job.status, startedAt: job.started_at ?? job.created_at,
    finishedAt: job.completed_at ?? job.finished_at, error: job.error_detail, metrics }];
}

const RESULT_LABELS: Record<string, string> = {
  processed_subjects: "Soggetti elaborati", notices_synced: "Avvisi sincronizzati",
  processed_items: "Elementi elaborati", total_items: "Elementi totali",
  progress_percent: "Avanzamento (%)", records_imported: "Record importati",
  records_errors: "Errori", synced_items: "Elementi sincronizzati",
  success_items: "Completati", failed_items: "Errori", skipped_items: "Saltati",
  failed_subjects: "Soggetti falliti", records_total: "Record totali", records_matched: "Record associati",
  records_unmatched: "Record non associati", details_scraped: "Dettagli acquisiti",
  processed: "Elaborati", imported: "Importati", skipped: "Saltati", failed: "Falliti",
  processed_rows: "Righe elaborate", total_rows: "Righe totali", domande_inserted: "Domande inserite",
  domande_updated: "Domande aggiornate", anomalies_opened: "Anomalie aperte",
};

export function resultMetrics(result: unknown): SyncMetric[] {
  if (!result || typeof result !== "object" || Array.isArray(result)) return [];
  return Object.entries(result)
    .filter(([key, value]) => key in RESULT_LABELS && typeof value === "number")
    .map(([key, value]) => ({ label: RESULT_LABELS[key], value: value as number }));
}

export function syncError(error: unknown): string {
  return error instanceof Error ? error.message : "Impossibile leggere lo stato del servizio";
}
