import { afterEach, beforeEach, expect, test, vi } from "vitest";

import { listRegenerationTargets, regenerateReminderItem } from "@/lib/ruolo-regeneration-api";

const fetchMock = vi.fn();

beforeEach(() => {
  fetchMock.mockReset();
  fetchMock.mockImplementation(async () => new Response(JSON.stringify({ items: [], excluded_drafts: 0 }), { status: 200, headers: { "content-type": "application/json" } }));
  vi.stubGlobal("fetch", fetchMock);
});

afterEach(() => vi.unstubAllGlobals());

test("lists every target or one batch and regenerates one sollecito with the chosen mode", async () => {
  await listRegenerationTargets("t", null);
  await listRegenerationTargets("t", "batch-1");
  await regenerateReminderItem("t", "item-1", "recompute");
  const [all, batch, regenerate] = fetchMock.mock.calls as [string, RequestInit][];
  expect(all[0]).toMatch(/\/ruolo\/tributi\/solleciti\/regeneration-targets$/);
  expect(batch[0]).toMatch(/regeneration-targets\?batch_id=batch-1$/);
  expect(regenerate[0]).toMatch(/\/ruolo\/tributi\/solleciti\/items\/item-1\/regenerate$/);
  expect(regenerate[1]).toMatchObject({ method: "POST", body: JSON.stringify({ mode: "recompute" }) });
  expect(regenerate[1].headers).toMatchObject({ Authorization: "Bearer t" });
});
