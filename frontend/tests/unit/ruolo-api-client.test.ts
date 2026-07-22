import { afterEach, describe, expect, test, vi } from "vitest";

import {
  addTributiNote,
  buildExportCsvUrl,
  buildRuoloCapacitasCheckExportUrl,
  buildRuoloGaiaCalculationExportUrl,
  createTributiReminderBatch,
  createTributiPayment,
  createTributiReminder,
  downloadTributiReminderDocument,
  getTributiReminderBatch,
  formatRuoloCapacitasCheckStatus,
  getAvvisiBySubject,
  getAvviso,
  getImportJob,
  getRuoloCapacitasCalculationDetail,
  getRuoloCapacitasCheck,
  getRuoloCapacitasCheckComuni,
  getRuoloCapacitasCheckStatusBadgeClassName,
  getRuoloGaiaCalculation,
  getRuoloParticelleSummary,
  getRuoloStats,
  getRuoloStatsAnalytics,
  getRuoloStatsComuni,
  getTributiAvviso,
  listAvvisi,
  listImportJobs,
  listRuoloParticelle,
  listTributiAvvisi,
  listTributiReminderBatches,
  listTributiReminderCandidates,
  listTributiReminders,
  updateTributiAvvisoStatus,
} from "@/lib/ruolo-api";

function jsonResponse(payload: unknown = {}): Response {
  return new Response(JSON.stringify(payload), {
    status: 200,
    headers: { "content-type": "application/json" },
  });
}

