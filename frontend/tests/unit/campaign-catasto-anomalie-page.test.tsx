import type { ReactNode } from "react";
import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import CatastoAnomaliePage from "@/app/catasto/anomalie/page";
import type { CatAnomalia } from "@/types/catasto";

const mocks = vi.hoisted(() => ({
  params: new URLSearchParams("tab=manuale"),
  router: { replace: vi.fn() },
  token: vi.fn(),
  list: vi.fn(),
  summary: vi.fn(),
  cfItems: vi.fn(),
  comuneItems: vi.fn(),
  particellaItems: vi.fn(),
  adeSummary: vi.fn(),
  adeCandidates: vi.fn(),
  batches: vi.fn(),
  users: vi.fn(),
  categories: vi.fn(),
  severities: vi.fn(),
  update: vi.fn(),
  createReport: vi.fn(),
  page: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => mocks.router,
  useSearchParams: () => mocks.params,
}));
vi.mock("@/lib/auth", () => ({ getStoredAccessToken: mocks.token }));
vi.mock("@/lib/api/catasto", () => ({
  catastoListAnomalie: mocks.list,
  catastoGetAnomalieSummary: mocks.summary,
  catastoGetCfWizardItems: mocks.cfItems,
  catastoGetComuneWizardItems: mocks.comuneItems,
  catastoGetParticellaWizardItems: mocks.particellaItems,
  catastoGetAdeStatusScanSummary: mocks.adeSummary,
  catastoGetAdeStatusScanCandidates: mocks.adeCandidates,
  catastoUpdateAnomalia: mocks.update,
}));
vi.mock("@/lib/api", () => ({
  getElaborazioneBatches: mocks.batches,
  listApplicationUsers: mocks.users,
}));
vi.mock("@/features/operazioni/api/client", () => ({
  getReportCategories: mocks.categories,
  getReportSeverities: mocks.severities,
  createReport: mocks.createReport,
}));
vi.mock("@/components/catasto/catasto-page", () => ({
  CatastoPage: (props: { children: ReactNode; requiredRoles: string[]; requiredModule: string }) => {
    mocks.page(props);
    return <>{props.children}</>;
  },
}));
vi.mock("@/components/elaborazioni/workspace-modal", () => ({
  ElaborazioneWorkspaceModal: () => null,
}));
vi.mock("@/components/catasto/workspace-modal", () => ({
  CatastoWorkspaceModal: ({ open, href, onClose }: { open: boolean; href: string | null; onClose: () => void }) => (
    open ? <div role="dialog" aria-label="Scheda particella" data-href={href}>
      <button type="button" onClick={onClose}>Chiudi scheda</button>
    </div> : null
  ),
}));

function anomaly(id = "a1", overrides: Partial<CatAnomalia> = {}): CatAnomalia {
  return {
    id,
    tipo: "VAL-99-custom",
    severita: "error",
    status: "aperta",
    descrizione: `Anomalia ${id}`,
    particella_id: "parcel-1",
    utenza_id: "utenza-1",
    anno_campagna: 2026,
    assigned_to: null,
    note_operatore: null,
    segnalazione_id: null,
    dati_json: { source: id },
    created_at: "2026-10-08T12:00:00Z",
    updated_at: "2026-10-08T12:00:00Z",
    ...overrides,
  };
}

function setItems(items: CatAnomalia[], total = items.length) {
  mocks.list.mockResolvedValue({ items, total, page: 1, page_size: 50 });
}

function deferred<Value>() {
  let resolve!: (value: Value) => void;
  const promise = new Promise<Value>((fulfill) => { resolve = fulfill; });
  return { promise, resolve };
}

async function mountManual() {
  const view = render(<CatastoAnomaliePage />);
  await screen.findByRole("button", { name: "Salva nota" });
  await waitFor(() => expect(screen.getByRole("button", { name: "Reset contesto" })).toBeEnabled());
  return view;
}

function table() {
  return screen.getByRole("table");
}

function row(id: string) {
  return within(table()).getByText(`Anomalia ${id}`).closest("tr")!;
}

