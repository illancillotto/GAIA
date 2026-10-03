import { beforeEach, describe, expect, test, vi } from "vitest";
import { dotazioniApi } from "@/features/dotazioni/api";

const mocks = vi.hoisted(() => ({ token: vi.fn() }));
vi.mock("@/lib/api", () => ({ getApiBaseUrl: () => "https://gaia.test/api" }));
vi.mock("@/lib/auth", () => ({ getStoredAccessToken: mocks.token }));

describe("Dotazioni REST client", () => {
  beforeEach(() => {
    mocks.token.mockReturnValue("token");
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => ({ items: [] }) }));
  });
  test("uses encoded identifiers and canonical endpoints", async () => {
    await dotazioniApi.list(new URLSearchParams({ search: "telefono" }));
    await dotazioniApi.asset("asset/id");
    await dotazioniApi.byCode("TEL/01");
    await dotazioniApi.create({ asset_code: "TEL-01", asset_type: "phone", name: "Telefono" });
    await dotazioniApi.update("asset/id", { name: "Nuovo" });
    await dotazioniApi.history("asset/id", 2);
    await dotazioniApi.custody("asset/id", "transfer", { holder_user_id: 7 });
    await dotazioniApi.operatorAssets(7);
    await dotazioniApi.lookups();
    expect(vi.mocked(fetch).mock.calls.map(([url]) => url)).toEqual([
      "https://gaia.test/api/dotazioni/assets?search=telefono",
      "https://gaia.test/api/dotazioni/assets/asset%2Fid",
      "https://gaia.test/api/dotazioni/assets/by-code/TEL%2F01",
      "https://gaia.test/api/dotazioni/assets",
      "https://gaia.test/api/dotazioni/assets/asset%2Fid",
      "https://gaia.test/api/dotazioni/assets/asset%2Fid/custody-history?page=2&page_size=25",
      "https://gaia.test/api/dotazioni/assets/asset%2Fid/transfer",
      "https://gaia.test/api/dotazioni/operators/7/assets?page=1&page_size=100",
      "https://gaia.test/api/dotazioni/lookups",
    ]);
    expect(fetch).toHaveBeenNthCalledWith(4, expect.any(String), expect.objectContaining({ method: "POST", body: JSON.stringify({ asset_code: "TEL-01", asset_type: "phone", name: "Telefono" }), headers: { "Content-Type": "application/json", Authorization: "Bearer token" } }));
    expect(fetch).toHaveBeenNthCalledWith(5, expect.any(String), expect.objectContaining({ method: "PATCH" }));
  });
  test("does not send an authorization header without a stored token", async () => {
    mocks.token.mockReturnValue(null);
    await dotazioniApi.asset("1");
    expect(fetch).toHaveBeenCalledWith(expect.any(String), expect.objectContaining({ headers: { "Content-Type": "application/json" }, body: undefined, cache: "no-store" }));
  });
  test.each([
    [async () => ({ detail: "Asset già in custodia" }), "Asset già in custodia"],
    [async () => ({ detail: [{ msg: "invalid" }] }), "Operazione non riuscita (409)"],
    [async () => { throw new Error("invalid JSON"); }, "Operazione non riuscita (409)"],
  ])("reports API errors safely", async (json, message) => {
    vi.mocked(fetch).mockResolvedValue({ ok: false, status: 409, json } as Response);
    await expect(dotazioniApi.asset("1")).rejects.toThrow(message);
  });
});
