import type { PresenzeCollaborator, PresenzeDailyRecord } from "@/types/api";

export type MonthAnomalyRecord = {
  record: PresenzeDailyRecord;
  kind: "anomaly" | "analysis";
  reason: string;
};
export type AnomalyPanelDayGroup = {
  iso: string;
  items: MonthAnomalyRecord[];
  anomalyCount: number;
  analysisCount: number;
};
export type AnomalyPanelCollaboratorGroup = {
  collaboratorId: string;
  collaboratorName: string;
  items: MonthAnomalyRecord[];
  anomalyCount: number;
  analysisCount: number;
};
type AnomalyComparison = (first: MonthAnomalyRecord, second: MonthAnomalyRecord) => number;

function anomalyPriorityScore(item: MonthAnomalyRecord): number {
  const base = item.kind === "anomaly" ? 0 : 1;
  return base * 100000 - item.record.operational_missing_minutes;
}

function compareInOrder(comparisons: AnomalyComparison[]): AnomalyComparison {
  return (first, second) => {
    for (const compare of comparisons) {
      const order = compare(first, second);
      if (order !== 0) return order;
    }
    return 0;
  };
}

function compareAnomalyPriority(first: MonthAnomalyRecord, second: MonthAnomalyRecord): number {
  return anomalyPriorityScore(first) - anomalyPriorityScore(second);
}

function compareAnomalyDate(first: MonthAnomalyRecord, second: MonthAnomalyRecord): number {
  return first.record.work_date.localeCompare(second.record.work_date);
}

export function anomalyPanelComparisons(collaborators: ReadonlyMap<string, PresenzeCollaborator>) {
  const compareName: AnomalyComparison = (first, second) => {
    const firstName = collaborators.get(first.record.collaborator_id)?.name ?? "";
    const secondName = collaborators.get(second.record.collaborator_id)?.name ?? "";
    return firstName.localeCompare(secondName);
  };
  return {
    month: compareInOrder([compareAnomalyPriority, compareAnomalyDate, compareName]),
    day: compareInOrder([compareAnomalyPriority, compareName]),
    collaborator: compareInOrder([compareAnomalyPriority, compareAnomalyDate]),
  };
}

export function anomalyPanelCounts(items: readonly MonthAnomalyRecord[]) {
  return {
    anomaly: items.filter((item) => item.kind === "anomaly").length,
    analysis: items.filter((item) => item.kind === "analysis").length,
  };
}

function collectAnomalyGroups(items: readonly MonthAnomalyRecord[], key: "work_date" | "collaborator_id") {
  const groups = new Map<string, MonthAnomalyRecord[]>();
  for (const item of items) {
    const groupKey = item.record[key];
    const current = groups.get(groupKey) ?? [];
    current.push(item);
    groups.set(groupKey, current);
  }
  return Array.from(groups.entries());
}

function anomalyGroupItems(items: MonthAnomalyRecord[], comparison: AnomalyComparison) {
  const counts = anomalyPanelCounts(items);
  return {
    items: [...items].sort(comparison),
    anomalyCount: counts.anomaly,
    analysisCount: counts.analysis,
  };
}

export function buildAnomalyDayGroups(
  items: readonly MonthAnomalyRecord[],
  collaborators: ReadonlyMap<string, PresenzeCollaborator>,
): AnomalyPanelDayGroup[] {
  const comparison = anomalyPanelComparisons(collaborators).day;
  return collectAnomalyGroups(items, "work_date")
    .sort((first, second) => first[0].localeCompare(second[0]))
    .map(([iso, entries]) => ({ iso, ...anomalyGroupItems(entries, comparison) }));
}

export function buildAnomalyCollaboratorGroups(
  items: readonly MonthAnomalyRecord[],
  collaborators: ReadonlyMap<string, PresenzeCollaborator>,
): AnomalyPanelCollaboratorGroup[] {
  const comparison = anomalyPanelComparisons(collaborators).collaborator;
  return collectAnomalyGroups(items, "collaborator_id")
    .map(([collaboratorId, entries]) => ({
      collaboratorId,
      collaboratorName: collaborators.get(collaboratorId)?.name ?? collaboratorId,
      ...anomalyGroupItems(entries, comparison),
    }))
    .sort((first, second) => {
      if (second.anomalyCount !== first.anomalyCount) return second.anomalyCount - first.anomalyCount;
      if (second.items.length !== first.items.length) return second.items.length - first.items.length;
      return first.collaboratorName.localeCompare(second.collaboratorName);
    });
}
