import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import {
  ApiError,
  SESSION_BOOTSTRAP_TIMEOUT_MESSAGE,
  createQueryString,
  getApiBaseUrl,
  getWebSocketBaseUrl,
  isAuthError,
  request,
  requestBlob,
  requestFormDataWithUploadProgress,
} from "@/lib/api";

describe("api core helpers", () => {
  beforeEach(() => {
    vi.unstubAllEnvs();
    vi.unstubAllGlobals();
  });

  afterEach(() => {
    vi.unstubAllEnvs();
    vi.unstubAllGlobals();
  });

  test("ApiError and isAuthError identify auth failures", () => {
    const error = new ApiError("denied", { code: "x" }, 403);
    expect(error.name).toBe("ApiError");
    expect(error.detailData).toEqual({ code: "x" });
    expect(isAuthError(error)).toBe(true);
    expect(isAuthError(new ApiError("bad", undefined, 500))).toBe(false);
    expect(isAuthError(new Error("plain"))).toBe(false);
  });

  test("getApiBaseUrl normalizes env and browser-safe values", () => {
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "/custom/");
    expect(getApiBaseUrl()).toBe("/custom");

    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "");
    expect(getApiBaseUrl()).toBe("/api");

    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "http://localhost:8000");
    vi.stubGlobal("window", {} as Window & typeof globalThis);
    expect(getApiBaseUrl()).toBe("/api");
  });

  test("createQueryString skips empty values", () => {
    expect(createQueryString({})).toBe("");
    expect(createQueryString({ q: "  rossi  ", empty: "   ", skip: undefined })).toBe("?q=rossi");
  });

  test("getWebSocketBaseUrl maps http(s) and relative browser bases", () => {
    vi.stubGlobal("window", undefined);
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "https://api.example.com/v1");
    expect(getWebSocketBaseUrl()).toBe("wss://api.example.com/v1");

    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "http://api.example.com/v1");
    expect(getWebSocketBaseUrl()).toBe("ws://api.example.com/v1");

    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "/api");
    expect(getWebSocketBaseUrl()).toBe("/api");

    vi.stubGlobal("window", {
      location: { protocol: "https:", host: "gaia.example.com" },
    } as Window & typeof globalThis);
    expect(getWebSocketBaseUrl()).toBe("wss://gaia.example.com/api");

    vi.stubGlobal("window", {
      location: { protocol: "http:", host: "localhost:8080" },
    } as Window & typeof globalThis);
    expect(getWebSocketBaseUrl()).toBe("ws://localhost:8080/api");
  });

  test("request handles structured errors, empty bodies and form uploads", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ detail: { message: "Validation failed" } }), {
          status: 422,
          headers: { "content-type": "application/json" },
        }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ detail: { field: "x" } }), {
          status: 400,
          headers: { "content-type": "application/json" },
        }),
      )
      .mockResolvedValueOnce(new Response(null, { status: 205 }))
      .mockResolvedValueOnce(new Response("", { status: 200, headers: { "content-length": "0" } }))
      .mockResolvedValueOnce(new Response('{"ok":true}', { status: 200 }))
      .mockResolvedValueOnce(new Response("network", { status: 502, statusText: "Bad Gateway" }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(request("/bad-message")).rejects.toMatchObject({
      message: "Validation failed",
      status: 422,
    });
    await expect(request("/bad-json")).rejects.toMatchObject({
      message: JSON.stringify({ field: "x" }),
      status: 400,
    });
    await expect(request<void>("/empty-205")).resolves.toBeUndefined();
    await expect(request<void>("/empty-length")).resolves.toBeUndefined();
    await expect(request<{ ok: boolean }>("/plain-json")).resolves.toEqual({ ok: true });
    await expect(request("/bad-status")).rejects.toMatchObject({
      message: "Bad Gateway",
      status: 502,
    });

    const formData = new FormData();
    formData.append("file", new Blob(["x"]), "file.csv");
    fetchMock.mockResolvedValueOnce(new Response(JSON.stringify({ uploaded: true }), { status: 200 }));
    await expect(
      request<{ uploaded: boolean }>("/upload", { method: "POST", body: formData }),
    ).resolves.toEqual({ uploaded: true });
    expect(fetchMock.mock.calls.at(-1)?.[1]?.headers).not.toHaveProperty("Content-Type");
  });

  test("request propagates external abort and non-timeout fetch failures", async () => {
    const fetchMock = vi.fn().mockImplementation((_input: string, init?: RequestInit) => {
      if (init?.signal?.aborted) {
        return Promise.reject(init.signal.reason ?? new Error("aborted"));
      }
      return Promise.resolve(new Response(JSON.stringify({ ok: true }), { status: 200 }));
    });
    vi.stubGlobal("fetch", fetchMock);

    const external = new AbortController();
    external.abort(new Error("user abort"));
    await expect(request("/auth/me", { signal: external.signal })).rejects.toThrow("user abort");

    fetchMock.mockRejectedValueOnce(new Error("offline"));
    await expect(request("/auth/me")).rejects.toThrow("offline");
  });

  test("requestBlob returns blob and maps errors", async () => {
    const blob = new Blob(["pdf"]);
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(new Response(blob, { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ detail: "Forbidden" }), { status: 403 }))
      .mockResolvedValueOnce(new Response(null, { status: 500, statusText: "Server error" }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(requestBlob("/export")).resolves.toEqual(blob);
    await expect(requestBlob("/forbidden")).rejects.toMatchObject({ message: "Forbidden", status: 403 });
    await expect(requestBlob("/broken")).rejects.toMatchObject({ message: "Server error", status: 500 });
  });

  test("requestFormDataWithUploadProgress resolves and rejects xhr outcomes", async () => {
    class MockXHR {
      static instances: MockXHR[] = [];
      upload = { addEventListener: vi.fn() };
      status = 200;
      statusText = "OK";
      response: unknown = { imported: 3 };
      open = vi.fn();
      setRequestHeader = vi.fn();
      send = vi.fn();
      addEventListener = vi.fn((event: string, handler: () => void) => {
        if (event === "load") {
          this.loadHandler = handler;
        }
        if (event === "error") {
          this.errorHandler = handler;
        }
      });
      loadHandler: (() => void) | null = null;
      errorHandler: (() => void) | null = null;

      constructor() {
        MockXHR.instances.push(this);
      }
    }

    vi.stubGlobal("XMLHttpRequest", MockXHR as unknown as typeof XMLHttpRequest);

    const formData = new FormData();
    formData.append("file", new Blob(["x"]), "file.csv");
    const progress: number[] = [];
    const pending = requestFormDataWithUploadProgress<{ imported: number }>(
      "/import",
      formData,
      "token",
      (percent) => progress.push(percent),
    );
    const xhr = MockXHR.instances.at(-1)!;
    xhr.upload.addEventListener.mock.calls.find(([event]) => event === "progress")?.[1]?.({
      lengthComputable: true,
      loaded: 50,
      total: 100,
    });
    xhr.upload.addEventListener.mock.calls.find(([event]) => event === "progress")?.[1]?.({
      lengthComputable: false,
      loaded: 10,
      total: 0,
    });
    xhr.loadHandler?.();
    await expect(pending).resolves.toEqual({ imported: 3 });
    expect(progress).toEqual([50, 100]);

    const failing = requestFormDataWithUploadProgress("/import", formData, "token");
    const failingXhr = MockXHR.instances.at(-1)!;
    failingXhr.status = 422;
    failingXhr.response = { detail: { message: "CSV invalido" } };
    failingXhr.loadHandler?.();
    await expect(failing).rejects.toMatchObject({ message: "CSV invalido", status: 422 });

    const network = requestFormDataWithUploadProgress("/import", formData, "token");
    MockXHR.instances.at(-1)!.errorHandler?.();
    await expect(network).rejects.toMatchObject({ message: "Errore di rete durante upload CSV" });
  });

  test("request timeout uses bootstrap timeout message", async () => {
    vi.useFakeTimers();
    const fetchMock = vi.fn().mockImplementation((_input: string, init?: RequestInit) => new Promise((_, reject) => {
      init?.signal?.addEventListener("abort", () => reject(new Error("aborted")), { once: true });
    }));
    vi.stubGlobal("fetch", fetchMock);

    const pending = request("/auth/me", { timeoutMs: 25 });
    const timeoutExpectation = expect(pending).rejects.toMatchObject({
      message: SESSION_BOOTSTRAP_TIMEOUT_MESSAGE,
      name: "ApiError",
    });
    await vi.advanceTimersByTimeAsync(25);
    await timeoutExpectation;
    vi.useRealTimers();
  });
});
