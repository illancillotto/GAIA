import { beforeEach, expect, it, vi } from "vitest";

const api = vi.hoisted(() => ({ request: vi.fn() }));
vi.mock("@/lib/api", () => api);

import { getBatchOverview } from "@/lib/ruolo-batch-overview-api";

beforeEach(() => api.request.mockReset());

it("asks the summary of several batches at once", async () => {
  api.request.mockResolvedValue([]);
  await getBatchOverview("t", ["b1", "b2"]);
  expect(api.request).toHaveBeenCalledWith("/ruolo/tributi/solleciti/batch-overview?batch_id=b1&batch_id=b2", { headers: { Authorization: "Bearer t" } });
});
