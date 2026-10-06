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

  test.each([
    { detail: "Denied", message: "Denied" },
    { detail: "", message: "" },
    { detail: { message: "Denied", code: "forbidden" }, message: "Denied" },
    { detail: { message: "", code: "forbidden" }, message: "" },
    { detail: { message: 0 }, message: '{"message":0}' },
    { detail: { message: null }, message: '{"message":null}' },
    { detail: { code: "forbidden" }, message: '{"code":"forbidden"}' },
    { detail: [{ loc: ["body", "name"], msg: "Required" }], message: '[{"loc":["body","name"],"msg":"Required"}]' },
    { detail: [], message: "[]" },
    { detail: 0, message: "0" },
    { detail: false, message: "false" },
    { detail: null, message: "Request failed" },
    { detail: undefined, message: "Request failed" },
  ])("preserves message and detailData for $detail", async ({ detail, message }) => {
    const response = new Response(JSON.stringify({ detail }), {
      status: 403,
      statusText: "Forbidden",
    });
    const jsonSpy = vi.spyOn(response, "json");
    const fetchMock = vi.fn().mockResolvedValue(response);
    vi.stubGlobal("fetch", fetchMock);

    await expect(request("/error")).rejects.toMatchObject({
      name: "ApiError",
      message,
      status: 403,
      detailData: detail,
    });
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(jsonSpy).toHaveBeenCalledTimes(1);
  });

  test.each([
    { body: "not-json", statusText: "Bad Gateway", message: "Bad Gateway" },
    { body: "null", statusText: "Bad Gateway", message: "Bad Gateway" },
    { body: "not-json", statusText: "", message: "Request failed" },
    { body: "null", statusText: "", message: "Request failed" },
  ])("retains the status fallback for $body / $statusText", async ({ body, statusText, message }) => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(body, {
      status: 502,
      statusText,
    })));

    await expect(request("/error")).rejects.toMatchObject({
      name: "ApiError",
      message,
      status: 502,
      detailData: undefined,
    });
  });

  test("retains parsed detailData when serialization fails", async () => {
    const detail = { code: "invalid", value: BigInt(1) };
    const response = new Response(null, { status: 400, statusText: "Bad Request" });
    vi.spyOn(response, "json").mockResolvedValue({ detail });
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response));

    await expect(request("/error")).rejects.toMatchObject({
      name: "ApiError",
      message: "Bad Request",
      status: 400,
      detailData: detail,
    });
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

  test("retains default detail when serialization fails without status text", async () => {
    const detail = { value: BigInt(1) };
    const response = new Response(null, { status: 400 });
    vi.spyOn(response, "json").mockResolvedValue({ detail });
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response));

    await expect(request("/error")).rejects.toMatchObject({
      message: "Request failed",
      status: 400,
      detailData: detail,
    });
  });

  test.each([
    { label: "symbol", detail: Symbol("invalid") },
    { label: "function", detail: () => undefined },
  ])("does not add a fallback when serialization returns undefined: $label", async ({ detail }) => {
    const response = new Response(null, { status: 400, statusText: "Bad Request" });
    vi.spyOn(response, "json").mockResolvedValue({ detail });
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response));

    await expect(request("/error")).rejects.toMatchObject({
      message: "",
      status: 400,
      detailData: detail,
    });
  });

  test("request and requestBlob retain default messages for malformed or incomplete errors", async () => {
    const plainJson = new Response('{"ok":true}', { status: 200 });
    plainJson.headers.delete("content-type");
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({ detail: null }), { status: 400 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ detail: { message: 7 } }), { status: 400 }))
      .mockResolvedValueOnce(new Response("not-json", { status: 500, statusText: "" }))
      .mockResolvedValueOnce(new Response(null, { status: 200 }))
      .mockResolvedValueOnce(plainJson)
      .mockResolvedValueOnce(new Response(JSON.stringify({ detail: null }), { status: 500 }))
      .mockResolvedValueOnce(new Response("not-json", { status: 500, statusText: "" }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(request("/null-detail")).rejects.toMatchObject({ message: "Request failed" });
    await expect(request("/numeric-message")).rejects.toMatchObject({
      message: JSON.stringify({ message: 7 }),
    });
    await expect(request("/invalid-error")).rejects.toMatchObject({ message: "Request failed" });
    await expect(request<void>("/empty-without-content-type")).resolves.toBeUndefined();
    await expect(request<{ ok: boolean }>("/json-without-content-type")).resolves.toEqual({ ok: true });
    await expect(requestBlob("/blob-null-detail")).rejects.toMatchObject({ message: "Request failed" });
    await expect(requestBlob("/invalid-blob-error")).rejects.toMatchObject({ message: "Request failed" });
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

    for (const [response, statusText, message] of [
      [{ detail: "plain detail" }, "", "plain detail"],
      [{ detail: { code: "invalid" } }, "", JSON.stringify({ code: "invalid" })],
      [null, "Rejected", "Rejected"],
      [null, "", "Request failed"],
    ] as const) {
      const rejected = requestFormDataWithUploadProgress("/import", formData, "token");
      const rejectedXhr = MockXHR.instances.at(-1)!;
      rejectedXhr.status = 400;
      rejectedXhr.statusText = statusText;
      rejectedXhr.response = response;
      rejectedXhr.loadHandler?.();
      await expect(rejected).rejects.toMatchObject({ message });
    }
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

describe("upload error detail contract", () => {
  class MockUploadXHR {
    static current: MockUploadXHR;
    upload = { addEventListener: vi.fn() };
    status = 422;
    statusText = "Unprocessable Entity";
    response: unknown;
    open = vi.fn();
    setRequestHeader = vi.fn();
    send = vi.fn();
    loadHandler!: () => void;

    constructor() {
      MockUploadXHR.current = this;
    }

    addEventListener(event: string, handler: () => void) {
      if (event === "load") {
        this.loadHandler = handler;
      }
    }
  }

  beforeEach(() => {
    vi.stubGlobal("XMLHttpRequest", MockUploadXHR);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  test.each([
    { detail: "Denied", message: "Denied" },
    { detail: "", message: "" },
    { detail: { message: "Denied", code: "invalid" }, message: "Denied" },
    { detail: { message: "" }, message: "" },
    { detail: { message: 0 }, message: '{"message":0}' },
    { detail: { message: null }, message: '{"message":null}' },
    { detail: { code: "invalid" }, message: '{"code":"invalid"}' },
    { detail: [{ msg: "Required" }], message: '[{"msg":"Required"}]' },
    { detail: [], message: "[]" },
    { detail: 0, message: "0" },
    { detail: false, message: "false" },
    { detail: null, message: "Unprocessable Entity" },
    { detail: undefined, message: "Unprocessable Entity" },
  ])("preserves upload message and detailData for $detail", async ({ detail, message }) => {
    const pending = requestFormDataWithUploadProgress("/upload", new FormData(), "token");
    MockUploadXHR.current.response = { detail };
    MockUploadXHR.current.loadHandler();

    await expect(pending).rejects.toMatchObject({ name: "ApiError", message, detailData: detail, status: 422 });
  });

  test.each([null, undefined, "not-json", 0, false, []])("falls back to statusText for response %s", async (response) => {
    const pending = requestFormDataWithUploadProgress("/upload", new FormData(), "token");
    MockUploadXHR.current.response = response;
    MockUploadXHR.current.loadHandler();

    await expect(pending).rejects.toMatchObject({ message: "Unprocessable Entity", detailData: undefined, status: 422 });
  });

  test("does not swallow serialization errors from an upload detail", () => {
    void requestFormDataWithUploadProgress("/upload", new FormData(), "token");
    MockUploadXHR.current.response = { detail: { value: BigInt(1) } };

    expect(() => MockUploadXHR.current.loadHandler()).toThrow(TypeError);
  });
});

describe("request empty response precedence", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  test.each([204, 205])("skips headers and body for status %s", async (status) => {
    const response = new Response(null, {
      status,
      headers: { "content-length": "12", "content-type": "application/json" },
    });
    const headersSpy = vi.spyOn(response.headers, "get");
    const jsonSpy = vi.spyOn(response, "json");
    const textSpy = vi.spyOn(response, "text");
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response));

    await expect(request("/empty")).resolves.toBeUndefined();
    expect(headersSpy).not.toHaveBeenCalled();
    expect(jsonSpy).not.toHaveBeenCalled();
    expect(textSpy).not.toHaveBeenCalled();
  });

  test.each([null, "application/json", "text/plain"])("skips body for exact zero length with content type %s", async (contentType) => {
    const response = new Response("not-json", { headers: { "content-length": "0" } });
    response.headers.delete("content-type");
    if (contentType !== null) {
      response.headers.set("content-type", contentType);
    }
    const headersSpy = vi.spyOn(response.headers, "get");
    const jsonSpy = vi.spyOn(response, "json");
    const textSpy = vi.spyOn(response, "text");
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response));

    await expect(request("/empty")).resolves.toBeUndefined();
    expect(headersSpy.mock.calls).toEqual([["content-length"]]);
    expect(jsonSpy).not.toHaveBeenCalled();
    expect(textSpy).not.toHaveBeenCalled();
  });

  test.each([null, "00", "0 ", " 0", "12"])("parses JSON for non-exact zero length %s", async (contentLength) => {
    const response = new Response('{"ok":true}', { headers: { "content-type": "application/json" } });
    vi.spyOn(response.headers, "get").mockImplementation((header) => (
      header === "content-length" ? contentLength : "application/json"
    ));
    const jsonSpy = vi.spyOn(response, "json");
    const textSpy = vi.spyOn(response, "text");
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response));

    await expect(request("/json")).resolves.toEqual({ ok: true });
    expect(jsonSpy).toHaveBeenCalledTimes(1);
    expect(textSpy).not.toHaveBeenCalled();
  });

  test("decodes HTTP errors before applying the zero length rule", async () => {
    const response = new Response('{"detail":"Forbidden"}', {
      status: 403,
      headers: { "content-length": "0", "content-type": "application/json" },
    });
    const headersSpy = vi.spyOn(response.headers, "get");
    const jsonSpy = vi.spyOn(response, "json");
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response));

    await expect(request("/forbidden")).rejects.toMatchObject({ message: "Forbidden", status: 403 });
    expect(headersSpy).not.toHaveBeenCalled();
    expect(jsonSpy).toHaveBeenCalledTimes(1);
  });

  test.each([
    { body: "", result: undefined },
    { body: "null", result: null },
    { body: "false", result: false },
    { body: "0", result: 0 },
  ])("preserves empty and falsy JSON bodies without content type: $body", async ({ body, result }) => {
    const response = new Response(body);
    response.headers.delete("content-type");
    const textSpy = vi.spyOn(response, "text");
    const jsonSpy = vi.spyOn(response, "json");
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response));

    await expect(request("/body")).resolves.toBe(result);
    expect(textSpy).toHaveBeenCalledTimes(1);
    expect(jsonSpy).not.toHaveBeenCalled();
  });

  test.each([
    { body: "", contentType: "application/json" },
    { body: " ", contentType: null },
    { body: "not-json", contentType: null },
    { body: "not-json", contentType: "text/plain" },
  ])("preserves parsing failures for $body / $contentType", async ({ body, contentType }) => {
    const response = new Response(body);
    response.headers.delete("content-type");
    if (contentType !== null) {
      response.headers.set("content-type", contentType);
    }
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response));

    await expect(request("/invalid")).rejects.toBeInstanceOf(SyntaxError);
  });
});

