import { afterEach, describe, expect, test, vi } from "vitest";

import { ApiError } from "@/lib/api";
import {
  advanceRiordinoStep,
  checkRiordinoDeadlines,
  closeRiordinoIssue,
  completeRiordinoBlockSisterVisura,
  completeRiordinoPhase,
  createRiordinoAppeal,
  createRiordinoBlock,
  createRiordinoBlockPhase2Practice,
  createRiordinoDocumentType,
  createRiordinoGisLink,
  createRiordinoIssue,
  createRiordinoIssueType,
  deleteRiordinoDocument,
  deleteRiordinoDocumentType,
  deleteRiordinoIssueType,
  downloadRiordinoDocument,
  downloadRiordinoPracticeDossier,
  downloadRiordinoPracticeSummary,
  exportRiordinoBlockSummary,
  getRiordinoBlock,
  getRiordinoBlockCoordinatorSummary,
  getRiordinoBlockWizard,
  getRiordinoDashboard,
  getRiordinoPractice,
  listRiordinoAppeals,
  listRiordinoBlocks,
  listRiordinoDocumentTypes,
  listRiordinoDocuments,
  listRiordinoEvents,
  listRiordinoGisLinks,
  listRiordinoIssueTypes,
  listRiordinoIssues,
  listRiordinoMunicipalities,
  listRiordinoNotifications,
  listRiordinoParcels,
  listRiordinoPractices,
  markRiordinoNotificationRead,
  previewRiordinoBlockSelection,
  reopenRiordinoStep,
  requestRiordinoBlockSisterVisura,
  resolveRiordinoAppeal,
  reviewRiordinoBlockParcel,
  skipRiordinoStep,
  startRiordinoPhase,
  syncRiordinoBlockSisterVisura,
  syncRiordinoBlockSisterVisure,
  updateRiordinoDocumentType,
  updateRiordinoGisLink,
  updateRiordinoIssueType,
  uploadRiordinoDocument,
} from "@/lib/riordino-api";

function jsonResponse(payload: unknown = {}, status = 200): Response {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "content-type": "application/json" },
  });
}

