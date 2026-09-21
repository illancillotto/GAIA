import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { ImportWorkspace } from "@/components/ruolo/notice-register/import-workspace";
import { downloadImport, type ImportBatch, type ImportRow } from "@/components/ruolo/notice-register/import-client";
import { jsonResponse } from "./notice-register-fixtures";

let batch: ImportBatch;
let importedRows: ImportRow[];
let batches: ImportBatch[];
let total: number;
let fetchMock: ReturnType<typeof vi.fn>;
let writes: { path: string; body: unknown }[];
let failed: string;

beforeEach(() => {
  batch = { id: "batch-1", filename: "avvisi.xlsx", source: "excel_2022_2023", status: "preview", digest: "abc",
    parser_version: "v1", actor_id: 1, confirmed_by: null, reason: null, created_at: "2026-09-18", confirmed_at: null,
    summary: { rows: 2, ignored_non_operational: 1, outcomes: { new: 1, conflict: 1 } } };
  importedRows = [
    { id: "row-1", row_number: 3, source_key: "CUM", fingerprint: "fp", document_id: null, outcome: "new", anomalies: ["notifica_da_verificare"], resolution: null,
      payload: { document_number: "CUM", tax_code: "TESTCF", positions: [], original: { I: "29/06/204" }, dates: { I: "2024-06-29" } } },
    { id: "row-2", row_number: 4, source_key: "CUM-2", fingerprint: "fp2", document_id: "doc-2", outcome: "conflict", anomalies: [], resolution: null,
      payload: { document_number: "CUM-2", tax_code: null, positions: [], original: {} } },
  ];
  batches = [batch]; total = 11; failed = ""; writes = [];
  fetchMock = vi.fn(async (input: string, init: RequestInit) => {
    const url = new URL(input, "http://localhost");
    if (failed && url.pathname.endsWith(failed)) return jsonResponse({ detail: "Errore import di test" }, 422);
    if (init.method === "POST") {
      writes.push({ path: url.pathname, body: init.body instanceof FormData ? init.body : JSON.parse(String(init.body)) });
      if (url.pathname.endsWith("/conferma")) {
        batch = { ...batch, status: "confirmed", confirmed_by: 1, reason: "Verifica originale", confirmed_at: "2026-09-18" };
        importedRows[0] = { ...importedRows[0], document_id: "doc-1", outcome: "imported" };
      }
      return jsonResponse(batch);
    }
    const page = Number(url.searchParams.get("page") ?? 1);
    const pack = (items: unknown[], count: number) => ({ items: page === 1 ? items : [], page, page_size: 10, total: count });
    if (url.pathname.endsWith("/righe")) return jsonResponse(pack(importedRows, 11));
    if (url.pathname.endsWith("/originale")) return new Response("original workbook");
    if (url.pathname.endsWith(`/${batch.id}`)) return jsonResponse(batch);
    return jsonResponse(pack(batches, total));
  });
  vi.stubGlobal("fetch", fetchMock);
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });

async function open(canEdit = true) {
  const onSelect = vi.fn();
  render(<ImportWorkspace token="token" canEdit={canEdit} onSelect={onSelect} />);
  fireEvent.click(await screen.findByRole("button", { name: "avvisi.xlsx" }));
  await screen.findByRole("heading", { name: "avvisi.xlsx" });
  await screen.findByText("Riga 3 | CUM");
  return onSelect;
}

it("supports history, pagination, original comparison and manual navigation", async () => {
  const onSelect = await open();
  expect(screen.getByText(/Anteprima: registro non modificato/)).toBeVisible();
  expect(screen.getByText(/29\/06\/204/)).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Apri documento esistente da confrontare" }));
  expect(onSelect).toHaveBeenCalledWith("doc-2");
  fireEvent.click(screen.getByRole("button", { name: "Successiva" }));
  await waitFor(() => expect(screen.queryByText("Riga 3 | CUM")).toBeNull());
  fireEvent.click(screen.getByRole("button", { name: "Precedente" }));
  await screen.findByText("Riga 3 | CUM");
  fireEvent.click(screen.getByRole("button", { name: "Ricarica importazione" }));
  await screen.findByText("Riga 3 | CUM");
  fireEvent.click(screen.getByRole("button", { name: "Torna allo storico importazioni" }));
  await screen.findByRole("button", { name: "avvisi.xlsx" });
  fireEvent.click(screen.getByRole("button", { name: "Successiva" }));
  await waitFor(() => expect(screen.queryByRole("button", { name: "avvisi.xlsx" })).toBeNull());
  fireEvent.click(screen.getByRole("button", { name: "Precedente" }));
  await screen.findByRole("button", { name: "avvisi.xlsx" });
});

