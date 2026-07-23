import { afterEach, describe, expect, test, vi } from "vitest";

import {
  catastoCreateElaborazioneMassivaDistrettoExportJob,
  catastoDownloadElaborazioneMassivaDistrettoExportJob,
  catastoGetElaborazioneMassivaDistrettoExportJob,
  catastoListElaborazioneMassivaDistrettoExportJobs,
} from "@/lib/api/catasto-distretto-export-jobs";

const jobPayload = {
  id: "export-1",
  created_at: "2026-07-16T10:00:00Z",
  started_at: null,
  completed_at: null,
  num_distretto: "01",
  nome_distretto: "Sinis Nord Est",
  format: "csv",
  status: "pending",
  total_rows: 0,
  processed_rows: 0,
  current_label: "Export in coda",
  error_message: null,
  output_filename: null,
  download_url: null,
};

describe("Catasto distretto export jobs API client", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  test("creates, lists, reads and downloads district export jobs", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify(jobPayload), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ items: [jobPayload] }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ items: [] }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify(jobPayload), { status: 200 }))
      .mockResolvedValueOnce(new Response(new Blob(["csv"], { type: "text/csv" }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(catastoCreateElaborazioneMassivaDistrettoExportJob("token", "01", "csv")).resolves.toEqual(jobPayload);
    await expect(catastoListElaborazioneMassivaDistrettoExportJobs("token", { limit: 5 })).resolves.toEqual({ items: [jobPayload] });
    await expect(catastoListElaborazioneMassivaDistrettoExportJobs("token")).resolves.toEqual({ items: [] });
    await expect(catastoGetElaborazioneMassivaDistrettoExportJob("token", "export-1")).resolves.toEqual(jobPayload);
    await expect(catastoDownloadElaborazioneMassivaDistrettoExportJob("token", "export-1")).resolves.toBeInstanceOf(Blob);

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      "/api/catasto/elaborazioni-massive/particelle/distretti/01/exports?format=csv",
      expect.objectContaining({ method: "POST" }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      "/api/catasto/elaborazioni-massive/particelle/distretti/exports?limit=5",
      expect.anything(),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      3,
      "/api/catasto/elaborazioni-massive/particelle/distretti/exports",
      expect.anything(),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      4,
      "/api/catasto/elaborazioni-massive/particelle/distretti/exports/export-1",
      expect.anything(),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      5,
      "/api/catasto/elaborazioni-massive/particelle/distretti/exports/export-1/download",
      expect.anything(),
    );
  });
});
