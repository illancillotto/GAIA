import { describe, expect, test } from "vitest";

import { buildMonthlyRecordInsights } from "@/app/presenze/giornaliere/monthly-record-insights";
import type { MonthlyRecordFacts } from "@/app/presenze/giornaliere/monthly-record-insights";
import type { PresenzeDailyRecord } from "@/types/api";

function record(overrides: Partial<PresenzeDailyRecord> = {}): PresenzeDailyRecord {
  return {
    id: "record-1", collaborator_id: "collaborator-1", work_date: "2026-05-16",
    km_value: null, trasferta_minutes: null, effective_straordinario_minutes: null,
    straordinario_minutes: null, reperibilita_unit: "none", reperibilita_quantity: null,
    detail_requests: [], request_description: null, ...overrides,
  } as PresenzeDailyRecord;
}

function facts(overrides: Partial<MonthlyRecordFacts> = {}): MonthlyRecordFacts {
  return { extra: 0, ordinary: 0, absence: null, saturday: null, kind: "worked", schedule: null, ...overrides };
}

describe("monthly record insights", () => {
  test("counts attention per record while keeping distinct daily sets and blocking-only month counts", () => {
    const items = [
      record({ id: "analysis", request_description: "Permesso" }),
      record({ id: "blocking", detail_requests: [{}] }),
      record({ id: "other", collaborator_id: "collaborator-2" }),
    ];
    const result = buildMonthlyRecordInsights(items, (item) => facts({ kind: item.id === "blocking" ? "anomaly" : "analysis" }));
    expect(result.summary.anomalies).toBe(1);
    expect(result.monthTotals.get("collaborator-1")!.anomalies).toBe(1);
    expect(result.monthTotals.get("collaborator-2")!.anomalies).toBe(0);
    expect(result.dayTotals.get("2026-05-16")).toEqual({ extra: 0, km: 0, trasferta: 0, anomalies: 3, requests: 2 });
    expect([...result.dayAnomalyCollaboratorIds.get("2026-05-16")!]).toEqual(["collaborator-1", "collaborator-2"]);
    expect([...result.dayRequestCollaboratorIds.get("2026-05-16")!]).toEqual(["collaborator-1"]);
  });

  test("retains schedule insertion-order ties, first global truthy label and raw-code fallback", () => {
    const items = [record(), record({ id: "second" }), record({ id: "label", collaborator_id: "collaborator-2" }), record({ id: "later", collaborator_id: "collaborator-3" }), record({ id: "fallback", collaborator_id: "collaborator-4" })];
    const schedules = new Map<string, MonthlyRecordFacts["schedule"]>([
      ["record-1", { code: "FIRST", label: "" }], ["second", { code: "SECOND", label: "Second" }],
      ["label", { code: "FIRST", label: "First label" }], ["later", { code: "FIRST", label: "Later label" }],
      ["fallback", { code: "RAW", label: null }],
    ]);
    const result = buildMonthlyRecordInsights(items, (item) => facts({ schedule: schedules.get(item.id)! }));
    expect([...result.collaboratorSchedule]).toEqual([
      ["collaborator-1", { code: "FIRST", label: "First label" }],
      ["collaborator-2", { code: "FIRST", label: "First label" }],
      ["collaborator-3", { code: "FIRST", label: "First label" }],
      ["collaborator-4", { code: "RAW", label: "RAW" }],
    ]);
  });

  test("preserves left-to-right floating arithmetic independently in each accumulator and retains source records", () => {
    const items = [
      record({ km_value: 1e16, trasferta_minutes: 1e16 }),
      record({ id: "negative", km_value: -1e16, trasferta_minutes: -1e16 }),
      record({ id: "last", km_value: 1, trasferta_minutes: 1 }),
    ];
    const original = structuredClone(items);
    items.forEach(Object.freeze);
    Object.freeze(items);
    const result = buildMonthlyRecordInsights(items, (item) => facts({ extra: item.km_value!, ordinary: item.km_value! }));
    expect(result.summary).toEqual({ anomalies: 0, extra: 1, km: 1, trasferta: 1 });
    expect(result.monthTotals.get("collaborator-1")).toMatchObject({ extra: 1, km: 1, trasferta: 1, ordinary: 1 });
    expect(result.dayTotals.get("2026-05-16")).toMatchObject({ extra: 1, km: 1, trasferta: 1 });
    expect(items).toEqual(original);
  });

  test("accumulates absences per cause and preserves Saturday arrival order without sorting", () => {
    const items = [record({ id: "third" }), record({ id: "first" }), record({ id: "repeat" })];
    const perRecord = new Map([
      ["third", facts({ absence: { cause: "ferie", minutes: 120 }, saturday: { ordinal: 3, label: "fer" } })],
      ["first", facts({ absence: { cause: "permesso", minutes: 60 }, saturday: { ordinal: 1, label: "perm" } })],
      ["repeat", facts({ absence: { cause: "ferie", minutes: 60 }, saturday: { ordinal: 3, label: "fer" } })],
    ]);
    const result = buildMonthlyRecordInsights(items, (item) => perRecord.get(item.id)!);
    expect([...result.monthTotals.get("collaborator-1")!.absencesByCause]).toEqual([["ferie", 180], ["permesso", 60]]);
    expect(result.monthTotals.get("collaborator-1")!.saturdayEntries).toEqual([
      { ordinal: 3, label: "fer" }, { ordinal: 1, label: "perm" }, { ordinal: 3, label: "fer" },
    ]);
  });

  test.each([0, -1, Number.NaN])("does not replace an explicit numeric value (%s) through truthy fallback", (value) => {
    const result = buildMonthlyRecordInsights([
      record({ km_value: value, trasferta_minutes: value, effective_straordinario_minutes: value, straordinario_minutes: 120, reperibilita_unit: "days", reperibilita_quantity: value }),
    ], () => facts({ extra: value, ordinary: value }));
    expect(result.summary).toEqual({ anomalies: 0, extra: value, km: value, trasferta: value });
    expect(result.monthTotals.get("collaborator-1")).toMatchObject({ extra: value, ordinary: value, km: value, trasferta: value, straordinario: value, reperibilita: value });
    expect(result.dayTotals.get("2026-05-16")).toMatchObject({ extra: value, km: value, trasferta: value });
  });

  test("uses only nullish defaults, keeps independent day groups and builds fresh results each time", () => {
    const items = [record({ reperibilita_unit: "days" }), record({ id: "next", work_date: "2026-05-17", straordinario_minutes: 60 })];
    const first = buildMonthlyRecordInsights(items, () => facts());
    const second = buildMonthlyRecordInsights(items, () => facts());
    expect(first.monthTotals.get("collaborator-1")).toMatchObject({ reperibilita: 1, straordinario: 60, extra: 0, km: 0, trasferta: 0 });
    expect([...first.dayTotals.keys()]).toEqual(["2026-05-16", "2026-05-17"]);
    expect(first.dayTotals.get("2026-05-16")).not.toBe(first.dayTotals.get("2026-05-17"));
    expect(first.monthTotals).not.toBe(second.monthTotals);
    expect(first.monthTotals.get("collaborator-1")!.absencesByCause).not.toBe(second.monthTotals.get("collaborator-1")!.absencesByCause);
    expect(first.presentIds).toEqual(new Set(["collaborator-1"]));
    expect(first.dayAnomalyCollaboratorIds.size).toBe(0);
    expect(first.dayRequestCollaboratorIds.size).toBe(0);
  });

  test("returns an empty model without reading facts for an empty month", () => {
    const result = buildMonthlyRecordInsights([], () => { throw new Error("No source records"); });
    expect(result.summary).toEqual({ anomalies: 0, extra: 0, km: 0, trasferta: 0 });
    expect(result.monthTotals.size).toBe(0);
    expect(result.dayTotals.size).toBe(0);
    expect(result.collaboratorSchedule.size).toBe(0);
    expect(result.presentIds.size).toBe(0);
  });
});