it("shows empty history and allows preparing an XLSX snapshot", async () => {
  batches = []; total = 0;
  render(<ImportWorkspace token="token" canEdit onSelect={vi.fn()} />);
  expect(await screen.findByText("Nessuna importazione presente.")).toBeVisible();
  const file = new File(["original"], "avvisi.xlsx");
  fireEvent.change(screen.getByLabelText("Excel avvisi 2022/2023"), { target: { files: [file] } });
  fireEvent.submit(screen.getByRole("form", { name: "Prepara anteprima Excel" }));
  await screen.findByRole("heading", { name: "avvisi.xlsx" });
  expect(writes[0].body).toBeInstanceOf(FormData);
  expect(writes[0].path).toMatch(/\/excel$/);
});

it("prepares existing Poste data without requesting an upload", async () => {
  render(<ImportWorkspace token="token" canEdit onSelect={vi.fn()} />);
  fireEvent.submit(screen.getByRole("form", { name: "Prepara snapshot Poste" }));
  await screen.findByRole("heading", { name: "avvisi.xlsx" });
  expect(writes).toEqual([{ path: "/api/ruolo/tributi/registro-avvisi/importazioni/poste", body: {} }]);
});

it("confirms with digest and reason, reloads outcomes and opens imported documents", async () => {
  const onSelect = await open();
  const form = screen.getByRole("form", { name: "Conferma importazione" });
  expect(within(form).getByRole("checkbox")).toBeRequired();
  fireEvent.click(within(form).getByRole("checkbox"));
  fireEvent.change(within(form).getByLabelText("Motivo importazione"), { target: { value: " Verifica originale " } });
  fireEvent.submit(form);
  await screen.findByText(/Importazione confermata/);
  expect(writes[0].body).toEqual({ digest: "abc", confirmed: true, reason: "Verifica originale" });
  fireEvent.click(await screen.findByRole("button", { name: "Apri documento nel registro" }));
  expect(onSelect).toHaveBeenCalledWith("doc-1");
  expect(screen.queryByRole("form", { name: "Conferma importazione" })).toBeNull();
});

it("viewer has neither upload nor confirmation commands", async () => {
  await open(false);
  expect(screen.queryByRole("form")).toBeNull();
  expect(writes).toEqual([]);
});

it("displays write errors without changing the preview and sends false for missing confirmation", async () => {
  await open();
  failed = "/conferma";
  const form = screen.getByRole("form", { name: "Conferma importazione" });
  fireEvent.submit(form);
  expect(await screen.findByRole("alert")).toHaveTextContent("Errore import di test");
  failed = "";
  fireEvent.submit(form);
  await screen.findByText(/Importazione confermata/);
  expect(writes[0].body).toEqual({ digest: "abc", confirmed: false, reason: "" });
});

it("prevents a second submit while a request is pending", async () => {
  let finish!: (response: Response) => void;
  const normal = fetchMock.getMockImplementation()!;
  fetchMock.mockImplementation((input: string, init: RequestInit) => init.method === "POST" ? new Promise<Response>((resolve) => { finish = resolve; }) : normal(input, init));
  render(<ImportWorkspace token="token" canEdit onSelect={vi.fn()} />);
  const form = screen.getByRole("form", { name: "Prepara snapshot Poste" });
  fireEvent.submit(form); fireEvent.submit(form);
  expect(within(form).getByRole("button", { name: "Elaborazione..." })).toBeDisabled();
  expect(fetchMock.mock.calls.filter(([, init]) => init.method === "POST")).toHaveLength(1);
  await act(async () => finish(jsonResponse(batch)));
  await screen.findByRole("heading", { name: "avvisi.xlsx" });
});

it("downloads preserved originals and reports download errors", async () => {
  await open();
  vi.stubGlobal("URL", class extends URL { static createObjectURL = vi.fn(() => "blob:test"); static revokeObjectURL = vi.fn(); });
  const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
  fireEvent.click(screen.getByRole("button", { name: "Scarica originale conservato" }));
  await waitFor(() => expect(click).toHaveBeenCalledOnce());
  expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:test");
  await downloadImport("token", { ...batch, source: "poste_db" });
  failed = "/originale";
  fireEvent.click(screen.getByRole("button", { name: "Scarica originale conservato" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Errore import di test");
});

it("reports read failures and can reload the batch", async () => {
  failed = "/batch-1";
  render(<ImportWorkspace token="token" canEdit onSelect={vi.fn()} />);
  fireEvent.click(await screen.findByRole("button", { name: "avvisi.xlsx" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Errore import di test");
  failed = "";
  fireEvent.click(screen.getByRole("button", { name: "Ricarica importazione" }));
  await screen.findByText("Riga 3 | CUM");
});
