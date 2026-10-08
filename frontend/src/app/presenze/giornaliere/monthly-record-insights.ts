import type { PresenzeDailyRecord } from "@/types/api";

type OperationalAmounts = { extra: number; km: number; trasferta: number };
export type DayOperationalSummary = OperationalAmounts & { anomalies: number; requests: number };
export type CollaboratorMonthTotals = OperationalAmounts & {
  ordinary: number;
  anomalies: number;
  straordinario: number;
  reperibilita: number;
  absencesByCause: Map<string, number>;
  saturdayEntries: Array<{ ordinal: number; label: string }>;
};
export type MonthlyRecordFacts = {
  extra: number;
  ordinary: number;
  absence: { cause: string; minutes: number } | null;
  saturday: { ordinal: number; label: string } | null;
  kind: string;
  schedule: { code: string; label: string | null } | null;
};
type DailyAttentionIndexes = {
  anomalies: Map<string, Set<string>>;
  requests: Map<string, Set<string>>;
};
type ScheduleCounts = Map<string, Map<string, number>>;

function addOperationalAmounts(targets: OperationalAmounts[], amounts: OperationalAmounts): void {
  for (const totals of targets) {
    totals.extra += amounts.extra;
    totals.km += amounts.km;
    totals.trasferta += amounts.trasferta;
  }
}

function addCollaboratorDetails(totals: CollaboratorMonthTotals, record: PresenzeDailyRecord, facts: MonthlyRecordFacts): void {
  totals.ordinary += facts.ordinary;
  totals.straordinario += record.effective_straordinario_minutes ?? record.straordinario_minutes ?? 0;
  totals.reperibilita += record.reperibilita_unit !== "none" ? record.reperibilita_quantity ?? 1 : 0;
  totals.anomalies += Number(facts.kind === "anomaly");
  if (facts.saturday) totals.saturdayEntries.push(facts.saturday);
  if (facts.absence) {
    totals.absencesByCause.set(
      facts.absence.cause,
      (totals.absencesByCause.get(facts.absence.cause) ?? 0) + facts.absence.minutes,
    );
  }
}

function addDailyAttention(record: PresenzeDailyRecord, facts: MonthlyRecordFacts, totals: DayOperationalSummary, indexes: DailyAttentionIndexes): void {
  const attention: Array<{ key: keyof DailyAttentionIndexes; present: boolean }> = [
    { key: "requests", present: record.detail_requests.length > 0 || Boolean(record.request_description) },
    { key: "anomalies", present: facts.kind === "anomaly" || facts.kind === "analysis" },
  ];
  for (const { key, present } of attention) {
    if (!present) continue;
    totals[key] += 1;
    const ids = indexes[key].get(record.work_date) ?? new Set<string>();
    ids.add(record.collaborator_id);
    indexes[key].set(record.work_date, ids);
  }
}

function countSchedule(counts: ScheduleCounts, labels: Map<string, string>, collaboratorId: string, schedule: MonthlyRecordFacts["schedule"]): void {
  if (!schedule) return;
  const { code, label } = schedule;
  const perCollaborator = counts.get(collaboratorId) ?? new Map<string, number>();
  perCollaborator.set(code, (perCollaborator.get(code) ?? 0) + 1);
  counts.set(collaboratorId, perCollaborator);
  if (!labels.has(code) && label) labels.set(code, label);
}

function dominantSchedules(counts: ScheduleCounts, labels: Map<string, string>): Map<string, { code: string; label: string }> {
  const schedules = new Map<string, { code: string; label: string }>();
  for (const [collaboratorId, perCollaborator] of counts) {
    let bestCode = "";
    let bestCount = -1;
    for (const [code, occurrences] of perCollaborator) {
      if (occurrences > bestCount) {
        bestCount = occurrences;
        bestCode = code;
      }
    }
    schedules.set(collaboratorId, { code: bestCode, label: labels.get(bestCode) ?? bestCode });
  }
  return schedules;
}

export function buildMonthlyRecordInsights(records: readonly PresenzeDailyRecord[], readRecordFacts: (record: PresenzeDailyRecord) => MonthlyRecordFacts) {
  const monthTotals = new Map<string, CollaboratorMonthTotals>();
  const dayTotals = new Map<string, DayOperationalSummary>();
  const dayAnomalyCollaboratorIds = new Map<string, Set<string>>();
  const dayRequestCollaboratorIds = new Map<string, Set<string>>();
  const presentIds = new Set<string>();
  const scheduleCounts: ScheduleCounts = new Map();
  const scheduleLabels = new Map<string, string>();
  const summary = { anomalies: 0, km: 0, extra: 0, trasferta: 0 };
  for (const record of records) {
    presentIds.add(record.collaborator_id);
    const currentTotals = monthTotals.get(record.collaborator_id) ?? {
      ordinary: 0, extra: 0, km: 0, trasferta: 0, anomalies: 0, straordinario: 0, reperibilita: 0,
      absencesByCause: new Map<string, number>(), saturdayEntries: [],
    };
    const currentDayTotals = dayTotals.get(record.work_date) ?? { extra: 0, km: 0, trasferta: 0, anomalies: 0, requests: 0 };
    const facts = readRecordFacts(record);
    const amounts = { extra: facts.extra, km: record.km_value ?? 0, trasferta: record.trasferta_minutes ?? 0 };
    addOperationalAmounts([currentTotals, currentDayTotals, summary], amounts);
    addCollaboratorDetails(currentTotals, record, facts);
    addDailyAttention(record, facts, currentDayTotals, { anomalies: dayAnomalyCollaboratorIds, requests: dayRequestCollaboratorIds });
    summary.anomalies += Number(facts.kind === "anomaly");
    monthTotals.set(record.collaborator_id, currentTotals);
    dayTotals.set(record.work_date, currentDayTotals);
    countSchedule(scheduleCounts, scheduleLabels, record.collaborator_id, facts.schedule);
  }
  return {
    collaboratorSchedule: dominantSchedules(scheduleCounts, scheduleLabels),
    dayAnomalyCollaboratorIds, dayRequestCollaboratorIds, dayTotals, monthTotals, presentIds, summary,
  };
}
