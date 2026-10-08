import { describe, expect, test } from "vitest";

import { selectMonthlyCollaboratorRows } from "@/app/presenze/giornaliere/collaborator-rows";
import type { PresenzeCollaborator } from "@/types/api";

const collaborator: PresenzeCollaborator = {
  id: "collaborator-1",
  owner_user_id: null,
  application_user_id: null,
  kint: "1",
  kkint: "1",
  employee_code: "1",
  company_code: "53",
  company_label: null,
  name: "ALFA",
  birth_date: null,
  contract_kind: null,
  operai_group: null,
  standard_daily_minutes: null,
  is_active: true,
  last_seen_at: null,
  created_at: "2026-10-08T00:00:00Z",
  updated_at: "2026-10-08T00:00:00Z",
};

function selection(): Parameters<typeof selectMonthlyCollaboratorRows>[0] {
  return {
    collaborators: [collaborator],
    presentIds: new Set([collaborator.id]),
    collaboratorSchedule: new Map(),
    anomalyCollaboratorIds: new Set(),
    dayAnomalyCollaboratorIds: new Map(),
    dayRequestCollaboratorIds: new Map(),
    monthTotals: new Map([[collaborator.id, { km: 1, trasferta: 1, straordinario: 1, reperibilita: 1 }]]),
    filters: {
      search: "", schedule: "", profile: "", anomalies: false, dayFocus: null,
      km: false, trasferta: false, straordinario: false, reperibilita: false,
    },
  };
}

describe("monthly collaborator selection", () => {
  test.each(["km", "trasferta", "straordinario", "reperibilita"] as const)(
    "preserves the non-positive exclusion contract for %s, including NaN",
    (key) => {
      const input = selection();
      input.filters[key] = true;
      for (const value of [1, Number.NaN, Number.POSITIVE_INFINITY]) {
        input.monthTotals.get(collaborator.id)![key] = value;
        expect(selectMonthlyCollaboratorRows(input)).toEqual([collaborator]);
      }
      for (const value of [0, -1, Number.NEGATIVE_INFINITY]) {
        input.monthTotals.get(collaborator.id)![key] = value;
        expect(selectMonthlyCollaboratorRows(input)).toEqual([]);
      }
    },
  );

  test("ignores inactive totals and short-circuits active totals in their established order", () => {
    const input = selection();
    input.monthTotals.clear();
    expect(selectMonthlyCollaboratorRows(input)).toEqual([collaborator]);
    input.filters.km = true;
    input.filters.trasferta = true;
    input.monthTotals.set(collaborator.id, {
      km: 0,
      get trasferta(): number { throw new Error("Travel must not be evaluated after KM excludes the row"); },
      straordinario: 1,
      reperibilita: 1,
    });
    expect(selectMonthlyCollaboratorRows(input)).toEqual([]);
  });

  test("sorts a fresh result while retaining input order, references and totals", () => {
    const input = selection();
    const second = { ...collaborator, id: "collaborator-2", name: "ZETA" };
    input.collaborators = [second, collaborator];
    input.presentIds.add(second.id);
    const totals = input.monthTotals.get(collaborator.id)!;
    input.monthTotals.set(second.id, totals);
    const result = selectMonthlyCollaboratorRows(input);
    expect(result).toEqual([collaborator, second]);
    expect(input.collaborators).toEqual([second, collaborator]);
    expect(result[0]).toBe(collaborator);
    expect(input.monthTotals.get(collaborator.id)).toBe(totals);
    expect(totals).toEqual({ km: 1, trasferta: 1, straordinario: 1, reperibilita: 1 });
  });
});
