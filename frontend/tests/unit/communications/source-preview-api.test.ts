import { createHash } from "node:crypto";
import { afterEach, expect, it, vi } from "vitest";
import { loadSourcePreview } from "@/lib/communication-source-preview";
vi.mock("@/lib/api", () => ({ getApiBaseUrl: () => "http://synthetic/api" }));
const bytes = new Uint8Array([1, 2, 3, 4]);
const hash = createHash("sha256").update(bytes).digest("hex");
const headers = { "X-Content-SHA256": hash, "X-PDF-Pages": "3" };
afterEach(() => vi.unstubAllGlobals());
it("loads authenticated exact bytes without Web Crypto (including HTTP intranet)", async () => {
  vi.stubGlobal("crypto", undefined);
  const fetcher = vi.fn().mockResolvedValue(new Response(bytes, { headers })); vi.stubGlobal("fetch", fetcher);
  const signal = new AbortController().signal;
  const snapshot = await loadSourcePreview("token", "source", signal);
  expect(snapshot.part).toMatchObject({ id: "source", sha256: hash, pages: 3, size: 4 });
  expect(new Uint8Array(snapshot.content)).toEqual(bytes);
  expect(fetcher).toHaveBeenCalledWith("http://synthetic/api/communications/ruolo/candidates/source/preview", { headers: { Authorization: "Bearer token" }, cache: "no-store", signal });
});
it.each([
  { "X-Content-SHA256": "" }, { "X-Content-SHA256": "wrong" },
  { "X-PDF-Pages": "1.5" }, { "X-PDF-Pages": "0" }, { "X-PDF-Pages": "201" }, { "X-PDF-Pages": "invalid" },
])("rejects invalid metadata %j", async (changed) => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(bytes, { headers: { ...headers, ...changed } })));
  await expect(loadSourcePreview("token", "source", new AbortController().signal)).rejects.toThrow("Integrità");
});
it.each([0, 32 * 1024 * 1024 + 1])("rejects document size %i", async (size) => {
  const data = new Uint8Array(size);
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(data, { headers: { ...headers, "X-Content-SHA256": createHash("sha256").update(data).digest("hex") } })));
  await expect(loadSourcePreview("token", "source", new AbortController().signal)).rejects.toThrow("limiti");
});
it("reports missing or forbidden PDFs and propagates network failures", async () => {
  const fetcher = vi.fn().mockResolvedValue(new Response(null, { status: 403 })); vi.stubGlobal("fetch", fetcher);
  await expect(loadSourcePreview("token", "source", new AbortController().signal)).rejects.toThrow("accesso negato");
  fetcher.mockRejectedValue(new Error("offline"));
  await expect(loadSourcePreview("token", "source", new AbortController().signal)).rejects.toThrow("offline");
});