describe("Riordino API client", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  test("calls read endpoints with query parameters", async () => {
    const fetchMock = vi.fn().mockImplementation(() => Promise.resolve(jsonResponse({ items: [] })));
    vi.stubGlobal("fetch", fetchMock);

    await getRiordinoDashboard("token");
    await previewRiordinoBlockSelection("token", { parcel_ids: ["p-1"] });
    await listRiordinoBlocks("token", { status: "open", coordinator: "mrossi", page: "2", per_page: "10" });
    await listRiordinoBlocks("token");
    await getRiordinoBlock("token", "block-1");
    await getRiordinoBlockWizard("token", "block-1");
    await getRiordinoBlockCoordinatorSummary("token", "block-1");
    await listRiordinoPractices("token", {
      status: "open",
      municipality: "Oristano",
      phase: "phase-1",
      owner: "mrossi",
      page: "1",
      per_page: "20",
    });
    await listRiordinoPractices("token");
    await getRiordinoPractice("token", "practice-1");
    await listRiordinoEvents("token", "practice-1");
    await listRiordinoAppeals("token", "practice-1", "open");
    await listRiordinoAppeals("token", "practice-1");
    await listRiordinoIssues("token", "practice-1", {
      severity: "high",
      status_filter: "open",
      category: "cadastral",
    });
    await listRiordinoIssues("token", "practice-1");
    await listRiordinoDocuments("token", "practice-1", {
      phase_id: "phase-1",
      step_id: "step-1",
      document_type: "visura",
      appeal_id: "appeal-1",
    });
    await listRiordinoDocuments("token", "practice-1");
    await listRiordinoGisLinks("token", "practice-1");
    await listRiordinoParcels("token", "practice-1");
    await listRiordinoNotifications("token");
    await listRiordinoDocumentTypes("token");
    await listRiordinoIssueTypes("token");
    await listRiordinoMunicipalities("token");

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      "/api/api/riordino/dashboard",
      expect.objectContaining({ headers: expect.objectContaining({ Authorization: "Bearer token" }) }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      "/api/api/riordino/blocks/preview",
      expect.objectContaining({ method: "POST" }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      3,
      "/api/api/riordino/blocks?status=open&coordinator=mrossi&page=2&per_page=10",
      expect.any(Object),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(4, "/api/api/riordino/blocks", expect.any(Object));
    expect(fetchMock).toHaveBeenNthCalledWith(5, "/api/api/riordino/blocks/block-1", expect.any(Object));
    expect(fetchMock).toHaveBeenNthCalledWith(6, "/api/api/riordino/blocks/block-1/wizard", expect.any(Object));
    expect(fetchMock).toHaveBeenNthCalledWith(7, "/api/api/riordino/blocks/block-1/coordinator-summary", expect.any(Object));
    expect(fetchMock).toHaveBeenNthCalledWith(
      8,
      "/api/api/riordino/practices?status=open&municipality=Oristano&phase=phase-1&owner=mrossi&page=1&per_page=20",
      expect.any(Object),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(9, "/api/api/riordino/practices", expect.any(Object));
    expect(fetchMock).toHaveBeenNthCalledWith(10, "/api/api/riordino/practices/practice-1", expect.any(Object));
    expect(fetchMock).toHaveBeenNthCalledWith(11, "/api/api/riordino/practices/practice-1/events", expect.any(Object));
    expect(fetchMock).toHaveBeenNthCalledWith(12, "/api/api/riordino/practices/practice-1/appeals?status=open", expect.any(Object));
    expect(fetchMock).toHaveBeenNthCalledWith(13, "/api/api/riordino/practices/practice-1/appeals", expect.any(Object));
    expect(fetchMock).toHaveBeenNthCalledWith(
      14,
      "/api/api/riordino/practices/practice-1/issues?severity=high&status_filter=open&category=cadastral",
      expect.any(Object),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(15, "/api/api/riordino/practices/practice-1/issues", expect.any(Object));
    expect(fetchMock).toHaveBeenNthCalledWith(
      16,
      "/api/api/riordino/practices/practice-1/documents?phase_id=phase-1&step_id=step-1&document_type=visura&appeal_id=appeal-1",
      expect.any(Object),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(17, "/api/api/riordino/practices/practice-1/documents", expect.any(Object));
    expect(fetchMock).toHaveBeenNthCalledWith(18, "/api/api/riordino/practices/practice-1/gis-links", expect.any(Object));
    expect(fetchMock).toHaveBeenNthCalledWith(19, "/api/api/riordino/practices/practice-1/parcels", expect.any(Object));
    expect(fetchMock).toHaveBeenNthCalledWith(20, "/api/api/riordino/notifications", expect.any(Object));
    expect(fetchMock).toHaveBeenNthCalledWith(21, "/api/api/riordino/config/document-types", expect.any(Object));
    expect(fetchMock).toHaveBeenNthCalledWith(22, "/api/api/riordino/config/issue-types", expect.any(Object));
    expect(fetchMock).toHaveBeenNthCalledWith(23, "/api/api/riordino/config/municipalities", expect.any(Object));
  });

  test("calls mutation endpoints and blob downloads", async () => {
    const blob = new Blob(["pdf"], { type: "application/pdf" });
    const fetchMock = vi
      .fn()
      .mockImplementationOnce(() => Promise.resolve(jsonResponse({ id: "block-1" })))
      .mockImplementationOnce(() => Promise.resolve(new Response(blob, { status: 200 })))
      .mockImplementationOnce(() => Promise.resolve(jsonResponse({ id: "practice-1" })))
      .mockImplementationOnce(() => Promise.resolve(jsonResponse({ id: "snapshot-1" })))
      .mockImplementationOnce(() => Promise.resolve(jsonResponse({ id: "snapshot-2" })))
      .mockImplementationOnce(() => Promise.resolve(jsonResponse({ id: "snapshot-3" })))
      .mockImplementationOnce(() => Promise.resolve(jsonResponse({ synced: 1 })))
      .mockImplementationOnce(() => Promise.resolve(jsonResponse({ synced: 2 })))
      .mockImplementationOnce(() => Promise.resolve(jsonResponse({ id: "appeal-1" })))
      .mockImplementationOnce(() => Promise.resolve(jsonResponse({ id: "appeal-1", status: "resolved" })))
      .mockImplementationOnce(() => Promise.resolve(jsonResponse({ id: "issue-1" })))
      .mockImplementationOnce(() => Promise.resolve(jsonResponse({ id: "issue-1", status: "closed" })))
      .mockImplementationOnce(() => Promise.resolve(jsonResponse({ id: "doc-1" })))
      .mockImplementationOnce(() => Promise.resolve(jsonResponse({ id: "doc-2" })))
      .mockImplementationOnce(() => Promise.resolve(jsonResponse({ id: "doc-1", deleted: true })))
      .mockImplementationOnce(() => Promise.resolve(new Response(blob, { status: 200 })))
      .mockImplementationOnce(() => Promise.resolve(new Response(blob, { status: 200 })))
      .mockImplementationOnce(() => Promise.resolve(new Response(blob, { status: 200 })))
      .mockImplementationOnce(() => Promise.resolve(jsonResponse({ id: "gis-1" })))
      .mockImplementationOnce(() => Promise.resolve(jsonResponse({ id: "gis-1", status: "active" })))
      .mockImplementationOnce(() => Promise.resolve(jsonResponse({ id: "step-1", status: "done" })))
      .mockImplementationOnce(() => Promise.resolve(jsonResponse({ id: "step-2", status: "skipped" })))
      .mockImplementationOnce(() => Promise.resolve(jsonResponse({ id: "step-2", status: "open" })))
      .mockImplementationOnce(() => Promise.resolve(jsonResponse({ id: "phase-1", status: "running" })))
      .mockImplementationOnce(() => Promise.resolve(jsonResponse({ id: "phase-1", status: "done" })))
      .mockImplementationOnce(() => Promise.resolve(jsonResponse({ id: "notification-1", read: true })))
      .mockImplementationOnce(() => Promise.resolve(jsonResponse([{ id: "notification-2" }])))
      .mockImplementationOnce(() => Promise.resolve(jsonResponse({ id: "doc-type-1" })))
      .mockImplementationOnce(() => Promise.resolve(jsonResponse({ id: "doc-type-1", label: "Visura" })))
      .mockImplementationOnce(() => Promise.resolve(jsonResponse({ id: "doc-type-1", deleted: true })))
      .mockImplementationOnce(() => Promise.resolve(jsonResponse({ id: "issue-type-1" })))
      .mockImplementationOnce(() => Promise.resolve(jsonResponse({ id: "issue-type-1", label: "Cadastral" })))
      .mockImplementationOnce(() => Promise.resolve(jsonResponse({ id: "issue-type-1", deleted: true })));
    vi.stubGlobal("fetch", fetchMock);

    await createRiordinoBlock("token", { name: "Block A", parcel_ids: ["p-1"] });
    await exportRiordinoBlockSummary("token", "block-1");
    await createRiordinoBlockPhase2Practice("token", "block-1", { practice_name: "Practice A" });
    await reviewRiordinoBlockParcel("token", "block-1", "snapshot-1", { review_status: "approved" });
    await requestRiordinoBlockSisterVisura("token", "block-1", "snapshot-1", { notes: "Need visura" });
    await completeRiordinoBlockSisterVisura("token", "block-1", "snapshot-1", { document_id: "doc-1" });
    await syncRiordinoBlockSisterVisura("token", "block-1", "snapshot-1", { force: true });
    await syncRiordinoBlockSisterVisure("token", "block-1", { force: true });
    await createRiordinoAppeal("token", "practice-1", { reason: "Appeal reason" });
    await resolveRiordinoAppeal("token", "practice-1", "appeal-1", { resolution: "Accepted" });
    await createRiordinoIssue("token", "practice-1", { title: "Issue", severity: "high" });
    await closeRiordinoIssue("token", "practice-1", "issue-1", { resolution: "Fixed" });
    await uploadRiordinoDocument("token", "practice-1", {
      file: new File(["pdf"], "visura.pdf", { type: "application/pdf" }),
      document_type: "visura",
      phase_id: "phase-1",
      step_id: "step-1",
      appeal_id: "appeal-1",
      issue_id: "issue-1",
      notes: "Uploaded",
    });
    await uploadRiordinoDocument("token", "practice-1", {
      file: new File(["pdf"], "visura-min.pdf", { type: "application/pdf" }),
      document_type: "visura",
    });
    await deleteRiordinoDocument("token", "doc-1");
    await downloadRiordinoDocument("token", "doc-1");
    await downloadRiordinoPracticeSummary("token", "practice-1");
    await downloadRiordinoPracticeDossier("token", "practice-1");
    await createRiordinoGisLink("token", "practice-1", { layer_id: "layer-1" });
    await updateRiordinoGisLink("token", "practice-1", "gis-1", { status: "active" });
    await advanceRiordinoStep("token", "practice-1", "step-1", { notes: "Done" });
    await skipRiordinoStep("token", "practice-1", "step-2", { reason: "Not needed" });
    await reopenRiordinoStep("token", "practice-1", "step-2");
    await startRiordinoPhase("token", "practice-1", "phase-1");
    await completeRiordinoPhase("token", "practice-1", "phase-1", { notes: "Completed" });
    await markRiordinoNotificationRead("token", "notification-1");
    await checkRiordinoDeadlines("token");
    await createRiordinoDocumentType("token", { code: "visura", label: "Visura" });
    await updateRiordinoDocumentType("token", "doc-type-1", { label: "Visura aggiornata" });
    await deleteRiordinoDocumentType("token", "doc-type-1");
    await createRiordinoIssueType("token", { code: "cadastral", label: "Cadastral" });
    await updateRiordinoIssueType("token", "issue-type-1", { label: "Cadastral updated" });
    await deleteRiordinoIssueType("token", "issue-type-1");

    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      "/api/api/riordino/blocks/block-1/export/summary",
      expect.objectContaining({ headers: expect.not.objectContaining({ "Content-Type": "application/json" }) }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      14,
      "/api/api/riordino/practices/practice-1/documents",
      expect.objectContaining({
        method: "POST",
        body: expect.any(FormData),
        headers: expect.not.objectContaining({ "Content-Type": "application/json" }),
      }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      16,
      "/api/api/riordino/practices/documents/doc-1/download",
      expect.any(Object),
    );
  });

  test("throws ApiError with parsed detail variants", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ detail: "Forbidden" }, 403))
      .mockResolvedValueOnce(jsonResponse({ detail: { message: "Validation failed" } }, 422))
      .mockResolvedValueOnce(jsonResponse({ detail: { code: "invalid" } }, 400))
      .mockResolvedValueOnce(new Response("not-json", { status: 500, statusText: "Server Error" }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(getRiordinoDashboard("token")).rejects.toSatisfy((error: unknown) => {
      expect(error).toBeInstanceOf(ApiError);
      expect(error).toMatchObject({ message: "Forbidden", status: 403 });
      return true;
    });
    await expect(getRiordinoDashboard("token")).rejects.toSatisfy((error: unknown) => {
      expect(error).toBeInstanceOf(ApiError);
      expect(error).toMatchObject({ message: "Validation failed", status: 422 });
      return true;
    });
    await expect(getRiordinoDashboard("token")).rejects.toSatisfy((error: unknown) => {
      expect(error).toBeInstanceOf(ApiError);
      expect(error).toMatchObject({ message: JSON.stringify({ code: "invalid" }), status: 400 });
      return true;
    });
    await expect(getRiordinoDashboard("token")).rejects.toSatisfy((error: unknown) => {
      expect(error).toBeInstanceOf(ApiError);
      expect(error).toMatchObject({ message: "Server Error", status: 500 });
      return true;
    });
  });

  test("throws ApiError from blob downloads and skips blank query params", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({}, 500))
      .mockResolvedValueOnce(jsonResponse({ items: [] }))
      .mockResolvedValueOnce(new Response("bad", { status: 500, statusText: "" }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(exportRiordinoBlockSummary("token", "block-1")).rejects.toMatchObject({
      message: "Request failed",
      status: 500,
    });
    await listRiordinoBlocks("token", { status: "  ", page: "2" });
    await expect(getRiordinoDashboard("token")).rejects.toMatchObject({
      message: "Request failed",
      status: 500,
    });

    expect(fetchMock).toHaveBeenNthCalledWith(2, "/api/api/riordino/blocks?page=2", expect.any(Object));
  });
});
