import { afterEach, describe, expect, test, vi } from "vitest";

import { catastoDownloadDistrettoParticelleExport } from "@/lib/api/catasto-distretti-export";

describe("Catasto distretti export API client", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  test("downloads district parcel export as a blob", async () => {
    const blob = new Blob(["csv"], { type: "text/csv" });
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(blob, {
        status: 200,
        headers: { "content-type": "text/csv" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(
      catastoDownloadDistrettoParticelleExport("token", "distretto-1", "csv"),
    ).resolves.toBeInstanceOf(Blob);

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/catasto/distretti/distretto-1/particelle/export?format=csv",
      expect.objectContaining({
        headers: expect.objectContaining({ Authorization: "Bearer token" }),
      }),
    );
  });
});
