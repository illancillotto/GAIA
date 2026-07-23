export const INCASS_JOB_COLLAPSED_LIMIT = 15;

export type CapacitasInCassVisibleJob = {
  status: string;
};

export type CapacitasInCassVisibleJobsResult<T extends CapacitasInCassVisibleJob> = {
  items: T[];
  hiddenCount: number;
};

export function isCapacitasInCassActiveJobStatus(status: string): boolean {
  return status === "pending" || status === "processing" || status === "queued_resume";
}

export function isCapacitasInCassRunningJobStatus(status: string): boolean {
  return status === "processing" || status === "queued_resume";
}

export function getVisibleCapacitasInCassJobs<T extends CapacitasInCassVisibleJob>(
  jobs: T[],
  expanded: boolean,
  limit = INCASS_JOB_COLLAPSED_LIMIT,
): CapacitasInCassVisibleJobsResult<T> {
  if (expanded) {
    return { items: jobs, hiddenCount: 0 };
  }

  const ordered = [
    ...jobs.filter((job) => isCapacitasInCassRunningJobStatus(job.status)),
    ...jobs.filter((job) => !isCapacitasInCassRunningJobStatus(job.status)),
  ];
  const items = ordered.slice(0, limit);
  return { items, hiddenCount: Math.max(0, jobs.length - items.length) };
}
