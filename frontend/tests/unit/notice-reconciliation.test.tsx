import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { DocumentDetail } from "@/components/ruolo/notice-register/document-detail";
import { ImportDetail } from "@/components/ruolo/notice-register/import-detail";
import type { ImportBatch, ImportRow } from "@/components/ruolo/notice-register/import-client";
import { jsonResponse, noticeFixture, positionFixture } from "./notice-register-fixtures";

let source: ReturnType<typeof noticeFixture>;
let target: ReturnType<typeof noticeFixture>;
let row: ImportRow;
let batch: ImportBatch;
let writes: { path: string; body: { expected_version: number; reason: string; data: Record<string, unknown> } }[];
let status: number;
let fetchMock: ReturnType<typeof vi.fn>;
let candidateCount: number;

beforeEach(() => {
  source = noticeFixture({ id: "poste", document_number: "Poste originale", source_system: "poste_db" });
  target = noticeFixture({ id: "excel", document_number: "Excel cumulativo", source_system: "excel_2022_2023", version: 4, positions: [positionFixture()], position_count: 1 });
  batch = { id: "batch", filename: "variante.xlsx", source: "excel_2022_2023", status: "confirmed", digest: "digest", parser_version: "v1", actor_id: 1, confirmed_by: 1, reason: "Import", created_at: "2026-09-18", confirmed_at: "2026-09-18", summary: { rows: 1, ignored_non_operational: 0, outcomes: { conflict: 1 } } };
  row = { id: "row", row_number: 2, source_key: "CUM", fingerprint: "fp", document_id: "excel", outcome: "conflict", anomalies: [], resolution: null, payload: { document_number: "Variante", tax_code: "ALTROCF", original: { I: "29/06/204" }, positions: [] } };
  writes = []; status = 200; candidateCount = 11;
  fetchMock = vi.fn(async (input: string, init: RequestInit) => {
    const url = new URL(input, "http://localhost");
    const page = Number(url.searchParams.get("page") ?? 1);
    const pack = (items: unknown[], total = items.length) => ({ items: page === 1 ? items : [], total, page, page_size: 10 });
    if (init.method === "POST") {
      const body = JSON.parse(String(init.body));
      writes.push({ path: url.pathname, body });
      if (status !== 200) return jsonResponse({ detail: "Errore di prova" }, status);
      if (url.pathname.endsWith("/annulla")) source = { ...source, version: 3, reconciled_into_id: null };
      else if (url.pathname.endsWith("/riconciliazione")) source = { ...source, version: 2, reconciled_into_id: target.id };
      else row = { ...row, resolution: { decision: String(body.data.decision), reason: body.reason, actor_id: 7, document_version: 5, document_id: "excel", decided_at: "2026-09-18", evidence_id: null } };
      return jsonResponse({ document_id: "excel", resource_id: "row", version: 5 });
    }
    if (url.pathname.endsWith("/poste")) return jsonResponse(source);
    if (url.pathname.endsWith("/excel")) return jsonResponse(target);
    if (url.pathname.endsWith("/righe")) {
      const filter = url.searchParams.get("review");
      return jsonResponse(pack(filter === "open" && row.resolution ? [] : [row]));
    }
    if (url.pathname.endsWith("/batch")) return jsonResponse(batch);
    if (url.searchParams.has("reconciliation_candidates")) return jsonResponse(pack(candidateCount ? [target] : [], candidateCount));
    return jsonResponse(pack([]));
  });
  vi.stubGlobal("fetch", fetchMock);
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });

async function search() {
  const form = await screen.findByRole("form", { name: "Cerca documento da riconciliare" });
  fireEvent.change(within(form).getByRole("searchbox"), { target: { value: "TESTCF" } });
  fireEvent.submit(form);
}

async function select() {
  await search();
  fireEvent.click(await screen.findByRole("button", { name: "Confronta Excel cumulativo" }));
  return screen.findByRole("form", { name: "Conferma riconciliazione Poste" });
}

function confirm(form: HTMLElement) {
  expect(within(form).getByRole("checkbox")).toBeRequired();
  fireEvent.click(within(form).getByRole("checkbox"));
  fireEvent.change(within(form).getByLabelText("Motivo della registrazione o correzione"), { target: { value: " Confronto documentale " } });
  fireEvent.submit(form);
}

it("reconciles with two versions and offers navigation to the canonical document", async () => {
  const onSelect = vi.fn();
  render(<DocumentDetail token="t" documentId="poste" canEdit onSelect={onSelect} />);
  const form = await select();
  expect(screen.getByLabelText("Documento di confronto")).toHaveTextContent("020220001834880");
  confirm(form);
  fireEvent.click(await screen.findByRole("button", { name: "Apri documento riconciliato" }));
  expect(onSelect).toHaveBeenCalledWith("excel");
  expect(screen.queryByLabelText("Operazioni documento")).toBeNull();
  expect(screen.queryByLabelText("Riconciliazione Poste")).toBeNull();
  expect(writes[0]).toEqual({ path: "/api/ruolo/tributi/registro-avvisi/poste/riconciliazione", body: { expected_version: 1, reason: "Confronto documentale", data: { target_document_id: "excel", target_version: 4, confirmed: true } } });
});

