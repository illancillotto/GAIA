import { afterEach, describe, expect, test, vi } from "vitest";

import { catastoGisGetWhiteCompanyReportLayer } from "@/lib/api/catasto";

describe("Catasto GIS WhiteCompany API client", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  test("loads the WhiteCompany report layer with date, type and operator filters", async () => {
    const payload = {
      generated_at: "2026-07-15T08:00:00",
      tipologie: ["Perdita condotta"],
      operatori: ["Mario Rossi"],
      stats: { total: 1, mapped: 1, unmapped: 0, truncated: false },
      geojson: { type: "FeatureCollection", features: [] },
    };
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(payload), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(
      catastoGisGetWhiteCompanyReportLayer("token", {
        dateFrom: " 2026-07-01 ",
        dateTo: "2026-07-31",
        tipologia: "Perdita condotta",
        operatore: "Mario Rossi",
        limit: 250,
      }),
    ).resolves.toEqual(payload);

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/catasto/gis/whitecompany-reports/layer?date_from=2026-07-01&date_to=2026-07-31&tipologia=Perdita+condotta&operatore=Mario+Rossi&limit=250",
      expect.objectContaining({
        headers: expect.objectContaining({ Authorization: "Bearer token" }),
      }),
    );
  });
});
