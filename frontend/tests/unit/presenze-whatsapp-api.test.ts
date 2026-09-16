import { afterEach, describe, expect, test, vi } from "vitest";

import {
  getPresenzeWhatsAppDashboard,
  getPresenzeWhatsAppConfiguration,
  getPresenzeWhatsAppPreview,
  getPresenzeWhatsAppQr,
  getPresenzeWhatsAppSession,
  listPresenzeWhatsAppMessages,
  listPresenzeWhatsAppOptOuts,
  reconcilePresenzeWhatsAppMessage,
  logoutPresenzeWhatsAppSession,
  restorePresenzeWhatsAppUser,
  startPresenzeWhatsAppSession,
  updatePresenzeWhatsAppPhone,
  updatePresenzeWhatsAppConfiguration,
} from "@/lib/api";

function response(payload: unknown = null, status = 200): Response {
  return new Response(status === 204 ? null : JSON.stringify(payload), { status, headers: { "content-type": "application/json" } });
}

describe("Presenze WhatsApp API", () => {
  afterEach(() => vi.unstubAllGlobals());

  test("reads dashboard, preview and STOP list", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(response({ provider_enabled: false }))
      .mockResolvedValueOnce(response({ ready: [], skipped: [] }))
      .mockResolvedValueOnce(response([]));
    vi.stubGlobal("fetch", fetchMock);
    await getPresenzeWhatsAppDashboard("token");
    await getPresenzeWhatsAppPreview("token");
    await listPresenzeWhatsAppOptOuts("token");
    expect(fetchMock.mock.calls.map((call) => call[0])).toEqual([
      "/api/presenze/whatsapp/dashboard",
      "/api/presenze/whatsapp/preview",
      "/api/presenze/whatsapp/opt-outs",
    ]);
  });

  test("reads and updates super-admin configuration", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(response({ provider: "" }))
      .mockResolvedValueOnce(response({ provider: "dry_run" }));
    vi.stubGlobal("fetch", fetchMock);
    await getPresenzeWhatsAppConfiguration("token");
    await updatePresenzeWhatsAppConfiguration("token", {
      provider: "dry_run", waha_url: "http://waha:3000", waha_session: "default",
      reminder_cron: "30 9 * * 1-5", lookback_days: 3, include_missing_punches: false,
      max_per_run: 40, min_delay_seconds: 25, max_delay_seconds: 75,
      send_start_hour: 8, send_end_hour: 19,
    });
    expect(fetchMock.mock.calls[0][0]).toBe("/api/presenze/whatsapp/configuration");
    expect(fetchMock.mock.calls[1][1]).toEqual(expect.objectContaining({ method: "PUT" }));
  });

  test("manages the protected WAHA session", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(response({ status: "working" }))
      .mockResolvedValueOnce(response({ status: "starting" }))
      .mockResolvedValueOnce(response({ image_data_url: "data:image/png;base64,cXI=" }))
      .mockResolvedValueOnce(response({ status: "stopped" }));
    vi.stubGlobal("fetch", fetchMock);
    await getPresenzeWhatsAppSession("token");
    await startPresenzeWhatsAppSession("token");
    await getPresenzeWhatsAppQr("token");
    await logoutPresenzeWhatsAppSession("token");
    expect(fetchMock.mock.calls.map((call) => [call[0], call[1]?.method])).toEqual([
      ["/api/presenze/whatsapp/session", undefined],
      ["/api/presenze/whatsapp/session/start", "POST"],
      ["/api/presenze/whatsapp/session/qr", undefined],
      ["/api/presenze/whatsapp/session/logout", "POST"],
    ]);
  });

  test("builds optional history filters and supports an empty query", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(response({ items: [], total: 0 }))
      .mockResolvedValueOnce(response({ items: [], total: 0 }));
    vi.stubGlobal("fetch", fetchMock);
    await listPresenzeWhatsAppMessages("token", { status: "READ", q: "Rossi", page: 2, pageSize: 10 });
    await listPresenzeWhatsAppMessages("token");
    expect(fetchMock.mock.calls[0][0]).toBe("/api/presenze/whatsapp/messages?status=READ&q=Rossi&page=2&page_size=10");
    expect(fetchMock.mock.calls[1][0]).toBe("/api/presenze/whatsapp/messages");
  });

  test("updates administrative state", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(response(null, 204))
      .mockResolvedValueOnce(response({ application_user_id: 7, phone: "+39333" }))
      .mockResolvedValueOnce(response(null, 204));
    vi.stubGlobal("fetch", fetchMock);
    await restorePresenzeWhatsAppUser("token", 7);
    await updatePresenzeWhatsAppPhone("token", 7, "+39333");
    await reconcilePresenzeWhatsAppMessage("token", "message-1", { sent: true, evidence: "WAHA", provider_message_id: "wa-1" });
    expect(fetchMock.mock.calls[0][1]).toEqual(expect.objectContaining({ method: "DELETE" }));
    expect(fetchMock.mock.calls[1][1]).toEqual(expect.objectContaining({ method: "PATCH", body: JSON.stringify({ phone: "+39333" }) }));
    expect(fetchMock.mock.calls[2][1]).toEqual(expect.objectContaining({ method: "POST" }));
  });
});
