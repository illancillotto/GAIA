export const MAX_RUNNING_OPERATIONS_PER_AREA = 3;

const ACTIVE_BATCH_STATUSES = new Set(["pending", "processing"]);
const ACTIVE_JOB_STATUSES = new Set(["pending", "processing", "queued_resume"]);
const ACTIVE_BONIFICA_STATUSES = new Set(["running"]);

export type DashboardPollingSnapshot = {
  batchStatuses: Iterable<string>;
  particelleStatuses: Iterable<string>;
  incassStatuses: Iterable<string>;
  bonificaStatuses: Iterable<string>;
  postaOnlineStatuses: Iterable<string>;
  autodocStatus: string | null | undefined;
  gateMobileStatus: string | null | undefined;
};

export type CollapsibleRunningOperation = {
  area: string;
};

export type HiddenRunningOperationsByArea<T extends CollapsibleRunningOperation> = {
  area: string;
  hiddenCount: number;
  sample: T;
};

export type CollapsedRunningOperations<T extends CollapsibleRunningOperation> = {
  items: T[];
  hiddenByArea: HiddenRunningOperationsByArea<T>[];
  totalCount: number;
};

function hasStatus(statuses: Iterable<string>, allowed: Set<string>): boolean {
  for (const status of statuses) {
    if (allowed.has(status)) return true;
  }
  return false;
}

export function dashboardHasActivePollingTargets(snapshot: DashboardPollingSnapshot): boolean {
  return (
    hasStatus(snapshot.batchStatuses, ACTIVE_BATCH_STATUSES) ||
    hasStatus(snapshot.particelleStatuses, ACTIVE_JOB_STATUSES) ||
    hasStatus(snapshot.incassStatuses, ACTIVE_JOB_STATUSES) ||
    hasStatus(snapshot.bonificaStatuses, ACTIVE_BONIFICA_STATUSES) ||
    hasStatus(snapshot.postaOnlineStatuses, ACTIVE_JOB_STATUSES) ||
    snapshot.autodocStatus === "queued" ||
    snapshot.autodocStatus === "running" ||
    snapshot.gateMobileStatus === "running"
  );
}

export function collapseRunningOperationsByArea<T extends CollapsibleRunningOperation>(
  operations: T[],
  limit = MAX_RUNNING_OPERATIONS_PER_AREA,
): CollapsedRunningOperations<T> {
  const visibleCountByArea: Record<string, number> = {};
  const hiddenCountByArea: Record<string, number> = {};
  const sampleByArea: Partial<Record<string, T>> = {};
  const items: T[] = [];

  for (const operation of operations) {
    const visibleCount = visibleCountByArea[operation.area] ?? 0;
    if (visibleCount < limit) {
      visibleCountByArea[operation.area] = visibleCount + 1;
      items.push(operation);
      sampleByArea[operation.area] ??= operation;
      continue;
    }
    hiddenCountByArea[operation.area] = (hiddenCountByArea[operation.area] ?? 0) + 1;
    sampleByArea[operation.area] ??= operation;
  }

  return {
    items,
    hiddenByArea: Object.keys(hiddenCountByArea).map((area) => ({
      area,
      hiddenCount: hiddenCountByArea[area] as number,
      sample: sampleByArea[area] as T,
    })),
    totalCount: operations.length,
  };
}