describe("Ruolo API client", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  test("formats Capacitas status labels and badge classes", () => {
    expect(formatRuoloCapacitasCheckStatus("amount_mismatch")).toBe("Importi non allineati");
    expect(formatRuoloCapacitasCheckStatus("only_in_ruolo")).toBe("Presente solo nel ruolo");
    expect(formatRuoloCapacitasCheckStatus("only_in_capacitas")).toBe("Presente solo in Capacitas");
    expect(formatRuoloCapacitasCheckStatus("matched")).toBe("Allineato");
    expect(formatRuoloCapacitasCheckStatus("custom" as never)).toBe("custom");

    expect(getRuoloCapacitasCheckStatusBadgeClassName("amount_mismatch")).toContain("amber");
    expect(getRuoloCapacitasCheckStatusBadgeClassName("only_in_ruolo")).toContain("sky");
    expect(getRuoloCapacitasCheckStatusBadgeClassName("only_in_capacitas")).toContain("fuchsia");
    expect(getRuoloCapacitasCheckStatusBadgeClassName("matched")).toContain("emerald");
    expect(getRuoloCapacitasCheckStatusBadgeClassName("custom" as never)).toContain("gray");
  });

  test("builds export URLs with optional filters", () => {
    expect(
      buildExportCsvUrl({
        anno: 2024,
        subject_id: "subject-1",
        q: "Rossi",
        codice_fiscale: "RSSMRA80A01H501Z",
        comune: "Oristano",
        codice_utenza: "UT-1",
        unlinked: true,
      }),
    ).toBe(
      "/api/ruolo/avvisi/export?anno=2024&subject_id=subject-1&q=Rossi&codice_fiscale=RSSMRA80A01H501Z&comune=Oristano&codice_utenza=UT-1&unlinked=true",
    );
    expect(buildExportCsvUrl({})).toBe("/api/ruolo/avvisi/export?");

    expect(buildRuoloGaiaCalculationExportUrl(2025, {
      limit: 50,
      taxCode: "RSSMRA80A01H501Z",
      anomalousOnly: true,
    })).toBe(
      "/api/ruolo/stats/calcolo-gaia/export?anno=2025&limit=50&tax_code=RSSMRA80A01H501Z&anomalous_only=true",
    );
    expect(buildRuoloGaiaCalculationExportUrl(2025)).toBe("/api/ruolo/stats/calcolo-gaia/export?anno=2025&limit=100000");
    expect(buildRuoloCapacitasCheckExportUrl(2025, 0.5)).toBe("/api/ruolo/stats/capacitas-check/export?anno=2025&min_delta=0.5");
    expect(buildRuoloCapacitasCheckExportUrl(2025)).toBe("/api/ruolo/stats/capacitas-check/export?anno=2025&min_delta=0.01");
  });

  test("calls ruolo read endpoints with query parameters", async () => {
    const fetchMock = vi.fn().mockImplementation(() => Promise.resolve(jsonResponse({ items: [] })));
    vi.stubGlobal("fetch", fetchMock);

    await listImportJobs("token", 2024, 2, 10);
    await listImportJobs("token");
    await getImportJob("token", "job-1");
    await listAvvisi("token", {
      anno: 2024,
      subject_id: "subject-1",
      q: "Rossi",
      codice_fiscale: "RSSMRA80A01H501Z",
      comune: "Oristano",
      codice_utenza: "UT-1",
      unlinked: true,
      page: 3,
      page_size: 15,
    });
    await listAvvisi("token");
    await getAvviso("token", "avviso-1");
    await getAvvisiBySubject("token", "subject-1");
    await listRuoloParticelle("token", {
      anno: 2024,
      foglio: "1",
      particella: "2",
      comune: "Oristano",
      match_status: "matched",
      match_reason: "cf",
      unmatched_only: true,
      page: 2,
      page_size: 5,
    });
    await listRuoloParticelle("token");

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      "/api/ruolo/import/jobs?page=2&page_size=10&anno=2024",
      expect.objectContaining({ headers: expect.objectContaining({ Authorization: "Bearer token" }) }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(2, "/api/ruolo/import/jobs?page=1&page_size=20", expect.any(Object));
    expect(fetchMock).toHaveBeenNthCalledWith(3, "/api/ruolo/import/jobs/job-1", expect.any(Object));
    expect(fetchMock).toHaveBeenNthCalledWith(
      4,
      "/api/ruolo/avvisi?anno=2024&subject_id=subject-1&q=Rossi&codice_fiscale=RSSMRA80A01H501Z&comune=Oristano&codice_utenza=UT-1&unlinked=true&page=3&page_size=15",
      expect.any(Object),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(5, "/api/ruolo/avvisi?page=1&page_size=20", expect.any(Object));
    expect(fetchMock).toHaveBeenNthCalledWith(6, "/api/ruolo/avvisi/avviso-1", expect.any(Object));
    expect(fetchMock).toHaveBeenNthCalledWith(7, "/api/ruolo/soggetti/subject-1/avvisi", expect.any(Object));
    expect(fetchMock).toHaveBeenNthCalledWith(
      8,
      "/api/ruolo/particelle?anno=2024&foglio=1&particella=2&comune=Oristano&match_status=matched&match_reason=cf&unmatched_only=true&page=2&page_size=5",
      expect.any(Object),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(9, "/api/ruolo/particelle?page=1&page_size=50", expect.any(Object));
  });

  test("calls tributi endpoints", async () => {
    const fetchMock = vi.fn().mockImplementation(() => Promise.resolve(jsonResponse({ items: [] })));
    vi.stubGlobal("fetch", fetchMock);

    await listTributiAvvisi("token", {
      anno: 2024,
      subject_id: "subject-1",
      q: "Rossi",
      codice_fiscale: "RSSMRA80A01H501Z",
      comune: "Oristano",
      codice_utenza: "UT-1",
      unlinked: true,
      payment_status: "partial",
      workflow_status: "moroso",
      open_only: true,
      page: 2,
      page_size: 30,
    });
    await listTributiAvvisi("token");
    await getTributiAvviso("token", "avviso-1");
    await createTributiPayment("token", "avviso-1", { amount: 10 });
    await updateTributiAvvisoStatus("token", "avviso-1", { workflow_status: "moroso" });
    await addTributiNote("token", "avviso-1", { body: "Nota", visibility: "internal" });
    await listTributiReminders("token", "avviso-1");
    await createTributiReminder("token", "avviso-1", { notes: "Sollecito" });
    await createTributiReminder("token", "avviso-1");
    await listTributiReminderCandidates("token", {
      anno_from: 2022,
      anno_to: 2023,
      q: "Rossi",
      comune: "Uras",
      codice_fiscale: ["RSSMRA80A01H501Z", "BNCLGU80A01H501Y"],
      page: 2,
      page_size: 10,
    });
    await listTributiReminderCandidates("token");
    await createTributiReminderBatch("token", {
      title: "Batch",
      codice_fiscale: ["RSSMRA80A01H501Z"],
      filters: { anno_from: 2022 },
      template_path: "/tmp/template.docx",
      notes: "note",
    });
    await listTributiReminderBatches("token", 3, 5);
    await getTributiReminderBatch("token", "batch-1");

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      "/api/ruolo/tributi/avvisi?anno=2024&subject_id=subject-1&q=Rossi&codice_fiscale=RSSMRA80A01H501Z&comune=Oristano&codice_utenza=UT-1&unlinked=true&payment_status=partial&workflow_status=moroso&open_only=true&page=2&page_size=30",
      expect.any(Object),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(2, "/api/ruolo/tributi/avvisi?page=1&page_size=20", expect.any(Object));
    expect(fetchMock).toHaveBeenNthCalledWith(3, "/api/ruolo/tributi/avvisi/avviso-1", expect.any(Object));
    expect(fetchMock).toHaveBeenNthCalledWith(
      4,
      "/api/ruolo/tributi/avvisi/avviso-1/payments",
      expect.objectContaining({ method: "POST", body: JSON.stringify({ amount: 10 }) }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      5,
      "/api/ruolo/tributi/avvisi/avviso-1/status",
      expect.objectContaining({ method: "PATCH", body: JSON.stringify({ workflow_status: "moroso" }) }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      6,
      "/api/ruolo/tributi/avvisi/avviso-1/notes",
      expect.objectContaining({ method: "POST", body: JSON.stringify({ body: "Nota", visibility: "internal" }) }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(7, "/api/ruolo/tributi/avvisi/avviso-1/reminders", expect.any(Object));
    expect(fetchMock).toHaveBeenNthCalledWith(
      8,
      "/api/ruolo/tributi/avvisi/avviso-1/reminders",
      expect.objectContaining({ method: "POST", body: JSON.stringify({ notes: "Sollecito" }) }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      9,
      "/api/ruolo/tributi/avvisi/avviso-1/reminders",
      expect.objectContaining({ method: "POST", body: JSON.stringify({}) }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      10,
      "/api/ruolo/tributi/solleciti/candidates?anno_from=2022&anno_to=2023&q=Rossi&comune=Uras&codice_fiscale=RSSMRA80A01H501Z&codice_fiscale=BNCLGU80A01H501Y&page=2&page_size=10",
      expect.any(Object),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(11, "/api/ruolo/tributi/solleciti/candidates?page=1&page_size=50", expect.any(Object));
    expect(fetchMock).toHaveBeenNthCalledWith(
      12,
      "/api/ruolo/tributi/solleciti/batches",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          title: "Batch",
          codice_fiscale: ["RSSMRA80A01H501Z"],
          filters: { anno_from: 2022 },
          template_path: "/tmp/template.docx",
          notes: "note",
        }),
      }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(13, "/api/ruolo/tributi/solleciti/batches?page=3&page_size=5", expect.any(Object));
    expect(fetchMock).toHaveBeenNthCalledWith(14, "/api/ruolo/tributi/solleciti/batches/batch-1", expect.any(Object));
  });

  test("calls stats endpoints with default and explicit options", async () => {
    const fetchMock = vi.fn().mockImplementation(() => Promise.resolve(jsonResponse({ items: [] })));
    vi.stubGlobal("fetch", fetchMock);

    await getRuoloStats("token", 2024);
    await getRuoloStats("token");
    await getRuoloParticelleSummary("token", 2024);
    await getRuoloParticelleSummary("token");
    await getRuoloStatsComuni("token", 2024);
    await getRuoloStatsAnalytics("token", 2024);
    await getRuoloCapacitasCheck("token", 2024, 0.5, 10);
    await getRuoloCapacitasCheck("token", 2024);
    await getRuoloCapacitasCheckComuni("token", 2024, 3);
    await getRuoloCapacitasCheckComuni("token", 2024);
    await getRuoloCapacitasCalculationDetail("token", 2024, "RSSMRA80A01H501Z");
    await getRuoloGaiaCalculation("token", 2024, {
      limit: 50,
      taxCode: "RSSMRA80A01H501Z",
      anomalousOnly: true,
    });
    await getRuoloGaiaCalculation("token", 2024);

    expect(fetchMock).toHaveBeenNthCalledWith(1, "/api/ruolo/stats?anno=2024", expect.any(Object));
    expect(fetchMock).toHaveBeenNthCalledWith(2, "/api/ruolo/stats?", expect.any(Object));
    expect(fetchMock).toHaveBeenNthCalledWith(3, "/api/ruolo/stats/particelle?anno=2024", expect.any(Object));
    expect(fetchMock).toHaveBeenNthCalledWith(4, "/api/ruolo/stats/particelle?", expect.any(Object));
    expect(fetchMock).toHaveBeenNthCalledWith(5, "/api/ruolo/stats/comuni?anno=2024", expect.any(Object));
    expect(fetchMock).toHaveBeenNthCalledWith(6, "/api/ruolo/stats/analytics?anno=2024", expect.any(Object));
    expect(fetchMock).toHaveBeenNthCalledWith(7, "/api/ruolo/stats/capacitas-check?anno=2024&min_delta=0.5&limit=10", expect.any(Object));
    expect(fetchMock).toHaveBeenNthCalledWith(8, "/api/ruolo/stats/capacitas-check?anno=2024&min_delta=0.01&limit=25", expect.any(Object));
    expect(fetchMock).toHaveBeenNthCalledWith(9, "/api/ruolo/stats/capacitas-check/comuni?anno=2024&limit=3", expect.any(Object));
    expect(fetchMock).toHaveBeenNthCalledWith(10, "/api/ruolo/stats/capacitas-check/comuni?anno=2024&limit=8", expect.any(Object));
    expect(fetchMock).toHaveBeenNthCalledWith(11, "/api/ruolo/stats/capacitas-check/detail?anno=2024&tax_code=RSSMRA80A01H501Z", expect.any(Object));
    expect(fetchMock).toHaveBeenNthCalledWith(12, "/api/ruolo/stats/calcolo-gaia?anno=2024&limit=50&tax_code=RSSMRA80A01H501Z&anomalous_only=true", expect.any(Object));
    expect(fetchMock).toHaveBeenNthCalledWith(13, "/api/ruolo/stats/calcolo-gaia?anno=2024&limit=100", expect.any(Object));
  });

  test("downloads reminder documents as blobs", async () => {
    const blob = new Blob(["docx"], { type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document" });
    const fetchMock = vi.fn().mockResolvedValue(new Response(blob, { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(downloadTributiReminderDocument("token", "/ruolo/tributi/reminders/reminder-1/download")).resolves.toBeInstanceOf(Blob);

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/ruolo/tributi/reminders/reminder-1/download",
      expect.objectContaining({ headers: { Authorization: "Bearer token" } }),
    );
  });

  test("raises ApiError with string, structured and fallback error details", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({ detail: "Accesso negato" }), { status: 403 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ detail: [{ msg: "Campo richiesto" }] }), { status: 422 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({}), { status: 404 }))
      .mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: "Errore server",
        json: vi.fn().mockRejectedValue(new Error("invalid json")),
      })
      .mockResolvedValueOnce({
        ok: false,
        status: 502,
        statusText: "",
        json: vi.fn().mockRejectedValue(new Error("invalid json")),
      });
    vi.stubGlobal("fetch", fetchMock);

    await expect(getAvviso("token", "blocked")).rejects.toMatchObject({
      message: "Accesso negato",
      status: 403,
    });
    await expect(getAvviso("token", "invalid")).rejects.toMatchObject({
      message: JSON.stringify([{ msg: "Campo richiesto" }]),
      status: 422,
    });
    await expect(downloadTributiReminderDocument("token", "/broken")).rejects.toMatchObject({
      message: "Request failed",
      status: 404,
    });
    await expect(downloadTributiReminderDocument("token", "/broken-json")).rejects.toMatchObject({
      message: "Errore server",
      status: 500,
    });
    await expect(downloadTributiReminderDocument("token", "/broken-empty")).rejects.toMatchObject({
      message: "Request failed",
      status: 502,
    });
  });
});
