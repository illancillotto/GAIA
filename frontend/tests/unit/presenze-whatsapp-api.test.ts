import { afterEach, describe, expect, test, vi } from "vitest";

import {
  getPresenzeWhatsAppDashboard,
  getPresenzeWhatsAppPreview,
  listPresenzeWhatsAppMessages,
  listPresenzeWhatsAppOptOuts,
  reconcilePresenzeWhatsAppMessage,
  restorePresenzeWhatsAppUser,
  updatePresenzeWhatsAppPhone,
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
