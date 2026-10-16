import { useEffect, useRef, useState, type Dispatch, type MutableRefObject, type SetStateAction } from "react";

import { getStoredAccessToken } from "@/lib/auth";
import type { PresenzeSyncJob } from "@/types/api";

export const EXPORT_JOB_HISTORY_LIMIT = 25;
export const EXPORT_JOB_HISTORY_POLL_INTERVAL_MS = 2500;

type RefreshOptions = { silent?: boolean; suppressCompletionNotice?: boolean };

export type ExportJobHistoryOptions = {
  enabled: boolean;
  listJobs: (token: string, params: { limit: number }) => Promise<PresenzeSyncJob[]>;
  completionNotice: (job: PresenzeSyncJob) => string;
  loadErrorMessage: string;
  onSuccess: (message: string) => void;
  onError: (message: string) => void;
};

export type ExportJobHistory = {
  jobs: PresenzeSyncJob[];
  setJobs: Dispatch<SetStateAction<PresenzeSyncJob[]>>;
  isLoading: boolean;
  knownStatusesRef: MutableRefObject<Map<string, string>>;
};

export function sortExportJobs(items: PresenzeSyncJob[]): PresenzeSyncJob[] {
  return [...items].sort((left, right) => Date.parse(right.created_at) - Date.parse(left.created_at));
}

export function isActiveExportJobStatus(status: string | undefined): boolean {
  return status === "pending" || status === "running";
}

export function hasActiveExportJob(knownStatuses: Map<string, string>): boolean {
  return Array.from(knownStatuses.values()).some(isActiveExportJobStatus);
}

export function findNewlyCompletedJobs(items: PresenzeSyncJob[], knownStatuses: Map<string, string>): PresenzeSyncJob[] {
  return items.filter((item) => isActiveExportJobStatus(knownStatuses.get(item.id)) && item.status === "completed");
}

type ExportJobHistoryRefreshContext = Omit<ExportJobHistoryOptions, "enabled"> & {
  token: string;
  knownStatusesRef: MutableRefObject<Map<string, string>>;
  isCancelled: () => boolean;
  setJobs: (items: PresenzeSyncJob[]) => void;
  setIsLoading: (value: boolean) => void;
};

async function refreshExportJobHistory(context: ExportJobHistoryRefreshContext, options: RefreshOptions): Promise<void> {
  if (!options.silent) {
    context.setIsLoading(true);
  }
  try {
    const items = sortExportJobs(await context.listJobs(context.token, { limit: EXPORT_JOB_HISTORY_LIMIT }));
    if (context.isCancelled()) return;

    if (!options.suppressCompletionNotice) {
      findNewlyCompletedJobs(items, context.knownStatusesRef.current).forEach((item) => context.onSuccess(context.completionNotice(item)));
    }

    context.knownStatusesRef.current = new Map(items.map((item) => [item.id, item.status]));
    context.setJobs(items);
  } catch (loadError) {
    if (!context.isCancelled()) {
      context.onError(loadError instanceof Error ? loadError.message : context.loadErrorMessage);
    }
  } finally {
    if (!context.isCancelled() && !options.silent) {
      context.setIsLoading(false);
    }
  }
}

/**
 * Loads an export-job history and polls it silently while a known job is pending or running.
 * `listJobs`, `completionNotice`, `onSuccess` and `onError` must be referentially stable
 * (module-level functions or React state setters): they are effect dependencies, so a new
 * reference on each render would restart the load and the polling interval.
 */
export function useExportJobHistory({
  enabled,
  listJobs,
  completionNotice,
  loadErrorMessage,
  onSuccess,
  onError,
}: ExportJobHistoryOptions): ExportJobHistory {
  const [jobs, setJobs] = useState<PresenzeSyncJob[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const knownStatusesRef = useRef<Map<string, string>>(new Map());

  useEffect(() => {
    const token = getStoredAccessToken();
    if (!token) return;
    if (!enabled) {
      setIsLoading(false);
      setJobs([]);
      knownStatusesRef.current = new Map();
      return;
    }

    let cancelled = false;
    const context: ExportJobHistoryRefreshContext = {
      token,
      listJobs,
      completionNotice,
      loadErrorMessage,
      onSuccess,
      onError,
      knownStatusesRef,
      isCancelled: () => cancelled,
      setJobs,
      setIsLoading,
    };

    void refreshExportJobHistory(context, { suppressCompletionNotice: true });
    const intervalId = window.setInterval(() => {
      if (!hasActiveExportJob(knownStatusesRef.current)) {
        return;
      }
      void refreshExportJobHistory(context, { silent: true });
    }, EXPORT_JOB_HISTORY_POLL_INTERVAL_MS);

    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
    };
  }, [enabled, listJobs, completionNotice, loadErrorMessage, onSuccess, onError]);

  return { jobs, setJobs, isLoading, knownStatusesRef };
}