it("clears selected candidates on pagination and handles empty searches", async () => {
  target.tax_code = null; target.issued_on = null;
  render(<DocumentDetail token="t" documentId="poste" canEdit onSelect={vi.fn()} />);
  await select();
  expect(screen.getByLabelText("Documento di confronto")).toHaveTextContent("CF: Assente | Emesso: Data assente");
  const panel = screen.getByLabelText("Riconciliazione Poste");
  fireEvent.click(within(panel).getByRole("button", { name: "Successiva" }));
  await within(panel).findByText(/Nessun documento compatibile/);
  expect(screen.queryByRole("form", { name: "Conferma riconciliazione Poste" })).toBeNull();
  fireEvent.click(within(panel).getByRole("button", { name: "Precedente" }));
  await within(panel).findByRole("button", { name: "Confronta Excel cumulativo" });
  candidateCount = 0;
  const form = screen.getByRole("form", { name: "Cerca documento da riconciliare" });
  fireEvent.change(within(form).getByRole("searchbox"), { target: { value: "OTHER" } });
  fireEvent.submit(form);
  await within(panel).findByText(/Nessun documento compatibile/);
});

it("reports stale versions and does not hide the source on failure", async () => {
  status = 409;
  render(<DocumentDetail token="t" documentId="poste" canEdit onSelect={vi.fn()} />);
  const form = await select();
  fireEvent.submit(form);
  expect(await screen.findByRole("alert")).toHaveTextContent("Conflitto:");
  expect(writes[0].body.data.confirmed).toBe(false);
  expect(screen.queryByRole("button", { name: "Apri documento riconciliato" })).toBeNull();
});

it("undoes reconciliation with both versions and returns to the editable source", async () => {
  source.reconciled_into_id = target.id;
  source.version = 2;
  render(<DocumentDetail token="t" documentId="poste" canEdit onSelect={vi.fn()} />);
  const form = await screen.findByRole("form", { name: "Annulla riconciliazione" });
  confirm(form);
  await screen.findByRole("form", { name: "Cerca documento da riconciliare" });
  expect(writes[0]).toEqual({ path: "/api/ruolo/tributi/registro-avvisi/poste/riconciliazione/annulla", body: { expected_version: 2, reason: "Confronto documentale", data: { target_document_id: "excel", target_version: 4, confirmed: true } } });
  expect(screen.queryByRole("form", { name: "Annulla riconciliazione" })).toBeNull();
});

it("shows undo conflicts without losing the canonical link", async () => {
  source.reconciled_into_id = target.id;
  status = 409;
  render(<DocumentDetail token="t" documentId="poste" canEdit onSelect={vi.fn()} />);
  fireEvent.submit(await screen.findByRole("form", { name: "Annulla riconciliazione" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Conflitto:");
  expect(writes[0].body.data.confirmed).toBe(false);
  expect(screen.getByRole("button", { name: "Apri documento riconciliato" })).toBeVisible();
});

it.each([false, true])("does not offer reconciliation to viewers or Poste with positions: %s", async (canEdit) => {
  if (canEdit) source.positions = [positionFixture()];
  render(<DocumentDetail token="t" documentId="poste" canEdit={canEdit} onSelect={vi.fn()} />);
  await screen.findByRole("heading", { name: "Poste originale" });
  expect(screen.queryByLabelText("Riconciliazione Poste")).toBeNull();
});

it.each(["keep_existing", "register_evidence"])("resolves conflicts explicitly with decision %s and filters the resolved row", async (decision) => {
  render(<ImportDetail token="t" batchId="batch" canEdit onSelect={vi.fn()} />);
  fireEvent.click(await screen.findByRole("button", { name: "Confronta variante e risolvi" }));
  const form = await screen.findByRole("form", { name: "Risolvi conflitto importazione" });
  fireEvent.change(within(form).getByLabelText("Decisione sul conflitto"), { target: { value: decision } });
  confirm(form);
  expect(await screen.findByText(/Conflitto risolto:/)).toBeVisible();
  expect(screen.getByText(/Operatore #7/)).toHaveTextContent("Versione 5");
  expect(writes[0].body).toEqual({ expected_version: 4, reason: "Confronto documentale", data: { decision, fingerprint: "fp", document_id: "excel", confirmed: true } });
  fireEvent.change(screen.getByLabelText("Stato conflitti"), { target: { value: "open" } });
  await screen.findByText("Nessuna riga per questo filtro.");
  fireEvent.change(screen.getByLabelText("Stato conflitti"), { target: { value: "resolved" } });
  await screen.findByText(/Conflitto risolto:/);
  expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("review=resolved"), expect.anything());
});

it("follows a reconciled source for comparison and guards viewer decisions", async () => {
  source.reconciled_into_id = "excel";
  row.document_id = "poste";
  render(<ImportDetail token="t" batchId="batch" canEdit={false} onSelect={vi.fn()} />);
  fireEvent.click(await screen.findByRole("button", { name: "Confronta variante e risolvi" }));
  await screen.findByRole("heading", { name: "Excel cumulativo" });
  expect(screen.queryByRole("form")).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "Chiudi confronto" }));
  expect(screen.queryByLabelText("Documento di confronto")).toBeNull();
});

it("retains an open conflict after a failed decision and sends actual checkbox state", async () => {
  status = 409;
  render(<ImportDetail token="t" batchId="batch" canEdit onSelect={vi.fn()} />);
  fireEvent.click(await screen.findByRole("button", { name: "Confronta variante e risolvi" }));
  fireEvent.submit(await screen.findByRole("form", { name: "Risolvi conflitto importazione" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Conflitto:");
  expect(writes[0].body.data.confirmed).toBe(false);
  expect(screen.queryByText(/Conflitto risolto:/)).toBeNull();
  status = 200;
  confirm(screen.getByRole("form", { name: "Risolvi conflitto importazione" }));
  await waitFor(() => expect(screen.queryByRole("alert")).toBeNull());
  await screen.findByText(/Conflitto risolto:/);
});
