import { EventEmitter } from "node:events";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { Page, Request, Response } from "@playwright/test";

const playwright = vi.hoisted(() => ({ visible: vi.fn(), poll: vi.fn() }));
vi.mock("@playwright/test", () => ({
  expect: Object.assign(() => ({ toBeVisible: playwright.visible }), {
    poll: (callback: () => Promise<string>, options: unknown) => ({
      toBe: (expected: string) => playwright.poll(callback, options, expected),
    }),
  }),
}));

import { observeDistrettiLoading, openReadyDistrettiList, readDistrettiSnapshot, type DistrettiSnapshot } from "../e2e/helpers/distretti-readiness";

const populated: DistrettiSnapshot = { loading: false, error: false, year: 2026, total: 1, rows: 1, empty: false };
const empty: DistrettiSnapshot = { ...populated, total: 0, rows: 0, empty: true };
const districts = [{ num_distretto: "1" }];
const history = [{ status: "completed", anno_campagna: 2026 }];

function request(path: string, options: { redirect?: Request; method?: string; failure?: string; resource?: string } = {}): Request {
  return {
    url: () => `http://private/api/catasto/${path}`,
    method: () => options.method ?? "GET",
    resourceType: () => options.resource ?? "fetch",
    redirectedFrom: () => options.redirect ?? null,
    failure: () => options.failure ? { errorText: options.failure } : null,
  } as Request;
}

async function respond(bus: EventEmitter, owned: Request, data: unknown, status = 200) {
  bus.emit("response", {
    request: () => owned,
    status: () => status,
    ok: () => status >= 200 && status < 300,
    json: async () => data,
  } as Response);
  await Promise.resolve();
}

function fixture() {
  const bus = new EventEmitter();
  const observer = observeDistrettiLoading(bus as unknown as Page, 2026);
  function start(path: string, options?: Parameters<typeof request>[1]) {
    const owned = request(path, options);
    bus.emit("request", owned);
    return owned;
  }
  async function load(rows: unknown = districts, imports: unknown = history) {
    const list = start("distretti");
    const batches = start("import/history");
    await respond(bus, list, rows);
    await respond(bus, batches, imports);
  }
  return { bus, observer, start, load };
}

afterEach(() => { document.body.innerHTML = ""; vi.resetAllMocks(); });