describe("request cancellation lifecycle", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  test.each([undefined, 0, Number.NaN])("forwards the original signal without a truthy timeout: %s", async (timeoutMs) => {
    const external = new AbortController();
    const fetchMock = vi.fn().mockResolvedValue(new Response(null, { status: 204 }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(request("/empty", { timeoutMs, signal: external.signal })).resolves.toBeUndefined();
    expect(fetchMock.mock.calls[0][1].signal).toBe(external.signal);
    expect(external.signal.aborted).toBe(false);
    expect(vi.getTimerCount()).toBe(0);
  });

  test.each([true, false])("preserves external abort reason and clears the timer (already aborted: %s)", async (alreadyAborted) => {
    const external = new AbortController();
    const reason = new Error("caller cancelled");
    if (alreadyAborted) {
      external.abort(reason);
    }
    const fetchMock = vi.fn().mockImplementation((_input: string, init: RequestInit) => {
      const signal = init.signal!;
      return new Promise((_resolve, reject) => {
        if (signal.aborted) {
          reject(signal.reason);
        } else {
          signal.addEventListener("abort", () => reject(signal.reason), { once: true });
        }
      });
    });
    vi.stubGlobal("fetch", fetchMock);

    const pending = request("/pending", { timeoutMs: 25, signal: external.signal });
    const rejection = expect(pending).rejects.toBe(reason);
    external.abort(reason);
    await rejection;

    const forwardedSignal = fetchMock.mock.calls[0][1].signal;
    expect(forwardedSignal).not.toBe(external.signal);
    expect(forwardedSignal.reason).toBe(reason);
    expect(vi.getTimerCount()).toBe(0);
    await vi.advanceTimersByTimeAsync(25);
    expect(forwardedSignal.reason).toBe(reason);
  });

  test("aborts at the deadline and translates the fetch rejection into ApiError", async () => {
    const fetchMock = vi.fn().mockImplementation((_input: string, init: RequestInit) => new Promise((_resolve, reject) => {
      init.signal!.addEventListener("abort", () => reject(init.signal!.reason), { once: true });
    }));
    vi.stubGlobal("fetch", fetchMock);
    const external = new AbortController();
    const pending = request("/pending", { timeoutMs: 25, signal: external.signal });
    const rejection = expect(pending).rejects.toMatchObject({
      name: "ApiError",
      message: SESSION_BOOTSTRAP_TIMEOUT_MESSAGE,
      status: undefined,
    });
    const forwardedSignal = fetchMock.mock.calls[0][1].signal;

    await vi.advanceTimersByTimeAsync(24);
    expect(forwardedSignal.aborted).toBe(false);
    await vi.advanceTimersByTimeAsync(1);
    await rejection;
    expect(forwardedSignal.reason).toBeInstanceOf(Error);
    expect(forwardedSignal.reason.message).toBe(SESSION_BOOTSTRAP_TIMEOUT_MESSAGE);
    expect(external.signal.aborted).toBe(false);
    expect(vi.getTimerCount()).toBe(0);
  });

  test("preserves network errors and clears a pending timeout", async () => {
    const reason = new Error("offline");
    const fetchMock = vi.fn().mockRejectedValue(reason);
    vi.stubGlobal("fetch", fetchMock);

    await expect(request("/offline", { timeoutMs: 25 })).rejects.toBe(reason);
    expect(vi.getTimerCount()).toBe(0);
    await vi.advanceTimersByTimeAsync(25);
    expect(fetchMock.mock.calls[0][1].signal.aborted).toBe(false);
  });

  test.each([200, 403])("ends the timeout when fetch resolves, before decoding a delayed body: %s", async (status) => {
    const response = new Response(null, { status, headers: { "content-type": "application/json" } });
    let finishBody!: (payload: unknown) => void;
    vi.spyOn(response, "json").mockImplementation(() => {
      expect(vi.getTimerCount()).toBe(0);
      return new Promise((resolve) => {
        finishBody = resolve;
      });
    });
    const fetchMock = vi.fn().mockResolvedValue(response);
    vi.stubGlobal("fetch", fetchMock);
    const pending = request("/delayed-body", { timeoutMs: 25 });
    const outcome = status === 200
      ? expect(pending).resolves.toEqual({ ok: true })
      : expect(pending).rejects.toMatchObject({ message: "Forbidden", status: 403 });

    await vi.advanceTimersByTimeAsync(50);
    expect(fetchMock.mock.calls[0][1].signal.aborted).toBe(false);
    finishBody(status === 200 ? { ok: true } : { detail: "Forbidden" });
    await outcome;
    expect(vi.getTimerCount()).toBe(0);
  });
});
