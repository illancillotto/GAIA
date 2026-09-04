import { describe, expect, test } from "vitest";

import {
  collapseRunningOperationsByArea,
  dashboardHasActivePollingTargets,
  MAX_RUNNING_OPERATIONS_PER_AREA,
} from "@/lib/elaborazioni-dashboard-overview";

describe("elaborazioni dashboard overview helpers", () => {
  const idleSnapshot = {
    batchStatuses: ["completed", "failed"],
    particelleStatuses: ["succeeded"],
    incassStatuses: ["succeeded", "cancelled"],
    bonificaStatuses: ["idle"],
    postaOnlineStatuses: ["failed"],
    autodocStatus: null as string | null | undefined,
    gateMobileStatus: undefined as string | null | undefined,
  };

  test.each([
    ["batchStatuses", { batchStatuses: ["processing"] }],
    ["particelleStatuses", { particelleStatuses: ["queued_resume"] }],
    ["incassStatuses", { incassStatuses: ["pending"] }],
    ["bonificaStatuses", { bonificaStatuses: ["running"] }],
    ["postaOnlineStatuses", { postaOnlineStatuses: ["processing"] }],
    ["autodoc queued", { autodocStatus: "queued" }],
    ["autodoc running", { autodocStatus: "running" }],
    ["gate mobile", { gateMobileStatus: "running" }],
  ] as const)("keeps polling active for %s", (_label, override) => {
    expect(dashboardHasActivePollingTargets({ ...idleSnapshot, ...override })).toBe(true);
  });

  test("stops polling when every family is idle", () => {
    expect(dashboardHasActivePollingTargets(idleSnapshot)).toBe(false);
  });

  test("shows at most three operations of the same area and keeps a sample for overflow", () => {
    const operations = Array.from({ length: 5 }, (_, index) => ({
      area: "Capacitas inCass",
      id: index + 1,
    }));

    const collapsed = collapseRunningOperationsByArea(operations);

    expect(MAX_RUNNING_OPERATIONS_PER_AREA).toBe(3);
    expect(collapsed.totalCount).toBe(5);
    expect(collapsed.items.map((item) => item.id)).toEqual([1, 2, 3]);
    expect(collapsed.hiddenByArea).toEqual([
      { area: "Capacitas inCass", hiddenCount: 2, sample: operations[0] },
    ]);
  });

  test("collapses each area independently and keeps short lists intact", () => {
    const operations = [
      { area: "Capacitas inCass", id: "a1" },
      { area: "Batch runtime", id: "b1" },
      { area: "Capacitas inCass", id: "a2" },
      { area: "Capacitas inCass", id: "a3" },
      { area: "Batch runtime", id: "b2" },
      { area: "Capacitas inCass", id: "a4" },
    ];

    const collapsed = collapseRunningOperationsByArea(operations, 2);

    expect(collapsed.items.map((item) => item.id)).toEqual(["a1", "b1", "a2", "b2"]);
    expect(collapsed.hiddenByArea).toEqual([
      { area: "Capacitas inCass", hiddenCount: 2, sample: operations[0] },
    ]);
    expect(collapseRunningOperationsByArea(operations.slice(0, 2)).hiddenByArea).toEqual([]);
  });
});
