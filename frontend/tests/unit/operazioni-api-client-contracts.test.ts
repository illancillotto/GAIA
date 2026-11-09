import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import * as api from "@/features/operazioni/api/client";

const session = vi.hoisted(() => ({ token: "synthetic-token" as string | null }));
vi.mock("@/lib/api", () => ({ getApiBaseUrl: () => "/synthetic-api" }));
vi.mock("@/lib/auth", () => ({ getStoredAccessToken: () => session.token }));

const fetch = vi.fn();
const response = { id: "synthetic", items: [], total: 0 };
beforeEach(() => {
  session.token = "synthetic-token";
  fetch.mockReset().mockImplementation(async () => new Response(JSON.stringify(response)));
  vi.stubGlobal("fetch", fetch);
});
afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); vi.useRealTimers(); });

type Contract = { name: string; call: () => Promise<unknown>; path: string; method?: string; body?: unknown };
const data = { note: "Synthetic input" };
const contracts: Contract[] = [
  { name: "vehicle detail", call: () => api.getVehicle("v1"), path: "/vehicles/v1" },
  { name: "vehicle update", call: () => api.updateVehicle("v1", data), path: "/vehicles/v1", method: "PATCH", body: data },
  { name: "vehicle creation", call: () => api.createVehicle(data), path: "/vehicles", method: "POST", body: data },
  { name: "autodoc status", call: () => api.getVehicleAutodocSyncStatus(), path: "/vehicles/autodoc-sync/status" },
  { name: "autodoc defaults", call: () => api.queueVehicleAutodocSync(), path: "/vehicles/autodoc-sync", method: "POST", body: {} },
  { name: "autodoc selection", call: () => api.queueVehicleAutodocSync({ vehicle_ids: ["v1"] }), path: "/vehicles/autodoc-sync", method: "POST", body: { vehicle_ids: ["v1"] } },
  { name: "single autodoc", call: () => api.queueSingleVehicleAutodocSync("v1"), path: "/vehicles/v1/autodoc-sync", method: "POST" },
  { name: "start vehicle session", call: () => api.startVehicleUsageSession(data), path: "/vehicles/usage-sessions/start", method: "POST", body: data },
  { name: "stop vehicle session", call: () => api.stopVehicleUsageSession("s1", data), path: "/vehicles/usage-sessions/s1/stop", method: "POST", body: data },
  { name: "activity catalog", call: () => api.getActivityCatalog(), path: "/activities/catalog" },
  { name: "activity detail", call: () => api.getActivity("a1"), path: "/activities/a1" },
  { name: "activity attachments", call: () => api.getActivityAttachments("a1"), path: "/activities/a1/attachments" },
  { name: "activity GPS summary", call: () => api.getActivityGpsSummary("a1"), path: "/activities/a1/gps-summary" },
  { name: "activity GPS viewer", call: () => api.getActivityGpsViewer("a1"), path: "/activities/a1/gps-viewer" },
  { name: "start activity", call: () => api.startActivity(data), path: "/activities/start", method: "POST", body: data },
  { name: "stop activity", call: () => api.stopActivity("a1", data), path: "/activities/a1/stop", method: "POST", body: data },
  { name: "approve activity", call: () => api.approveActivity("a1", data), path: "/activities/a1/approve", method: "POST", body: data },
  { name: "create report", call: () => api.createReport(data), path: "/reports", method: "POST", body: data },
  { name: "report detail", call: () => api.getReport("r1"), path: "/reports/r1" },
  { name: "report attachments", call: () => api.getReportAttachments("r1"), path: "/reports/r1/attachments" },
  { name: "resolve fleet transactions", call: () => api.resolveFleetTransactions([]), path: "/vehicles/fuel-logs/resolve-fleet-transactions", method: "POST", body: [] },
  { name: "case detail", call: () => api.getCase("c1"), path: "/cases/c1" },
  { name: "case attachments", call: () => api.getCaseAttachments("c1"), path: "/cases/c1/attachments" },
  { name: "assign case", call: () => api.assignCase("c1", data), path: "/cases/c1/assign", method: "POST", body: data },
  { name: "acknowledge case", call: () => api.acknowledgeCase("c1", data), path: "/cases/c1/acknowledge", method: "POST", body: data },
  { name: "start case", call: () => api.startCase("c1", data), path: "/cases/c1/start", method: "POST", body: data },
  { name: "resolve case", call: () => api.resolveCase("c1", data), path: "/cases/c1/resolve", method: "POST", body: data },
  { name: "close case", call: () => api.closeCase("c1", data), path: "/cases/c1/close", method: "POST", body: data },
  { name: "reopen case", call: () => api.reopenCase("c1", data), path: "/cases/c1/reopen", method: "POST", body: data },
  { name: "case events", call: () => api.getCaseEvents("c1"), path: "/cases/c1/events" },
  { name: "storage metrics", call: () => api.getStorageLatestMetric(), path: "/storage/metrics/latest" },
  { name: "storage alerts", call: () => api.getStorageAlerts(), path: "/storage/alerts" },
  { name: "recalculate storage", call: () => api.recalculateStorage(), path: "/storage/recalculate", method: "POST" },
  { name: "report categories", call: () => api.getReportCategories(), path: "/lookups/report-categories" },
  { name: "report severities", call: () => api.getReportSeverities(), path: "/lookups/report-severities" },
  { name: "teams", call: () => api.getTeams(), path: "/lookups/teams" },
  { name: "maintenance types", call: () => api.getMaintenanceTypes(), path: "/lookups/maintenance-types" },
  { name: "operator", call: () => api.getOperator("o1"), path: "/operators/o1" },
  { name: "operator detail", call: () => api.getOperatorDetail("o1"), path: "/operators/o1/detail" },
  { name: "unlinked operators", call: () => api.getUnlinkedOperators(), path: "/operators/unlinked" },
  { name: "autolink operators", call: () => api.autoLinkGaiaOperators(), path: "/operators/auto-link-gaia", method: "POST" },
  { name: "link operator", call: () => api.linkGaiaUser("o1", 77), path: "/operators/o1/link-gaia", method: "POST", body: { gaia_user_id: 77 } },
  { name: "unlink operator", call: () => api.unlinkGaiaUser("o1"), path: "/operators/o1/unlink-gaia", method: "POST" },
  { name: "invite operator", call: () => api.inviteOperator("o1"), path: "/operators/o1/invite", method: "POST" },
  { name: "invitation status", call: () => api.getInvitationStatus("o1"), path: "/operators/o1/invitation-status" },
  { name: "bulk import operators", call: () => api.bulkImportOperatorsAsGaiaUsers(), path: "/operators/bulk-import-gaia", method: "POST" },
  { name: "area detail", call: () => api.getArea("ar1"), path: "/areas/ar1" },
  { name: "fuel card assignments", call: () => api.getFuelCardAssignments("f1"), path: "/fuel-cards/f1/assignments" },
  { name: "assign fuel card", call: () => api.assignFuelCard("f1", { wc_operator_id: "o1" }), path: "/fuel-cards/f1/assign", method: "POST", body: { wc_operator_id: "o1" } },
  { name: "ignore fuel card", call: () => api.ignoreFuelCardDriver("f1"), path: "/fuel-cards/f1/ignore", method: "POST" },
  { name: "ignore fuel card with note", call: () => api.ignoreFuelCardDriver("f1", "A & B"), path: "/fuel-cards/f1/ignore?note=A+%26+B", method: "POST" },
  { name: "available analytics periods", call: () => api.getAnalyticsAvailablePeriods(), path: "/analytics/available-periods" },
];
const lists: [string, (params?: Record<string, string>) => Promise<unknown>, string][] = [
  ["vehicles", api.getVehicles, "/vehicles"], ["activities", api.getActivities, "/activities"],
  ["reports", api.getReports, "/reports"], ["reports dashboard", api.getReportsDashboard, "/reports/dashboard"],
  ["refuel events", api.getWhiteRefuelEvents, "/vehicles/refuel-events"], ["cases", api.getCases, "/cases"],
  ["operators", api.getOperators, "/operators"], ["areas", api.getAreas, "/areas"],
  ["fuel cards", api.getFuelCards, "/fuel-cards"], ["unmatched fuel cards", api.getUnmatchedFuelCards, "/fuel-cards/unmatched"],
];

