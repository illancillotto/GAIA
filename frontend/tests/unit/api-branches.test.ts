import { afterEach, describe, expect, test, vi } from "vitest";

import {
  createElaborazioneBatchWebSocket,
  getElaborazioneBatch,
  request,
  requestFormDataWithUploadProgress,
} from "@/lib/api";

function jsonResponse(payload: unknown, status = 200): Response {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "content-type": "application/json" },
  });
}

describe("api branch coverage", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.useRealTimers();
  });

  test("request maps string detail errors and bodies without content-type", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ detail: "plain string error" }), {
          status: 400,
          headers: { "content-type": "application/json" },
        }),
      )
      .mockResolvedValueOnce(new Response('{"ok":true}', { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(request("/string-detail")).rejects.toMatchObject({
      message: "plain string error",
      status: 400,
    });
    await expect(request<{ ok: boolean }>("/missing-content-type")).resolves.toEqual({ ok: true });
  });

  test("request forwards abort signals when combined with timeout controller", async () => {
    const fetchMock = vi.fn().mockImplementation((_input: string, init?: RequestInit) => {
      if (init?.signal?.aborted) {
        return Promise.reject(init.signal.reason ?? new Error("aborted"));
      }
      return new Promise((_resolve, reject) => {
        init?.signal?.addEventListener(
          "abort",
          () => reject(init.signal?.reason ?? new Error("aborted")),
          { once: true },
        );
      });
    });
    vi.stubGlobal("fetch", fetchMock);

    const aborted = new AbortController();
    aborted.abort(new Error("already aborted"));
    await expect(request("/auth/me", { timeoutMs: 5000, signal: aborted.signal })).rejects.toThrow(
      "already aborted",
    );

    const controller = new AbortController();
    const pending = request("/auth/me", { timeoutMs: 5000, signal: controller.signal });
    controller.abort(new Error("linked abort"));
    await expect(pending).rejects.toThrow("linked abort");
  });

  test("requestFormDataWithUploadProgress maps xhr status text when detail missing", async () => {
    class MockXHR {
      static instances: MockXHR[] = [];
      upload = { addEventListener: vi.fn() };
      status = 500;
      statusText = "Server exploded";
      response = null;
      open = vi.fn();
      setRequestHeader = vi.fn();
      send = vi.fn();
      addEventListener = vi.fn((event: string, handler: () => void) => {
        if (event === "load") {
          this.loadHandler = handler;
        }
      });
      loadHandler: (() => void) | null = null;

      constructor() {
        MockXHR.instances.push(this);
      }
    }

    vi.stubGlobal("XMLHttpRequest", MockXHR as unknown as typeof XMLHttpRequest);
    const formData = new FormData();
    const pending = requestFormDataWithUploadProgress("/upload", formData, "token");
    MockXHR.instances.at(-1)!.loadHandler?.();
    await expect(pending).rejects.toMatchObject({ message: "Server exploded", status: 500 });
  });

  test("getElaborazioneBatch uses cache, bustCache and expiry cleanup", async () => {
    vi.useFakeTimers();
    const fetchMock = vi.fn().mockImplementation(() =>
      jsonResponse({ id: "batch-1", status: "ready" }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const token = "cache-token";
    await expect(getElaborazioneBatch(token, "batch-1")).resolves.toMatchObject({ id: "batch-1" });
    await expect(getElaborazioneBatch(token, "batch-1")).resolves.toMatchObject({ id: "batch-1" });
    expect(fetchMock).toHaveBeenCalledTimes(1);

    await expect(getElaborazioneBatch(token, "batch-1", { bustCache: true })).resolves.toMatchObject({
      id: "batch-1",
    });
    expect(fetchMock).toHaveBeenCalledTimes(2);

    await vi.advanceTimersByTimeAsync(60_000);
  });

  test("createElaborazioneBatchWebSocket returns null without window", () => {
    vi.stubGlobal("window", undefined);
    expect(createElaborazioneBatchWebSocket("batch-1", "token")).toBeNull();
  });

  test("createElaborazioneBatchWebSocket opens websocket in browser", () => {
    class MockWebSocket {
      url: string;
      constructor(url: string) {
        this.url = url;
      }
    }
    vi.stubGlobal("window", {
      location: { protocol: "https:", host: "gaia.example.com" },
    } as Window & typeof globalThis);
    vi.stubGlobal("WebSocket", MockWebSocket as unknown as typeof WebSocket);
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "/api");

    const socket = createElaborazioneBatchWebSocket("batch-1", "token");
    expect(socket).toBeInstanceOf(MockWebSocket);
    expect((socket as MockWebSocket).url).toContain("/elaborazioni/ws/batch-1");
    expect((socket as MockWebSocket).url).toContain("token=token");
  });
});