beforeEach(() => {
  vi.resetAllMocks();
  mocks.params = new URLSearchParams("tab=manuale");
  mocks.token.mockReturnValue("token");
  setItems([anomaly()]);
  mocks.summary.mockResolvedValue({ buckets: [], total: 1 });
  mocks.cfItems.mockResolvedValue({ items: [], total: 0 });
  mocks.comuneItems.mockResolvedValue({ items: [], total: 0 });
  mocks.particellaItems.mockResolvedValue({ items: [], total: 0 });
  mocks.adeSummary.mockResolvedValue({});
  mocks.adeCandidates.mockResolvedValue({ items: [], total: 0 });
  mocks.batches.mockResolvedValue([]);
  mocks.users.mockResolvedValue({ items: [] });
  mocks.categories.mockResolvedValue([{ id: "cat-1", name: "Catasto" }]);
  mocks.severities.mockResolvedValue([{ id: "sev-1", name: "Alta" }]);
  mocks.update.mockResolvedValue({});
  mocks.createReport.mockResolvedValue({ report: { id: "report-1", report_number: "R-0001" } });
});

afterEach(cleanup);

describe("Catasto anomalie manual queue characterization", () => {
  test("loads manual register, summary and lookups while inactive wizards remain idle", async () => {
    await mountManual();
    expect(mocks.list).toHaveBeenCalledExactlyOnceWith("token", {
      tipo: undefined,
      severita: undefined,
      status: "aperta",
      anno: undefined,
      distretto: undefined,
      q: undefined,
      sortBy: "created_at",
      sortDir: "desc",
      page: 1,
      pageSize: 50,
    });
    expect(mocks.summary).toHaveBeenCalledExactlyOnceWith("token", {
      status: "aperta", severita: undefined, anno: undefined, distretto: undefined,
    });
    expect(mocks.cfItems).not.toHaveBeenCalled();
    expect(mocks.comuneItems).not.toHaveBeenCalled();
    expect(mocks.particellaItems).not.toHaveBeenCalled();
    expect(mocks.adeCandidates).toHaveBeenCalledWith("token", { limit: 8 });
    expect(mocks.users).toHaveBeenCalledWith("token");
    expect(mocks.page).toHaveBeenCalledWith(expect.objectContaining({
      requiredModule: "catasto", requiredRoles: ["admin", "super_admin"],
    }));
    expect(screen.getByLabelText("Nota operatore")).toHaveValue("");
    expect(screen.getByLabelText("Titolo")).toHaveValue("VAL-99-custom · Anomalia a1");
  });

  test("initializes query context and preserves canonical URL parameters", async () => {
    mocks.params = new URLSearchParams("tab=manuale&tipo=VAL-06-imponibile&severita=warning&status=chiusa&anno=2025&distretto=3&page=2&q=%20source%20&sort_by=updated_at&sort_dir=asc&manual=without_wizard");
    setItems([anomaly()], 51);
    await mountManual();
    expect(mocks.list).toHaveBeenCalledWith("token", expect.objectContaining({
      tipo: "VAL-06-imponibile", severita: "warning", status: "chiusa", anno: 2025,
      distretto: "3", page: 2, q: "source", sortBy: "updated_at", sortDir: "asc",
    }));
    const url = new URL(mocks.router.replace.mock.calls.at(-1)![0], "http://localhost");
    expect(url.searchParams.get("q")).toBe("source");
    expect(url.searchParams.get("manual")).toBe("without_wizard");
    expect(url.searchParams.get("page")).toBe("2");
  });

  test.each(["0", "-2", "bad", "Infinity"])("normalizes invalid initial page %s", async (page) => {
    mocks.params = new URLSearchParams(`tab=manuale&page=${page}`);
    await mountManual();
    expect(mocks.list).toHaveBeenCalledWith("token", expect.objectContaining({ page: 1 }));
  });

  test("returns to page one when the requested backend page has become empty", async () => {
    mocks.params = new URLSearchParams("tab=manuale&page=3");
    mocks.list.mockResolvedValueOnce({ items: [], total: 1, page: 3, page_size: 50 });
    await mountManual();
    expect(mocks.list).toHaveBeenNthCalledWith(1, "token", expect.objectContaining({ page: 3 }));
    expect(mocks.list).toHaveBeenNthCalledWith(2, "token", expect.objectContaining({ page: 1 }));
    expect(within(table()).getByText("Anomalia a1")).toBeInTheDocument();
  });

  test("context filters and backend search reset pagination without local sorting", async () => {
    setItems([anomaly()], 101);
    await mountManual();
    fireEvent.click(screen.getByRole("button", { name: "Successiva" }));
    await waitFor(() => expect(mocks.list).toHaveBeenLastCalledWith("token", expect.objectContaining({ page: 2 })));
    fireEvent.change(screen.getByLabelText("Anno"), { target: { value: "2025" } });
    await waitFor(() => expect(mocks.list).toHaveBeenLastCalledWith("token", expect.objectContaining({ anno: 2025, page: 1 })));
    fireEvent.change(screen.getByLabelText("Distretto"), { target: { value: "7" } });
    fireEvent.change(screen.getByLabelText("Tipo"), { target: { value: "VAL-07-importi" } });
    fireEvent.change(screen.getByLabelText("Severità"), { target: { value: "warning" } });
    fireEvent.change(screen.getByLabelText("Stato"), { target: { value: "chiusa" } });
    fireEvent.change(screen.getByLabelText("Ricerca backend"), { target: { value: "  draft  " } });
    fireEvent.change(screen.getByLabelText("Ordina per"), { target: { value: "anno_campagna" } });
    fireEvent.change(screen.getByLabelText("Direzione"), { target: { value: "asc" } });
    await waitFor(() => expect(mocks.list).toHaveBeenLastCalledWith("token", expect.objectContaining({
      page: 1, anno: 2025, distretto: "7", tipo: "VAL-07-importi", severita: "warning",
      status: "chiusa", q: "draft", sortBy: "anno_campagna", sortDir: "asc",
    })));
    fireEvent.click(screen.getByRole("button", { name: "Reset contesto" }));
    await waitFor(() => expect(mocks.list).toHaveBeenLastCalledWith("token", expect.objectContaining({
      anno: undefined, distretto: undefined, tipo: undefined, severita: undefined, status: "aperta", q: "draft",
    })));
    fireEvent.click(screen.getByRole("button", { name: "Reset registro" }));
    await waitFor(() => expect(mocks.list).toHaveBeenLastCalledWith("token", expect.objectContaining({
      q: undefined, sortBy: "created_at", sortDir: "desc", status: "aperta",
    })));
  });

  test("without-wizard filter is local and recovers selection when a selected row disappears", async () => {
    setItems([anomaly("wizard", { tipo: "VAL-02-cf_invalido", note_operatore: "wizard note" }), anomaly("manual", { note_operatore: "manual note" })]);
    await mountManual();
    fireEvent.click(row("wizard"));
    expect(screen.getByLabelText("Nota operatore")).toHaveValue("wizard note");
    fireEvent.change(screen.getByLabelText("Vista manuale"), { target: { value: "without_wizard" } });
    expect(within(table()).queryByText("Anomalia wizard")).not.toBeInTheDocument();
    expect(within(table()).getByText("Anomalia manual")).toBeInTheDocument();
    expect(screen.getByLabelText("Nota operatore")).toHaveValue("manual note");
    expect(mocks.list).toHaveBeenCalledTimes(1);
  });

  test("unworked view excludes notes, assignment and non-open status but accepts whitespace notes", async () => {
    setItems([
      anomaly("clean", { note_operatore: "  " }),
      anomaly("noted", { note_operatore: "checked" }),
      anomaly("assigned", { assigned_to: 0 }),
      anomaly("closed", { status: "chiusa" }),
    ]);
    await mountManual();
    fireEvent.change(screen.getByLabelText("Vista manuale"), { target: { value: "unworked" } });
    expect(within(table()).getByText("Anomalia clean")).toBeInTheDocument();
    for (const id of ["noted", "assigned", "closed"]) {
      expect(within(table()).queryByText(`Anomalia ${id}`)).not.toBeInTheDocument();
    }
    expect(mocks.list).toHaveBeenCalledTimes(1);
  });

  test("row selection replaces note and report drafts without retaining another row's choices", async () => {
    setItems([anomaly("first", { note_operatore: "first note" }), anomaly("second", { note_operatore: "second note", particella_id: "parcel-2" })]);
    await mountManual();
    fireEvent.change(screen.getByLabelText("Nota operatore"), { target: { value: "unsaved note" } });
    fireEvent.change(screen.getByLabelText("Categoria"), { target: { value: "cat-1" } });
    fireEvent.click(row("second"));
    expect(screen.getByLabelText("Nota operatore")).toHaveValue("second note");
    expect(screen.getByLabelText("Categoria")).toHaveValue("");
    expect(screen.getByLabelText("Titolo")).toHaveValue("VAL-99-custom · Anomalia second");
    expect(screen.getByRole("link", { name: "Apri pagina particella" })).toHaveAttribute("href", "/catasto/particelle/parcel-2");
    fireEvent.click(screen.getByRole("button", { name: "Apri in modale" }));
    expect(screen.getByRole("dialog", { name: "Scheda particella" })).toHaveAttribute("data-href", "/catasto/particelle/parcel-2");
    fireEvent.click(screen.getByRole("button", { name: "Chiudi scheda" }));
    expect(screen.queryByRole("dialog", { name: "Scheda particella" })).not.toBeInTheDocument();
  });

  test.each([
    [" checked ", "checked"],
    ["   ", null],
  ])("saves trimmed note %j and refreshes the register", async (draft, expected) => {
    await mountManual();
    fireEvent.change(screen.getByLabelText("Nota operatore"), { target: { value: draft } });
    fireEvent.click(screen.getByRole("button", { name: "Salva nota" }));
    await waitFor(() => expect(mocks.update).toHaveBeenCalledExactlyOnceWith("token", "a1", { note_operatore: expected }));
    expect(await screen.findByText("Nota operatore salvata.")).toBeInTheDocument();
    expect(mocks.list).toHaveBeenCalledTimes(2);
  });

  test("keeps note commands busy until save and refresh complete in order", async () => {
    const save = deferred<object>();
    const refresh = deferred<{ items: CatAnomalia[]; total: number }>();
    await mountManual();
    mocks.update.mockReturnValueOnce(save.promise);
    mocks.list.mockReturnValueOnce(refresh.promise);
    fireEvent.click(screen.getByRole("button", { name: "Salva nota" }));
    expect(screen.getAllByRole("button", { name: "Salvataggio..." }).every(button => button.hasAttribute("disabled"))).toBe(true);
    expect(mocks.list).toHaveBeenCalledTimes(1);
    await act(async () => save.resolve({}));
    expect(mocks.list).toHaveBeenCalledTimes(2);
    expect(screen.getAllByRole("button", { name: "Salvataggio..." }).every(button => button.hasAttribute("disabled"))).toBe(true);
    await act(async () => refresh.resolve({ items: [anomaly()], total: 1 }));
    expect(screen.getByRole("button", { name: "Salva nota" })).toBeEnabled();
  });

  test.each([
    [new Error("Permission denied"), "Permission denied"],
    ["unknown failure", "Errore salvataggio nota"],
  ])("note error %s preserves draft and allows retry", async (failure, message) => {
    mocks.update.mockRejectedValueOnce(failure);
    await mountManual();
    fireEvent.change(screen.getByLabelText("Nota operatore"), { target: { value: "keep draft" } });
    fireEvent.click(screen.getByRole("button", { name: "Salva nota" }));
    expect(await screen.findByText(message)).toBeInTheDocument();
    expect(screen.getByLabelText("Nota operatore")).toHaveValue("keep draft");
    expect(screen.getByRole("button", { name: "Salva nota" })).toBeEnabled();
    expect(mocks.list).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByRole("button", { name: "Salva nota" }));
    expect(await screen.findByText("Nota operatore salvata.")).toBeInTheDocument();
  });

  test("assignment options require active Catasto users and numeric API identity", async () => {
    mocks.users.mockResolvedValue({ items: [
      { id: 7, username: "allowed", role: "admin", is_active: true, module_catasto: true },
      { id: 8, username: "inactive", role: "admin", is_active: false, module_catasto: true },
      { id: 9, username: "outside", role: "admin", is_active: true, module_catasto: false },
    ] });
    await mountManual();
    const select = screen.getByLabelText("Assegna a");
    expect(within(select).getByRole("option", { name: "allowed · admin" })).toBeInTheDocument();
    expect(within(select).queryByText(/inactive|outside/)).not.toBeInTheDocument();
    fireEvent.change(select, { target: { value: "7" } });
    fireEvent.click(screen.getByRole("button", { name: "Salva assegnazione" }));
    await waitFor(() => expect(mocks.update).toHaveBeenCalledWith("token", "a1", { assigned_to: 7 }));
    expect(await screen.findByText("Assegnazione aggiornata.")).toBeInTheDocument();
  });

  test("validates report fields before creating any external resource", async () => {
    await mountManual();
    fireEvent.click(screen.getByRole("button", { name: "Crea segnalazione" }));
    expect(screen.getByText("Compila categoria, gravità e titolo della segnalazione.")).toBeInTheDocument();
    expect(mocks.createReport).not.toHaveBeenCalled();
    expect(mocks.update).not.toHaveBeenCalled();
  });

  test("creates the report before linking and refreshing the anomaly", async () => {
    const creation = deferred<{ report: { id: string; report_number: string } }>();
    mocks.createReport.mockReturnValueOnce(creation.promise);
    await mountManual();
    fireEvent.change(screen.getByLabelText("Categoria"), { target: { value: "cat-1" } });
    fireEvent.change(screen.getByLabelText("Gravità"), { target: { value: "sev-1" } });
    fireEvent.change(screen.getByLabelText("Titolo"), { target: { value: " report title " } });
    fireEvent.change(screen.getByLabelText("Descrizione"), { target: { value: "  " } });
    fireEvent.click(screen.getByRole("button", { name: "Crea segnalazione" }));
    expect(mocks.createReport).toHaveBeenCalledWith({
      category_id: "cat-1", severity_id: "sev-1", title: "report title", description: null,
    });
    expect(screen.getByRole("button", { name: "Creazione..." })).toBeDisabled();
    expect(mocks.update).not.toHaveBeenCalled();
    await act(async () => creation.resolve({ report: { id: "report-1", report_number: "R-0001" } }));
    expect(mocks.update).toHaveBeenCalledWith("token", "a1", { segnalazione_id: "report-1" });
    expect(screen.getByText("Segnalazione operativa creata: R-0001.")).toBeInTheDocument();
    expect(mocks.list).toHaveBeenCalledTimes(2);
  });

  test("a report without ID never links an invalid resource", async () => {
    mocks.createReport.mockResolvedValueOnce({ report: {} });
    await mountManual();
    fireEvent.change(screen.getByLabelText("Categoria"), { target: { value: "cat-1" } });
    fireEvent.change(screen.getByLabelText("Gravità"), { target: { value: "sev-1" } });
    fireEvent.click(screen.getByRole("button", { name: "Crea segnalazione" }));
    expect(await screen.findByText("Segnalazione creata senza ID report")).toBeInTheDocument();
    expect(mocks.update).not.toHaveBeenCalled();
    expect(mocks.list).toHaveBeenCalledTimes(1);
    expect(screen.getByRole("button", { name: "Crea segnalazione" })).toBeEnabled();
  });

  test("link failure after report creation is surfaced without claiming an atomic rollback", async () => {
    mocks.update.mockRejectedValueOnce(new Error("Link failed"));
    await mountManual();
    fireEvent.change(screen.getByLabelText("Categoria"), { target: { value: "cat-1" } });
    fireEvent.change(screen.getByLabelText("Gravità"), { target: { value: "sev-1" } });
    fireEvent.click(screen.getByRole("button", { name: "Crea segnalazione" }));
    expect(await screen.findByText("Link failed")).toBeInTheDocument();
    expect(mocks.createReport).toHaveBeenCalledTimes(1);
    expect(mocks.update).toHaveBeenCalledWith("token", "a1", { segnalazione_id: "report-1" });
    expect(mocks.list).toHaveBeenCalledTimes(1);
  });

  test.each([
    ["Chiudi", "chiusa"], ["Ignora", "ignora"], ["Riapri", "aperta"],
  ])("row command %s changes only its row without changing detail selection", async (label, status) => {
    setItems([anomaly("first", { note_operatore: "first" }), anomaly("second", { note_operatore: "second" })]);
    await mountManual();
    fireEvent.click(row("second"));
    fireEvent.click(within(row("first")).getByRole("button", { name: label }));
    await waitFor(() => expect(mocks.update).toHaveBeenCalledWith("token", "first", { status }));
    expect(screen.getByLabelText("Nota operatore")).toHaveValue("second");
    expect(mocks.list).toHaveBeenCalledTimes(2);
  });

  test("expired token prevents note/assignment/status/report mutations", async () => {
    await mountManual();
    fireEvent.change(screen.getByLabelText("Categoria"), { target: { value: "cat-1" } });
    fireEvent.change(screen.getByLabelText("Gravità"), { target: { value: "sev-1" } });
    mocks.token.mockReturnValue(null);
    for (const label of ["Salva nota", "Salva assegnazione", "Chiudi da pannello", "Crea segnalazione"]) {
      fireEvent.click(screen.getByRole("button", { name: label }));
    }
    expect(mocks.update).not.toHaveBeenCalled();
    expect(mocks.createReport).not.toHaveBeenCalled();
  });

  test.each([
    [new Error("List unavailable"), "List unavailable"],
    ["unknown failure", "Errore caricamento anomalie"],
  ])("overview failure %s renders the error and releases loading state", async (failure, message) => {
    mocks.list.mockRejectedValueOnce(failure);
    render(<CatastoAnomaliePage />);
    expect(await screen.findByText(message)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Reset contesto" })).toBeEnabled();
    expect(screen.getByText("Nessuna anomalia")).toBeInTheDocument();
  });
});
