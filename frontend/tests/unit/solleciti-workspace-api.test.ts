import { beforeEach, expect, it, vi } from "vitest";
const api = vi.hoisted(() => ({ request: vi.fn() }));
vi.mock("@/lib/api", () => api);
import { generateSolleciti, getSollecitiWorkspace, prepareSolleciti, reconcileSollecitiAccount } from "@/lib/ruolo-solleciti-workspace-api";

beforeEach(() => api.request.mockReset());

it("sends server filters, pagination and authenticated non-cached reads", async () => {
  await getSollecitiWorkspace("t", { q: "Rossi & figli", year: "2021", account: "2", stage: "sent", page: 2 });
  const [path, options] = api.request.mock.calls[0];
  const url = new URL(path, "http://test.local");
  expect(Object.fromEntries(url.searchParams)).toEqual({ q: "Rossi & figli", year: "2021", account: "2", stage: "sent", page: "2", page_size: "20" });
  expect(options).toEqual({ headers: { Authorization: "Bearer t" }, cache: "no-store" });
  await getSollecitiWorkspace("t", { q: "", year: "", account: "all", stage: "all", page: 1 });
  expect(api.request.mock.calls[1][0]).not.toContain("year=");
});

it("keeps PDF generation and preparation as distinct POST commands", async () => {
  await generateSolleciti("t", 2021, "12345678901");
  expect(api.request).toHaveBeenLastCalledWith("/ruolo/tributi/solleciti/workspace/generate", { method: "POST", headers: { Authorization: "Bearer t" }, body: JSON.stringify({ year: 2021, tax_code: "12345678901" }) });
  await prepareSolleciti("t", ["i1"], 2);
  expect(api.request).toHaveBeenLastCalledWith("/ruolo/tributi/solleciti/workspace/prepare", { method: "POST", headers: { Authorization: "Bearer t" }, body: JSON.stringify({ item_ids: ["i1"], credential_id: 2 }) });
  await reconcileSollecitiAccount("t", 2, null);
  expect(api.request).toHaveBeenLastCalledWith("/ruolo/tributi/solleciti/workspace/reconcile", { method: "POST", headers: { Authorization: "Bearer t" }, body: JSON.stringify({ credential_id: 2, year: null }) });
});