describe("district readiness contract without browser or services", () => {
  it("waits for list, history, KPI and rendered rows separately", async () => {
    const { bus, observer, start } = fixture();
    const list = start("distretti");
    const batches = start("import/history");
    expect(observer.state(populated)).toBe("loading");
    await respond(bus, list, districts);
    expect(observer.state(populated)).toBe("loading");
    const kpi = start("distretti/id/kpi?anno=2026");
    await respond(bus, batches, history);
    expect(observer.state(populated)).toBe("loading");
    await respond(bus, kpi, {});
    expect(observer.state({ ...populated, loading: true })).toBe("loading");
    expect(observer.state({ ...populated, rows: 0 })).toBe("loading");
    expect(observer.state({ ...populated, total: null })).toBe("loading");
    expect(observer.state(populated)).toBe("ready");
  });

  it("rejects a transient empty state during an imported-year reload", async () => {
    const { observer, load, start, bus } = fixture();
    const older = [{ status: "completed", anno_campagna: 2025 }];
    await load([], older);
    expect(observer.state(empty)).toBe("loading");
    expect(observer.state({ ...empty, year: 2025 })).toBe("loading");
    const list = start("distretti");
    const batches = start("import/history");
    await respond(bus, list, []);
    expect(observer.state({ ...empty, year: 2025 })).toBe("loading");
    await respond(bus, batches, older);
    expect(observer.state({ ...empty, year: 2025 })).toBe("ready");
  });

  it("does not mistake duplicate initial effects for the imported-year reload", async () => {
    const { observer, start, bus, load } = fixture();
    const older = [{ status: "completed", anno_campagna: 2025 }];
    const firstList = start("distretti");
    const firstHistory = start("import/history");
    const duplicateList = start("distretti");
    const duplicateHistory = start("import/history");
    await respond(bus, firstList, []);
    await respond(bus, firstHistory, older);
    await respond(bus, duplicateList, []);
    await respond(bus, duplicateHistory, older);
    expect(observer.state({ ...empty, year: 2025 })).toBe("loading");
    await load([], older);
    expect(observer.state({ ...empty, year: 2025 })).toBe("ready");
  });

  it("does not count duplicates started between history headers and body as a reload", async () => {
    const { observer, start, bus, load } = fixture();
    const older = [{ status: "completed", anno_campagna: 2025 }];
    const firstList = start("distretti");
    const firstHistory = start("import/history");
    await respond(bus, firstList, []);
    let releaseBody!: (value: unknown) => void;
    const body = new Promise((resolve) => { releaseBody = resolve; });
    bus.emit("response", { request: () => firstHistory, status: () => 200, ok: () => true, json: () => body } as unknown as Response);
    const duplicateList = start("distretti");
    const duplicateHistory = start("import/history");
    releaseBody(older);
    await Promise.resolve();
    await respond(bus, duplicateList, []);
    await respond(bus, duplicateHistory, older);
    expect(observer.state({ ...empty, year: 2025 })).toBe("loading");
    await load([], older);
    expect(observer.state({ ...empty, year: 2025 })).toBe("ready");
  });

  it.each([{ rows: [] }, { rows: [{ num_distretto: "FD" }] }])("permits only confirmed successful empty lists: %j", async ({ rows }) => {
    const { observer, load } = fixture();
    await load(rows);
    expect(observer.state({ ...empty, empty: false })).toBe("loading");
    expect(observer.state({ ...empty, rows: 1 })).toBe("loading");
    expect(observer.state(empty)).toBe("ready");
    expect(observer.state({ ...empty, error: true })).toMatch(/^error:/);
  });

  it("never treats an unrendered nonempty response as an empty dataset", async () => {
    const { observer, load } = fixture();
    await load();
    expect(observer.state(empty)).toBe("loading");
    expect(observer.state({ ...populated, empty: true })).toBe("loading");
  });

  it("retains pagination and ignores incomplete imports when selecting the latest year", async () => {
    const { observer, load } = fixture();
    await load(Array.from({ length: 20 }, () => districts[0]), [
      { status: "failed", anno_campagna: 2027 }, { status: "completed", anno_campagna: "2028" }, ...history,
    ]);
    expect(observer.state({ ...populated, total: 20, rows: 12 })).toBe("ready");
  });

  it("uses the initial browser year when import history is empty", async () => {
    const { observer, load } = fixture();
    await load([], []);
    expect(observer.state(empty)).toBe("ready");
    expect(observer.state({ ...empty, year: 2025 })).toBe("loading");
  });

  it.each([401, 500])("keeps list/history HTTP %i failures out of the empty skip", async (status) => {
    const { observer, start, bus } = fixture();
    const list = start("distretti");
    await respond(bus, list, [], status);
    expect(observer.state(empty)).toContain(`error: Error: HTTP ${status}`);
  });

  it.each([[null, history], [districts, {}], [[null], history], [districts, [null]], [[{}], history]])(
    "fails closed on invalid list/history payloads: %j / %j", async (rows, imports) => {
      const { observer, load } = fixture();
      await load(rows, imports);
      expect(observer.state(empty)).toMatch(/^error:/);
    },
  );

  it("keeps JSON parse errors as failures", async () => {
    const { observer, start, bus } = fixture();
    const owned = start("import/history");
    bus.emit("response", { request: () => owned, status: () => 200, ok: () => true,
      json: async () => { throw new Error("bad JSON"); } } as unknown as Response);
    await Promise.resolve();
    expect(observer.state(empty)).toContain("bad JSON");
  });

  it("handles the slash redirect once without treating 307 as completion", async () => {
    const { observer, start, bus } = fixture();
    const list = start("distretti");
    await respond(bus, list, undefined, 307);
    expect(observer.state(populated)).toBe("loading");
    const redirected = start("distretti/", { redirect: list });
    await respond(bus, redirected, districts);
    await respond(bus, start("import/history/"), history);
    expect(observer.state(populated)).toBe("ready");
  });

  it("preserves optional KPI HTTP and transport failure fallbacks", async () => {
    const { observer, start, bus, load } = fixture();
    await load();
    await respond(bus, start("distretti/id/kpi"), undefined, 500);
    const failed = start("distretti/other/kpi", { failure: "connection reset" });
    bus.emit("requestfailed", failed);
    expect(observer.state(populated)).toBe("ready");
  });

  it("fails closed on required request failure, including after redirect", () => {
    const { observer, start, bus } = fixture();
    const original = start("distretti");
    const redirected = start("distretti/", { redirect: original });
    bus.emit("requestfailed", redirected);
    expect(observer.state(empty)).toContain("Request failed");
  });

  it("does not confuse unrelated or non-GET responses with readiness", async () => {
    const { observer, start, bus } = fixture();
    await respond(bus, start("distretti/id"), {});
    await respond(bus, start("distretti", { method: "POST" }), []);
    await respond(bus, start("distretti", { resource: "document" }), "<html/>");
    await respond(bus, start("distretti", { resource: "script" }), "javascript");
    expect(observer.state(empty)).toBe("loading");
  });

  it("supports XHR as well as fetch API requests", async () => {
    const { observer, start, bus } = fixture();
    await respond(bus, start("distretti", { resource: "xhr" }), districts);
    await respond(bus, start("import/history", { resource: "xhr" }), history);
    expect(observer.state(populated)).toBe("ready");
  });

  it("keeps missing-auth/no-request state pending and detaches all listeners", () => {
    const { observer, bus } = fixture();
    expect(observer.state(empty)).toBe("loading");
    observer.dispose();
    expect(bus.eventNames()).toEqual([]);
  });

  it("reads one coherent DOM snapshot scoped to the district table", () => {
    document.body.innerHTML = `<label>Anno campagna<select><option value="2026">2026</option></select></label>
      <article><h2>Other table</h2><table class="data-table"><tbody><tr><td>Other</td></tr></tbody></table></article>
      <article><h2>Tabella distretti</h2><p>1 distretti</p><table class="data-table"><tbody><tr><td>District</td></tr></tbody></table></article>`;
    expect(readDistrettiSnapshot()).toEqual(populated);
    document.body.innerHTML = `<label>Anno campagna<select><option value="2026">2026</option></select></label>
      <p>Errore caricamento</p><article><h2>Tabella distretti</h2><p>0 distretti</p><h3>Nessun distretto</h3></article>`;
    expect(readDistrettiSnapshot()).toEqual({ ...empty, error: true });
    document.body.innerHTML = `<article><h2>Tabella distretti</h2><p>Caricamento…</p></article>`;
    expect(readDistrettiSnapshot()).toMatchObject({ loading: true, total: null, rows: 0, empty: false });
    document.body.innerHTML = "";
    expect(readDistrettiSnapshot().loading).toBe(true);
  });

  it("opens the real list, uses default expect timeout, and disposes after readiness", async () => {
    const { bus, load } = fixture();
    const page = Object.assign(bus, {
      evaluate: vi.fn().mockResolvedValueOnce(2026).mockResolvedValue(populated),
      goto: vi.fn(async () => { await load(); }),
      getByText: vi.fn(),
    });
    playwright.poll.mockImplementation(async (callback, options, expected) => {
      expect(options).toEqual({ message: expect.any(String) });
      expect(await callback()).toBe(expected);
    });
    expect(await openReadyDistrettiList(page as unknown as Page)).toBe(1);
    expect(page.goto).toHaveBeenCalledWith("/catasto/distretti");
    expect(page.getByText).toHaveBeenCalledWith("Tabella distretti");
    expect(playwright.visible).toHaveBeenCalledOnce();
    expect(bus.listenerCount("request")).toBe(1);
  });

  it("propagates the bounded readiness timeout rather than returning zero for skip", async () => {
    const bus = new EventEmitter();
    const page = Object.assign(bus, { evaluate: vi.fn().mockResolvedValue(2026), goto: vi.fn(), getByText: vi.fn() });
    playwright.poll.mockRejectedValue(new Error("Readiness timeout"));
    await expect(openReadyDistrettiList(page as unknown as Page)).rejects.toThrow("Readiness timeout");
    expect(bus.eventNames()).toEqual([]);
  });

  it("disposes listeners if navigation fails", async () => {
    const bus = new EventEmitter();
    const page = Object.assign(bus, { evaluate: vi.fn().mockResolvedValue(2026), goto: vi.fn().mockRejectedValue(new Error("Navigation failed")) });
    await expect(openReadyDistrettiList(page as unknown as Page)).rejects.toThrow("Navigation failed");
    expect(bus.eventNames()).toEqual([]);
  });
});