describe("Operazioni client transport contracts, including the module used by HR permissions", () => {
  it.each(contracts)("preserves $name HTTP method, payload, session and response", async ({ call, path, method, body }) => {
    expect(await call()).toEqual(response);
    expect(fetch).toHaveBeenCalledExactlyOnceWith("/synthetic-api/operazioni" + path, {
      ...(method ? { method } : {}), ...(body === undefined ? {} : { body: JSON.stringify(body) }),
      headers: { "Content-Type": "application/json", Authorization: "Bearer synthetic-token" }, cache: "no-store",
    });
  });

  it.each(lists)("encodes %s filters and omits the query when absent", async (_name, list, path) => {
    expect(await list()).toEqual(response);
    expect(fetch.mock.calls[0][0]).toBe("/synthetic-api/operazioni" + path);
    expect(await list({ search: "A & B" })).toEqual(response);
    expect(fetch.mock.calls[1][0]).toBe("/synthetic-api/operazioni" + path + "?search=A+%26+B");
  });

  it.each([
    ["summary", api.getAnalyticsSummary], ["fuel", api.getAnalyticsFuel], ["km", api.getAnalyticsKm],
    ["work-hours", api.getAnalyticsWorkHours], ["anomalies", api.getAnalyticsAnomalies],
  ] as const)("preserves optional %s analytics dates", async (path, list) => {
    expect(await list()).toEqual(response);
    expect(fetch.mock.calls[0][0]).toBe("/synthetic-api/operazioni/analytics/" + path);
    expect(await list({ from_date: "2026-10-01", to_date: "2026-10-31" })).toEqual(response);
    expect(fetch.mock.calls[1][0]).toBe("/synthetic-api/operazioni/analytics/" + path + "?from_date=2026-10-01&to_date=2026-10-31");
  });

  it("keeps pagination and anomaly thresholds in the correct query parameters", async () => {
    await api.getVehicleFuelLogs("v1"); await api.getVehicleFuelLogs("v1", { page: "2" });
    await api.getUnresolvedTransactions(); await api.getUnresolvedTransactions({ status_filter: "pending", page: 2, page_size: 50 });
    await api.getUnresolvedAnomalies(); await api.getUnresolvedAnomalies({ liters_threshold: 100, same_day_min: 3 });
    await api.getGaiaUsersForLinking(); await api.getGaiaUsersForLinking("A & B");
    expect(fetch.mock.calls.map(([url]) => url)).toEqual([
      "/synthetic-api/operazioni/vehicles/v1/fuel-logs", "/synthetic-api/operazioni/vehicles/v1/fuel-logs?page=2",
      "/synthetic-api/operazioni/vehicles/fuel-logs/unresolved-transactions", "/synthetic-api/operazioni/vehicles/fuel-logs/unresolved-transactions?status_filter=pending&page=2&page_size=50",
      "/synthetic-api/operazioni/vehicles/fuel-logs/unresolved-transactions/anomalies", "/synthetic-api/operazioni/vehicles/fuel-logs/unresolved-transactions/anomalies?liters_threshold=100&same_day_min=3",
      "/synthetic-api/operazioni/operators/gaia-users", "/synthetic-api/operazioni/operators/gaia-users?search=A+%26+B",
    ]);
    expect(await api.skipUnresolvedTransaction("u1")).toBeUndefined();
    expect(fetch).toHaveBeenLastCalledWith("/synthetic-api/operazioni/vehicles/fuel-logs/unresolved-transactions/u1/skip", expect.objectContaining({ method: "POST" }));
  });

  it.each([
    [api.importWhiteReports, "/reports/import-white"], [api.importFleetTransactions, "/vehicles/fuel-logs/import-fleet-transactions"],
    [api.importFuelCards, "/fuel-cards/import-excel"],
  ] as const)("uploads multipart files without forcing a JSON content type (%s)", async (upload, path) => {
    const file = new File(["synthetic spreadsheet"], "synthetic.xlsx");
    expect(await upload(file)).toEqual(response);
    const [url, options] = fetch.mock.calls[0];
    expect(url).toBe("/synthetic-api/operazioni" + path);
    expect(options).toMatchObject({ method: "POST", cache: "no-store", headers: { Authorization: "Bearer synthetic-token" } });
    expect(options.headers).not.toHaveProperty("Content-Type");
    expect(options.body).toBeInstanceOf(FormData);
    expect(options.body.get("file")).toBe(file);
  });

  it.each(["text/plain", "application/json", "application/ld+json", "application/xml", "text/csv", "application/pdf", ""])("previews %s with the correct MIME type, filename and text policy", async mime => {
    fetch.mockResolvedValueOnce(new Response("synthetic contents", { headers: { "content-type": mime, "content-disposition": 'attachment; filename="synthetic.txt"' } }));
    const preview = await api.getAttachmentPreviewData("att1");
    expect(preview.filename).toBe("synthetic.txt");
    expect(preview.mimeType).toBe(mime || "application/octet-stream");
    expect(preview.textContent).toBe(mime && mime !== "application/pdf" ? "synthetic contents" : null);
    expect(preview.blob.size).toBe(18);
    expect(fetch).toHaveBeenCalledExactlyOnceWith("/synthetic-api/operazioni/attachments/att1/download", {
      method: "GET", headers: { Authorization: "Bearer synthetic-token" }, cache: "no-store",
    });
  });

  it("retains the attachment metadata when a text read fails", async () => {
    const blob = new Blob(["synthetic"], { type: "text/plain" });
    vi.spyOn(blob, "text").mockRejectedValue(new Error("Synthetic read failure"));
    const result = new Response();
    vi.spyOn(result, "blob").mockResolvedValue(blob);
    fetch.mockResolvedValueOnce(result);
    expect(await api.getAttachmentPreviewData("att1")).toEqual({ blob, filename: undefined, mimeType: "text/plain", textContent: null });
  });

  it.each([
    { body: JSON.stringify({ detail: "No permission" }), statusText: "Forbidden", message: "No permission" },
    { body: "unavailable", statusText: "Service Unavailable", message: "Service Unavailable" },
    { body: "unavailable", statusText: "", message: "Request failed" },
  ])("reports attachment download failure as $message without producing a file", async ({ body, statusText, message }) => {
    session.token = null;
    fetch.mockResolvedValueOnce(new Response(body, { status: 403, statusText }));
    await expect(api.getAttachmentPreviewData("att1")).rejects.toThrow(message);
    expect(fetch).toHaveBeenCalledWith("/synthetic-api/operazioni/attachments/att1/download", expect.objectContaining({ headers: {} }));
  });

  it.each([
    { preferred: "chosen.pdf", disposition: 'attachment; filename="server.pdf"', expected: "chosen.pdf" },
    { preferred: undefined, disposition: "attachment; filename=server.pdf", expected: "server.pdf" },
    { preferred: undefined, disposition: "", expected: "attachment-att1" },
  ])("downloads with filename $expected and releases the temporary browser URL", async ({ preferred, disposition, expected }) => {
    vi.useFakeTimers();
    const create = vi.fn().mockReturnValue("blob:synthetic"), revoke = vi.fn();
    vi.stubGlobal("URL", Object.assign(class extends URL {}, { createObjectURL: create, revokeObjectURL: revoke }));
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function (this: HTMLAnchorElement) {
      expect(this.download).toBe(expected); expect(this.href).toBe("blob:synthetic"); expect(this.isConnected).toBe(true);
    });
    fetch.mockResolvedValueOnce(new Response("pdf", { headers: disposition ? { "content-disposition": disposition } : {} }));
    await api.downloadAttachment("att1", preferred);
    expect(click).toHaveBeenCalledOnce(); expect(create).toHaveBeenCalledOnce();
    expect(document.querySelector('a[href="blob:synthetic"]')).toBeNull();
    expect(revoke).not.toHaveBeenCalled();
    await vi.advanceTimersByTimeAsync(60_000);
    expect(revoke).toHaveBeenCalledExactlyOnceWith("blob:synthetic");
  });
});
