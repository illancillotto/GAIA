import { webcrypto } from "node:crypto";
import { afterEach, expect, it, vi } from "vitest";
import { communications, loadSnapshot, receiptBlob, uploadAttachment } from "@/lib/communications-api";
import { part } from "./fixtures";
const request = vi.hoisted(() => vi.fn());
vi.mock("@/lib/api", () => ({ getApiBaseUrl: () => "http://synthetic/api", request }));
afterEach(() => vi.unstubAllGlobals());
it("uses authenticated commands, default GET and explicit PATCH without cached PII", async () => {
  request.mockResolvedValue({ ok: true });
  await communications("token", "/accounts");
  expect(request).toHaveBeenLastCalledWith("/communications/accounts", { method: "GET", headers: { Authorization: "Bearer token" }, cache: "no-store" });
  await communications("token", "/messages", { body: "text" });
  expect(request.mock.lastCall?.[1].method).toBe("POST");
  await communications("token", "/messages/id", {}, "PATCH");
  expect(request.mock.lastCall?.[1].method).toBe("PATCH");
  await communications("token", "/templates/id", { confirmed: true }, "DELETE");
  expect(request).toHaveBeenLastCalledWith("/communications/templates/id", {
    method: "DELETE", headers: { Authorization: "Bearer token", "Content-Type": "application/json" },
    body: JSON.stringify({ confirmed: true }), cache: "no-store",
  });
});
it("checks SHA256, size, review proof and authentication before returning PDF bytes", async () => {
  vi.stubGlobal("crypto", undefined);
  const bytes = new Uint8Array([1, 2, 3, 4]);
  const hash = Buffer.from(await webcrypto.subtle.digest("SHA-256", bytes)).toString("hex");
  const fetcher = vi.fn().mockResolvedValue(new Response(bytes, { headers: { "X-Communication-Review": "proof" } }));
  vi.stubGlobal("fetch", fetcher);
  expect((await loadSnapshot("token", "message", { ...part, sha256: hash }, new AbortController().signal)).reviewId).toBe("proof");
  expect(fetcher.mock.lastCall?.[1].headers.Authorization).toBe("Bearer token");
  for (const corrupted of [{ ...part, sha256: "wrong" }, { ...part, sha256: hash, size: 5 }]) {
    fetcher.mockResolvedValue(new Response(bytes, { headers: { "X-Communication-Review": "proof" } }));
    await expect(loadSnapshot("token", "message", corrupted, new AbortController().signal)).rejects.toThrow("Integrità");
  }
  fetcher.mockResolvedValue(new Response(bytes));
  await expect(loadSnapshot("token", "message", part, new AbortController().signal)).rejects.toThrow("Integrità");
  fetcher.mockResolvedValue(new Response(null, { status: 403 }));
  await expect(loadSnapshot("token", "message", part, new AbortController().signal)).rejects.toThrow("accesso negato");
});
it("downloads original receipt and uploads attachment using authenticated multipart", async () => {
  const fetcher = vi.fn().mockResolvedValue(new Response("synthetic eml"));
  vi.stubGlobal("fetch", fetcher);
  expect(await (await receiptBlob("token", "message", "receipt")).text()).toBe("synthetic eml");
  fetcher.mockResolvedValue(new Response(JSON.stringify({ id: "message" })));
  expect(await uploadAttachment("token", "message", 2, new File(["pdf"], "test.pdf"))).toEqual({ id: "message" });
  expect(fetcher.mock.lastCall?.[1].body.get("expected_version")).toBe("2");
  fetcher.mockResolvedValue(new Response(null, { status: 409 }));
  await expect(uploadAttachment("token", "message", 1, new File([], "bad.pdf"))).rejects.toThrow("Allegato rifiutato");
  await expect(receiptBlob("token", "message", "receipt")).rejects.toThrow("Ricevuta non disponibile");
});
