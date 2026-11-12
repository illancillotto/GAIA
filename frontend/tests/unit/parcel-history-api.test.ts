import { beforeEach, expect, test, vi } from "vitest";
import { parcelHistoryRequest } from "@/lib/parcel-history-api";

vi.mock("@/lib/api", () => ({ getApiBaseUrl: () => "/api" }));
beforeEach(() => vi.stubGlobal("fetch", vi.fn()));

test("private history GET carries authentication without cache or writes", async () => {
  vi.mocked(fetch).mockResolvedValue(new Response(JSON.stringify({ items: [] }), { status: 200 }));
  expect(await parcelHistoryRequest("token", "?foglio=1")).toEqual({ items: [] });
  expect(fetch).toHaveBeenCalledWith("/api/ruolo/particelle/storia?foglio=1", { headers: { Authorization: "Bearer token" }, cache: "no-store" });
});
test.each([[404, "non è disponibile"], [401, "Sessione scaduta"], [403, "permessi"], [500, "Impossibile caricare"]])("HTTP %s has an actionable error", async (status, message) => {
  vi.mocked(fetch).mockResolvedValue(new Response("error", { status }));
  await expect(parcelHistoryRequest("token", "/parcel")).rejects.toThrow(String(message));
});
