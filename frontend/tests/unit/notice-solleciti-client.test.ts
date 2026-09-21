import { afterEach, expect, it, vi } from "vitest";
import { confirmTributiReminderBatch } from "@/components/ruolo/solleciti/client";

afterEach(() => vi.unstubAllGlobals());

it("sends the explicit batch command with authentication", async () => {
  const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ id: "approved" }), { status: 200 }));
  vi.stubGlobal("fetch", fetchMock);
  await expect(confirmTributiReminderBatch("token", "batch-1")).resolves.toEqual({ id: "approved" });
  expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("/batches/batch-1/confirm"), expect.objectContaining({
    method: "POST", body: JSON.stringify({ batch: true }), headers: expect.objectContaining({ Authorization: "Bearer token" }),
  }));
});

it("propagates a stale generation conflict", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: "Revisione obsoleta" }), { status: 409 })));
  await expect(confirmTributiReminderBatch("token", "batch-1")).rejects.toThrow("Revisione obsoleta");
});
