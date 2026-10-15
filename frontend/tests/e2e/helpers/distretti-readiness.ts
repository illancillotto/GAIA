import { expect, type Page, type Request, type Response } from "@playwright/test";

type LoadKind = "districts" | "history" | "kpi";
type LoadRecord = { kind: LoadKind; started: number; pending: boolean; data?: unknown; error?: string };

export type DistrettiSnapshot = {
  loading: boolean;
  error: boolean;
  year: number;
  total: number | null;
  rows: number;
  empty: boolean;
};

export function readDistrettiSnapshot(): DistrettiSnapshot {
  const heading = Array.from(document.querySelectorAll("h2"))
    .find((element) => element.textContent?.trim() === "Tabella distretti");
  const article = heading?.closest("article");
  const texts = Array.from(article?.querySelectorAll("p") ?? []).map((element) => element.textContent?.trim());
  const totalText = texts.find((value) => /^\d+ distretti$/.test(value ?? ""));
  const yearLabel = Array.from(document.querySelectorAll("label"))
    .find((element) => element.textContent?.includes("Anno campagna"));
  return {
    loading: article == null || article.textContent?.includes("Caricamento…") === true,
    error: Array.from(document.querySelectorAll("h1,h2,h3,p,span,strong"))
      .some((element) => element.textContent?.trim() === "Errore caricamento"),
    year: Number(yearLabel?.querySelector("select")?.value ?? NaN),
    total: totalText == null ? null : Number(totalText.split(" ")[0]),
    rows: article?.querySelectorAll("table.data-table tbody tr").length ?? 0,
    empty: article?.textContent?.includes("Nessun distretto") === true,
  };
}

function loadKind(url: string): LoadKind | null {
  const pathname = new URL(url).pathname.replace(/\/$/, "");
  if (pathname.endsWith("/catasto/distretti")) return "districts";
  if (pathname.endsWith("/catasto/import/history")) return "history";
  if (/\/catasto\/distretti\/[^/]+\/kpi$/.test(pathname)) return "kpi";
  return null;
}

function originalRequest(request: Request): Request {
  let original = request;
  while (original.redirectedFrom()) original = original.redirectedFrom()!;
  return original;
}

export function observeDistrettiLoading(page: Page, initialYear: number) {
  const loads = new Map<Request, LoadRecord>();
  let requestSequence = 0;
  let firstHistoryBoundary: number | null = null;
  const onRequest = (request: Request) => {
    const kind = loadKind(request.url());
    const resource = request.resourceType();
    if (kind && (resource === "fetch" || resource === "xhr") && request.method() === "GET" && !request.redirectedFrom()) {
      loads.set(request, { kind, started: ++requestSequence, pending: true });
    }
  };
  const onResponse = async (response: Response) => {
    const record = loads.get(originalRequest(response.request()));
    if (!record || (response.status() >= 300 && response.status() < 400)) return;
    try {
      if (record.kind !== "kpi") {
        if (!response.ok()) throw new Error(`HTTP ${response.status()}`);
        record.data = await response.json();
        if (!Array.isArray(record.data)) throw new Error("Expected an array response");
        if (record.kind === "history" && firstHistoryBoundary == null) firstHistoryBoundary = requestSequence;
      }
    } catch (error) {
      record.error = String(error);
    } finally {
      record.pending = false;
    }
  };
  const onFailed = (request: Request) => {
    const record = loads.get(originalRequest(request));
    if (record) {
      record.error = request.failure()?.errorText ?? "Request failed";
      record.pending = false;
    }
  };
  page.on("request", onRequest);
  page.on("response", onResponse);
  page.on("requestfailed", onFailed);

  return {
    state(snapshot: DistrettiSnapshot): string {
      const records = [...loads.values()];
      const failure = records.find((record) => record.kind !== "kpi" && record.error);
      if (snapshot.error || failure) return `error: ${failure?.error ?? "Errore caricamento"}`;
      if (snapshot.loading || records.some((record) => record.pending)) return "loading";
      const districtLoads = records.filter((record) => record.kind === "districts");
      const historyLoads = records.filter((record) => record.kind === "history");
      const districts = districtLoads.at(-1)?.data;
      const history = historyLoads.at(-1)?.data;
      if (!Array.isArray(districts) || !Array.isArray(history)) return "loading";
      if (districts.some((item) => item == null || typeof item.num_distretto !== "string") ||
          history.some((item) => item == null || typeof item.status !== "string")) {
        return "error: Invalid district/history response";
      }
      const years = history.filter((item) => item.status === "completed" && typeof item.anno_campagna === "number")
        .map((item) => item.anno_campagna as number);
      const expectedYear = years.length ? Math.max(...years) : initialYear;
      if (expectedYear !== initialYear && (firstHistoryBoundary == null ||
          districtLoads.at(-1)!.started <= firstHistoryBoundary || historyLoads.at(-1)!.started <= firstHistoryBoundary)) {
        return "loading";
      }
      if (snapshot.year !== expectedYear) {
        return "loading";
      }
      const total = districts.filter((item) => item.num_distretto !== "FD").length;
      if (snapshot.total !== total) return "loading";
      if (total === 0) return snapshot.empty && snapshot.rows === 0 ? "ready" : "loading";
      return snapshot.rows > 0 && !snapshot.empty ? "ready" : "loading";
    },
    dispose() {
      page.off("request", onRequest);
      page.off("response", onResponse);
      page.off("requestfailed", onFailed);
    },
  };
}

export async function openReadyDistrettiList(page: Page): Promise<number> {
  const initialYear = await page.evaluate(() => new Date().getFullYear());
  const observer = observeDistrettiLoading(page, initialYear);
  try {
    await page.goto("/catasto/distretti");
    await expect(page.getByText("Tabella distretti")).toBeVisible();
    let snapshot: DistrettiSnapshot;
    await expect.poll(async () => {
      snapshot = await page.evaluate(readDistrettiSnapshot);
      return observer.state(snapshot);
    }, { message: "District list must finish loading successfully before the empty-dataset skip" }).toBe("ready");
    return snapshot!.rows;
  } finally {
    observer.dispose();
  }
}
