import { beforeEach, expect, it, vi } from "vitest";

const api = vi.hoisted(() => ({ request: vi.fn() }));
vi.mock("@/lib/api", () => api);

import { generateYearNotices, getYearStatus } from "@/lib/ruolo-year-notices-api";

beforeEach(() => api.request.mockReset());

it("reads the year status and makes the missing notices of the year", async () => {
  api.request.mockResolvedValue({});
  await getYearStatus("t", 2021);
  await generateYearNotices("t", 2021, ["a1", "a2"]);
  expect(api.request.mock.calls).toEqual([
    ["/ruolo/tributi/solleciti/years/2021/status", { headers: { Authorization: "Bearer t" } }],
    ["/ruolo/tributi/solleciti/years/2021/generate", { method: "POST", headers: { Authorization: "Bearer t" }, body: JSON.stringify({ avviso_ids: ["a1", "a2"] }) }],
  ]);
});
