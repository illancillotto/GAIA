import { describe, expect, test, vi } from "vitest";

import { buildAssignmentPayload, isInvalidSectorParent, nextChildUnitType, resolveManagerUserIds, syncDirectReportManagers } from "@/features/organigramma/organigramma-assignment";
import type { OrgAssignment, OrgUnitType } from "@/types/api";

const unit = { id: "reparto-1", tipo: "reparto" } as const;

describe("organigramma assignments", () => {
  test("builds normalized lead and member payloads", () => {
    expect(buildAssignmentPayload({ userId: 10, unit, mode: "lead", unitLeadUserId: null, parentLeadUserId: 5 })).toMatchObject({
      manager_user_id: 5, title: "Capo reparto", position_code: "capo_reparto", is_primary: true,
    });
    expect(buildAssignmentPayload({ userId: 11, unit, mode: "member", unitLeadUserId: 10, parentLeadUserId: 5 })).toMatchObject({
      manager_user_id: 10, title: null, position_code: "collaboratore", is_primary: false,
    });
  });

  test("resolves current and parent unit leads", () => {
    const leads = new Map([
      ["parent", { lead: { user_id: 5 } }],
      ["child", { lead: { user_id: 10 } }],
    ]);
    expect(resolveManagerUserIds({ id: "child", parent_id: "parent" }, leads)).toEqual({
      unitLeadUserId: 10,
      parentLeadUserId: 5,
    });
    expect(resolveManagerUserIds({ id: "root", parent_id: null }, leads)).toEqual({
      unitLeadUserId: null,
      parentLeadUserId: null,
    });
    expect(resolveManagerUserIds({ id: "orphan", parent_id: "missing" }, leads)).toEqual({
      unitLeadUserId: null,
      parentLeadUserId: null,
    });
  });

  test("updates only direct reports when a lead is assigned", async () => {
    const update = vi.fn().mockResolvedValue(undefined);
    const assignments = [
      { id: "a", user_id: 1, org_unit_id: "reparto-1" },
      { id: "b", user_id: 10, org_unit_id: "reparto-1" },
      { id: "c", user_id: 2, org_unit_id: "other" },
    ] as OrgAssignment[];
    await syncDirectReportManagers("lead", assignments, "reparto-1", 10, update);
    expect(update).toHaveBeenCalledTimes(1);
    expect(update).toHaveBeenCalledWith("a");
    update.mockClear();
    await syncDirectReportManagers("member", assignments, "reparto-1", 10, update);
    expect(update).not.toHaveBeenCalled();
  });

  test("maps child unit types and rejects invalid sector parents", () => {
    const types: (OrgUnitType | undefined)[] = ["direzione", "distretto", "settore", "reparto", "squadra", undefined];
    expect(types.map(nextChildUnitType)).toEqual(["distretto", "settore", "reparto", "squadra", "settore", "settore"]);
    expect(isInvalidSectorParent("settore", "reparto")).toBe(true);
    expect(isInvalidSectorParent("settore", "squadra")).toBe(true);
    expect(isInvalidSectorParent("settore", "direzione")).toBe(false);
    expect(isInvalidSectorParent("reparto", "squadra")).toBe(false);
  });
});
