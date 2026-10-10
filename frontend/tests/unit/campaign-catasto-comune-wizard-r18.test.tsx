import type { ReactNode } from "react";
import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import CatastoAnomaliePage from "@/app/catasto/anomalie/page";
import type {
  CatAnomaliaComuneCandidate,
  CatAnomaliaComuneWizardApplyResponse,
  CatAnomaliaComuneWizardItem,
  CatAnomaliaComuneWizardListResponse,
} from "@/types/catasto";

const mocks = vi.hoisted(() => ({
  params: new URLSearchParams("tab=comune"),
  router: { replace: vi.fn() },
  token: vi.fn(),
  list: vi.fn(),
  summary: vi.fn(),
  comuneItems: vi.fn(),
  applyComune: vi.fn(),
  cfItems: vi.fn(),
  particellaItems: vi.fn(),
  adeSummary: vi.fn(),
  adeCandidates: vi.fn(),
  batches: vi.fn(),
  users: vi.fn(),
  categories: vi.fn(),
  severities: vi.fn(),
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
  catastoGetComuneWizardItems: mocks.comuneItems,
  catastoApplyComuneWizard: mocks.applyComune,
  catastoGetCfWizardItems: mocks.cfItems,
  catastoGetParticellaWizardItems: mocks.particellaItems,
  catastoGetAdeStatusScanSummary: mocks.adeSummary,
  catastoGetAdeStatusScanCandidates: mocks.adeCandidates,
}));
vi.mock("@/lib/api", () => ({
  getElaborazioneBatches: mocks.batches,
  listApplicationUsers: mocks.users,
}));
vi.mock("@/features/operazioni/api/client", () => ({
  getReportCategories: mocks.categories,
  getReportSeverities: mocks.severities,
}));
vi.mock("@/components/catasto/catasto-page", () => ({
  CatastoPage: (props: { children: ReactNode; requiredRoles: string[]; requiredModule: string }) => {
    mocks.page(props);
    return <>{props.children}</>;
  },
}));
vi.mock("@/components/elaborazioni/workspace-modal", () => ({ ElaborazioneWorkspaceModal: () => null }));
vi.mock("@/components/catasto/workspace-modal", () => ({ CatastoWorkspaceModal: () => null }));

function candidate(id = "town-first", overrides: Partial<CatAnomaliaComuneCandidate> = {}): CatAnomaliaComuneCandidate {
  return {
    id,
    nome_comune: `Comune ${id}`,
    nome_comune_legacy: `Legacy ${id}`,
    codice_catastale: "H501",
    cod_comune_capacitas: 101,
    codice_comune_formato_numerico: 101,
    codice_comune_numerico_2017_2025: 101,
    sigla_provincia: "RM",
    match_score: 0.2,
    ...overrides,
  };
}

function comuneItem(id = "com-1", overrides: Partial<CatAnomaliaComuneWizardItem> = {}): CatAnomaliaComuneWizardItem {
  return {
    anomalia_id: id,
    utenza_id: "utenza-1",
    anno_campagna: 2026,
    tipo: "VAL-04-comune_invalido",
    severita: "error",
    descrizione: "Comune da riallineare",
    status: "aperta",
    denominazione: `Utenza ${id}`,
    nome_comune: "Comune originale",
    cod_comune_capacitas: 90,
    source_cod_comune_capacitas: 91,
    num_distretto: 7,
    sezione_catastale: "B",
    foglio: "23",
    particella: "45",
    subalterno: "3",
    candidates: [candidate(), candidate("town-second", { cod_comune_capacitas: 202, match_score: 0.9 })],
    created_at: "2026-10-09T11:00:00Z",
    ...overrides,
  };
}

function response(items: CatAnomaliaComuneWizardItem[], total = items.length, page = 1): CatAnomaliaComuneWizardListResponse {
  return { items, total, page, page_size: 25 };
}

function deferred<Value>() {
  let resolve!: (value: Value) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<Value>((fulfill, fail) => { resolve = fulfill; reject = fail; });
  return { promise, resolve, reject };
}

function wizard() {
  return screen.getByText("Wizard comune invalido").closest("article")!;
}

function row(id = "com-1") {
  return screen.getByText(`Utenza ${id}`).closest<HTMLDivElement>("div.rounded-2xl")!;
}

function radio(id = "com-1", town = "town-first") {
  return within(row(id)).getByRole("radio", { name: new RegExp(`Comune ${town} `) });
}

function singleButton(id = "com-1") {
  return within(row(id)).getByRole("button", { name: /Applica solo questa riga|Applicazione\.\.\./ });
}

function batchButton() {
  return within(wizard()).getByRole("button", { name: /Applica batch|Applicazione batch/ });
}

function note() {
  return screen.getByLabelText("Nota batch applicata alle correzioni");
}

function clearSelection() {
  fireEvent.click(within(wizard()).getByRole("button", { name: "Pulisci selezioni" }));
}

function selectTop() {
  fireEvent.click(within(wizard()).getByRole("button", { name: "Seleziona top candidate" }));
}

function selectManualTab() {
  fireEvent.click(within(screen.getByRole("navigation", { name: "Code anomalie" })).getByRole("button", { name: /Triage manuale/ }));
}

function selectComuneTab() {
  fireEvent.click(within(screen.getByRole("navigation", { name: "Code anomalie" })).getByRole("button", { name: /Comuni/ }));
}

async function mountComune() {
  const view = render(<CatastoAnomaliePage />);
  await screen.findByText("Utenza com-1");
  await waitFor(() => expect(within(wizard()).queryByText("Sincronizzazione...")).not.toBeInTheDocument());
  await waitFor(() => expect(screen.getByRole("button", { name: "Reset contesto" })).toBeEnabled());
  return view;
}

beforeEach(() => {
  vi.resetAllMocks();
  mocks.params = new URLSearchParams("tab=comune");
  mocks.token.mockReturnValue("token");
  mocks.list.mockResolvedValue({ items: [], total: 0, page: 1, page_size: 50 });
  mocks.summary.mockResolvedValue({ buckets: [], total: 0 });
  mocks.comuneItems.mockResolvedValue(response([comuneItem()]));
  mocks.applyComune.mockResolvedValue({ applied_count: 1, updated_utenze: 2, closed_anomalies: 3 });
  mocks.cfItems.mockResolvedValue({ items: [], total: 0 });
  mocks.particellaItems.mockResolvedValue({ items: [], total: 0 });
  mocks.adeSummary.mockResolvedValue({});
  mocks.adeCandidates.mockResolvedValue({ items: [], total: 0 });
  mocks.batches.mockResolvedValue([]);
  mocks.users.mockResolvedValue({ items: [] });
  mocks.categories.mockResolvedValue([]);
  mocks.severities.mockResolvedValue([]);
});

afterEach(cleanup);

describe("R18 original Catasto Comune candidate and batch public transitions", () => {
  test("loads open Comune items with a literal request and selects the first response candidate rather than the highest score", async () => {
    await mountComune();
    expect(mocks.comuneItems).toHaveBeenCalledExactlyOnceWith("token", {
      status: "aperta", anno: undefined, distretto: undefined, page: 1, pageSize: 25,
    });
    expect(radio()).toBeChecked();
    expect(radio("com-1", "town-second")).not.toBeChecked();
    const after = within(row()).getByText("Dopo").parentElement!;
    expect(within(after).getByText("Comune town-first")).toBeInTheDocument();
    expect(within(after).getByText("101")).toBeInTheDocument();
    expect(batchButton()).toHaveTextContent("Applica batch (1)");
    expect(note()).toHaveValue("Correzione comune batch da console anomalie");
    expect(mocks.cfItems).not.toHaveBeenCalled();
    expect(mocks.particellaItems).not.toHaveBeenCalled();
    expect(mocks.page).toHaveBeenCalledWith(expect.objectContaining({ requiredModule: "catasto", requiredRoles: ["admin", "super_admin"] }));
  });

  test.each(["workspace=comune", "tab=comune&workspace=cf"])("activates Comune through URL %s", async (query) => {
    mocks.params = new URLSearchParams(query);
    await mountComune();
    expect(mocks.comuneItems).toHaveBeenCalledTimes(1);
    expect(within(screen.getByRole("navigation", { name: "Code anomalie" })).getByRole("button", { name: /Comuni/ })).toHaveAttribute("aria-pressed", "true");
  });

  test("explicit manual mode keeps Comune idle until navigation and resets its URL type", async () => {
    mocks.params = new URLSearchParams("tab=manuale&workspace=comune");
    render(<CatastoAnomaliePage />);
    await waitFor(() => expect(screen.getByRole("button", { name: "Reset contesto" })).toBeEnabled());
    expect(mocks.comuneItems).not.toHaveBeenCalled();
    selectComuneTab();
    await screen.findByText("Utenza com-1");
    const url = new URL(mocks.router.replace.mock.calls.at(-1)![0], "http://localhost");
    expect(url.searchParams.get("tab")).toBe("comune");
    expect(url.searchParams.get("tipo")).toBe("VAL-04-comune_invalido");
  });

  test("uses only year and district for Comune even when overview URL filters and page differ", async () => {
    mocks.params = new URLSearchParams("tab=comune&status=chiusa&severita=warning&anno=2025&distretto=09&page=3");
    await mountComune();
    expect(mocks.comuneItems).toHaveBeenCalledExactlyOnceWith("token", {
      status: "aperta", anno: 2025, distretto: "09", page: 1, pageSize: 25,
    });
    expect(mocks.list).toHaveBeenCalledWith("token", expect.objectContaining({ status: "chiusa", severita: "warning", page: 3 }));
  });

  test("initial loading disables batch and selection controls, then renders the empty queue", async () => {
    const load = deferred<CatAnomaliaComuneWizardListResponse>();
    mocks.comuneItems.mockReturnValue(load.promise);
    render(<CatastoAnomaliePage />);
    expect(within(wizard()).getByText("Caricamento workspace comuni...")).toBeInTheDocument();
    expect(batchButton()).toBeDisabled();
    expect(within(wizard()).getByRole("button", { name: "Seleziona top candidate" })).toBeDisabled();
    expect(within(wizard()).getByRole("button", { name: "Pulisci selezioni" })).toBeDisabled();
    expect(note()).toBeEnabled();
    await act(async () => { load.resolve(response([])); });
    expect(within(wizard()).getByText("Nessuna anomalia comune aperta")).toBeInTheDocument();
    expect(within(wizard()).getByText("0 righe su 0")).toBeInTheDocument();
    expect(batchButton()).toBeDisabled();
    expect(within(wizard()).getByRole("button", { name: "Seleziona top candidate" })).toBeEnabled();
    expect(within(wizard()).queryByRole("button", { name: "Successiva" })).not.toBeInTheDocument();
  });

  test("a row without candidates has no preview or single apply and contributes no batch selection", async () => {
    mocks.comuneItems.mockResolvedValue(response([comuneItem("com-1", { candidates: [] })]));
    await mountComune();
    expect(within(row()).getByText("Nessun comune candidato trovato con i dati correnti. La riga resta in triage manuale.")).toBeInTheDocument();
    expect(within(row()).queryByText("Anteprima prima / dopo")).not.toBeInTheDocument();
    expect(within(row()).queryByRole("button", { name: "Applica solo questa riga" })).not.toBeInTheDocument();
    expect(batchButton()).toHaveTextContent("Applica batch (0)");
    expect(batchButton()).toBeDisabled();
    selectTop();
    fireEvent.click(batchButton());
    expect(mocks.applyComune).not.toHaveBeenCalled();
  });

  test.each([
    [null, 91, "91"],
    [0, 91, "0"],
    [null, null, "—"],
  ])("before preview uses nullish current code %j then source %j", async (current, source, expected) => {
    mocks.comuneItems.mockResolvedValue(response([comuneItem("com-1", {
      nome_comune: null, cod_comune_capacitas: current, source_cod_comune_capacitas: source,
      sezione_catastale: null, foglio: null, particella: null, subalterno: null,
      num_distretto: null, anno_campagna: null,
    })]));
    await mountComune();
    const before = within(row()).getByText("Prima").parentElement!;
    expect(within(before).getByText("Comune:")).toHaveTextContent("Comune: —");
    expect(within(before).getByText("Codice comune:")).toHaveTextContent(`Codice comune: ${expected}`);
  });

  test("candidate selection updates its independent radio group and literal after-preview fields", async () => {
    mocks.comuneItems.mockResolvedValue(response([comuneItem(), comuneItem("com-2")]));
    await mountComune();
    fireEvent.click(radio("com-1", "town-second"));
    expect(radio()).not.toBeChecked();
    expect(radio("com-1", "town-second")).toBeChecked();
    expect(radio("com-2")).toBeChecked();
    const after = within(row()).getByText("Dopo").parentElement!;
    expect(within(after).getByText("Comune town-second")).toBeInTheDocument();
    expect(within(after).getByText("202")).toBeInTheDocument();
    expect(batchButton()).toHaveTextContent("Applica batch (2)");
  });

  test("clear removes all candidate drafts and top selection restores each first candidate, including overwriting prior choices", async () => {
    mocks.comuneItems.mockResolvedValue(response([comuneItem(), comuneItem("com-2", { candidates: [] })]));
    await mountComune();
    fireEvent.click(radio("com-1", "town-second"));
    clearSelection();
    expect(radio()).not.toBeChecked();
    expect(radio("com-1", "town-second")).not.toBeChecked();
    expect(within(row()).queryByText("Anteprima prima / dopo")).not.toBeInTheDocument();
    expect(batchButton()).toHaveTextContent("Applica batch (0)");
    expect(batchButton()).toBeDisabled();
    selectTop();
    expect(radio()).toBeChecked();
    expect(batchButton()).toHaveTextContent("Applica batch (1)");
    fireEvent.click(radio("com-1", "town-second"));
    selectTop();
    expect(radio()).toBeChecked();
  });

  test("pending reload preserves a latest candidate edit and refills a cleared row from its new first candidate", async () => {
    mocks.comuneItems.mockResolvedValue(response([comuneItem(), comuneItem("com-2")]));
    await mountComune();
    clearSelection();
    const load = deferred<CatAnomaliaComuneWizardListResponse>();
    mocks.comuneItems.mockReturnValueOnce(load.promise);
    fireEvent.change(screen.getByLabelText("Anno"), { target: { value: "2025" } });
    expect(batchButton()).toBeDisabled();
    expect(radio("com-1", "town-second")).toBeEnabled();
    fireEvent.click(radio("com-1", "town-second"));
    await act(async () => { load.resolve(response([
      comuneItem(), comuneItem("com-2", { candidates: [candidate("new-first")] }),
    ])); });
    expect(radio("com-1", "town-second")).toBeChecked();
    expect(radio("com-2", "new-first")).toBeChecked();
    expect(batchButton()).toHaveTextContent("Applica batch (2)");
  });

  test("retains an off-page draft but batch applies only selected rows on the current page in response order", async () => {
    mocks.comuneItems.mockResolvedValueOnce(response([comuneItem()], 26));
    await mountComune();
    fireEvent.click(radio("com-1", "town-second"));
    mocks.comuneItems.mockResolvedValueOnce(response([
      comuneItem("com-3", { candidates: [candidate("town-third")] }),
      comuneItem("com-2", { candidates: [candidate("town-other")] }),
      comuneItem("com-4", { candidates: [] }),
    ], 26, 2));
    fireEvent.click(within(wizard()).getByRole("button", { name: "Successiva" }));
    await screen.findByText("Utenza com-3");
    expect(batchButton()).toHaveTextContent("Applica batch (2)");
    fireEvent.click(batchButton());
    await waitFor(() => expect(mocks.applyComune).toHaveBeenCalledExactlyOnceWith("token", [
      { anomalia_id: "com-3", comune_id: "town-third", note_operatore: "Correzione comune batch da console anomalie" },
      { anomalia_id: "com-2", comune_id: "town-other", note_operatore: "Correzione comune batch da console anomalie" },
    ]));
    await waitFor(() => expect(batchButton()).toBeEnabled());
    mocks.comuneItems.mockResolvedValueOnce(response([comuneItem()], 26));
    fireEvent.click(within(wizard()).getByRole("button", { name: "Precedente" }));
    await screen.findByText("Utenza com-1");
    expect(radio("com-1", "town-second")).toBeChecked();
  });

  test("a truthy stale candidate remains selected for batch even after candidates disappear, until clear removes it", async () => {
    await mountComune();
    fireEvent.click(radio("com-1", "town-second"));
    mocks.comuneItems.mockResolvedValueOnce(response([comuneItem("com-1", { candidates: [] })]));
    fireEvent.change(screen.getByLabelText("Distretto"), { target: { value: "8" } });
    await screen.findByText("Nessun comune candidato trovato con i dati correnti. La riga resta in triage manuale.");
    expect(within(row()).queryByText("Anteprima prima / dopo")).not.toBeInTheDocument();
    expect(batchButton()).toHaveTextContent("Applica batch (1)");
    expect(batchButton()).toBeEnabled();
    selectTop();
    fireEvent.click(batchButton());
    await waitFor(() => expect(mocks.applyComune).toHaveBeenCalledExactlyOnceWith("token", [{
      anomalia_id: "com-1", comune_id: "town-second", note_operatore: "Correzione comune batch da console anomalie",
    }]));
    await waitFor(() => expect(batchButton()).toBeEnabled());
    clearSelection();
    expect(batchButton()).toHaveTextContent("Applica batch (0)");
    expect(batchButton()).toBeDisabled();
  });

  test("paginates Comune without changing overview URL page and resets to page one for year, district and context reset", async () => {
    mocks.comuneItems.mockResolvedValue(response([comuneItem()], 51));
    await mountComune();
    const urlCalls = mocks.router.replace.mock.calls.length;
    expect(within(wizard()).getByText("Pagina 1 di 3")).toBeInTheDocument();
    fireEvent.click(within(wizard()).getByRole("button", { name: "Successiva" }));
    await waitFor(() => expect(mocks.comuneItems).toHaveBeenLastCalledWith("token", {
      status: "aperta", anno: undefined, distretto: undefined, page: 2, pageSize: 25,
    }));
    expect(mocks.router.replace).toHaveBeenCalledTimes(urlCalls);
    fireEvent.change(screen.getByLabelText("Anno"), { target: { value: "2025" } });
    await waitFor(() => expect(mocks.comuneItems).toHaveBeenLastCalledWith("token", {
      status: "aperta", anno: 2025, distretto: undefined, page: 1, pageSize: 25,
    }));
    fireEvent.click(within(wizard()).getByRole("button", { name: "Successiva" }));
    fireEvent.change(screen.getByLabelText("Distretto"), { target: { value: "07" } });
    await waitFor(() => expect(mocks.comuneItems).toHaveBeenLastCalledWith("token", {
      status: "aperta", anno: 2025, distretto: "07", page: 1, pageSize: 25,
    }));
    await waitFor(() => expect(screen.getByRole("button", { name: "Reset contesto" })).toBeEnabled());
    fireEvent.click(screen.getByRole("button", { name: "Reset contesto" }));
    await waitFor(() => expect(mocks.comuneItems).toHaveBeenLastCalledWith("token", {
      status: "aperta", anno: undefined, distretto: undefined, page: 1, pageSize: 25,
    }));
  });

  test("an empty positive-total later page reloads page one before changing the current candidate rows", async () => {
    mocks.comuneItems.mockResolvedValueOnce(response([comuneItem()], 26));
    await mountComune();
    const recovery = deferred<CatAnomaliaComuneWizardListResponse>();
    mocks.comuneItems.mockResolvedValueOnce(response([], 1, 2)).mockReturnValueOnce(recovery.promise);
    fireEvent.click(within(wizard()).getByRole("button", { name: "Successiva" }));
    await waitFor(() => expect(mocks.comuneItems).toHaveBeenCalledTimes(3));
    expect(mocks.comuneItems).toHaveBeenNthCalledWith(2, "token", {
      status: "aperta", anno: undefined, distretto: undefined, page: 2, pageSize: 25,
    });
    expect(mocks.comuneItems).toHaveBeenNthCalledWith(3, "token", {
      status: "aperta", anno: undefined, distretto: undefined, page: 1, pageSize: 25,
    });
    expect(radio()).toBeChecked();
    await act(async () => { recovery.resolve(response([comuneItem("com-2")], 1)); });
    expect(screen.queryByText("Utenza com-1")).not.toBeInTheDocument();
    expect(within(wizard()).getByRole("button", { name: "Successiva" })).toBeDisabled();
  });

  test("an empty positive-total first page renders empty without a second load", async () => {
    mocks.comuneItems.mockResolvedValue(response([], 4));
    render(<CatastoAnomaliePage />);
    await screen.findByText("Nessuna anomalia comune aperta");
    await waitFor(() => expect(within(wizard()).getByText("0 righe su 4")).toBeInTheDocument());
    expect(mocks.comuneItems).toHaveBeenCalledTimes(1);
  });

  test.each([
    [new Error("Comune load rejected"), "Comune load rejected"],
    ["offline", "Errore caricamento workspace comuni"],
  ])("load error %j is displayed and released, then clears after successful context reload", async (reason, message) => {
    mocks.comuneItems.mockRejectedValueOnce(reason);
    render(<CatastoAnomaliePage />);
    expect(await screen.findByText(message)).toBeInTheDocument();
    expect(within(wizard()).queryByText("Caricamento workspace comuni...")).not.toBeInTheDocument();
    expect(within(wizard()).getByRole("button", { name: "Pulisci selezioni" })).toBeEnabled();
    fireEvent.change(screen.getByLabelText("Distretto"), { target: { value: "9" } });
    await screen.findByText("Utenza com-1");
    expect(screen.queryByText(message)).not.toBeInTheDocument();
    expect(radio()).toBeChecked();
  });

  test("a failed reload retains the selected candidate and old item total", async () => {
    await mountComune();
    fireEvent.click(radio("com-1", "town-second"));
    mocks.comuneItems.mockRejectedValueOnce(new Error("Comune refresh unavailable"));
    fireEvent.change(screen.getByLabelText("Anno"), { target: { value: "2024" } });
    await screen.findByText("Comune refresh unavailable");
    expect(radio("com-1", "town-second")).toBeChecked();
    expect(within(wizard()).getByText("1 righe su 1")).toBeInTheDocument();
    expect(batchButton()).toBeEnabled();
  });

  test("a missing initial token leaves Comune idle and empty while report lookups still load", async () => {
    mocks.token.mockReturnValue(null);
    render(<CatastoAnomaliePage />);
    await waitFor(() => expect(mocks.categories).toHaveBeenCalledTimes(1));
    expect(mocks.comuneItems).not.toHaveBeenCalled();
    expect(mocks.list).not.toHaveBeenCalled();
    expect(within(wizard()).getByText("Nessuna anomalia comune aperta")).toBeInTheDocument();
    expect(batchButton()).toBeDisabled();
    expect(within(wizard()).queryByText("Sincronizzazione...")).not.toBeInTheDocument();
  });

  test.each([
    ["  custom single note  ", "custom single note"],
    ["   ", "Correzione comune da console anomalie"],
    ["", "Correzione comune da console anomalie"],
  ])("single apply uses selected candidate and trimmed/fallback note %j", async (draft, expected) => {
    await mountComune();
    fireEvent.click(radio("com-1", "town-second"));
    fireEvent.change(note(), { target: { value: draft } });
    fireEvent.click(singleButton());
    await waitFor(() => expect(mocks.applyComune).toHaveBeenCalledExactlyOnceWith("token", [{
      anomalia_id: "com-1", comune_id: "town-second", note_operatore: expected,
    }]));
    expect(await screen.findByText("Correzione applicata: 2 utenza aggiornata, 3 anomalie comune chiuse.")).toBeInTheDocument();
    await waitFor(() => expect(singleButton()).toBeEnabled());
  });

  test.each([
    ["  custom batch note  ", "custom batch note"],
    ["   ", "Correzione comune batch da console anomalie"],
    ["", "Correzione comune batch da console anomalie"],
  ])("batch apply annotates its selected item with trimmed/fallback note %j", async (draft, expected) => {
    await mountComune();
    fireEvent.change(note(), { target: { value: draft } });
    fireEvent.click(batchButton());
    await waitFor(() => expect(mocks.applyComune).toHaveBeenCalledExactlyOnceWith("token", [{
      anomalia_id: "com-1", comune_id: "town-first", note_operatore: expected,
    }]));
    expect(await screen.findByText("Batch applicato: 2 utenze aggiornate, 3 anomalie comune chiuse.")).toBeInTheDocument();
    await waitFor(() => expect(batchButton()).toBeEnabled());
  });

  test("batch excludes falsey drafts after clear and counts only explicitly selected current items", async () => {
    mocks.comuneItems.mockResolvedValue(response([comuneItem(), comuneItem("com-2")]));
    await mountComune();
    clearSelection();
    fireEvent.click(radio("com-2", "town-second"));
    expect(batchButton()).toHaveTextContent("Applica batch (1)");
    fireEvent.click(batchButton());
    await waitFor(() => expect(mocks.applyComune).toHaveBeenCalledExactlyOnceWith("token", [{
      anomalia_id: "com-2", comune_id: "town-second", note_operatore: "Correzione comune batch da console anomalie",
    }]));
    await waitFor(() => expect(batchButton()).toBeEnabled());
  });

  test("single captures candidate and note before mutation and waits for overview and Comune refresh", async () => {
    await mountComune();
    const apply = deferred<CatAnomaliaComuneWizardApplyResponse>();
    const list = deferred<{ items: never[]; total: number }>();
    const summary = deferred<{ buckets: never[]; total: number }>();
    const load = deferred<CatAnomaliaComuneWizardListResponse>();
    mocks.applyComune.mockReturnValueOnce(apply.promise);
    mocks.list.mockReturnValueOnce(list.promise);
    mocks.summary.mockReturnValueOnce(summary.promise);
    mocks.comuneItems.mockReturnValueOnce(load.promise);
    fireEvent.change(note(), { target: { value: " captured single " } });
    fireEvent.click(singleButton());
    expect(singleButton()).toBeDisabled();
    expect(batchButton()).toBeEnabled();
    fireEvent.click(radio("com-1", "town-second"));
    fireEvent.change(note(), { target: { value: "latest note" } });
    expect(mocks.applyComune).toHaveBeenCalledExactlyOnceWith("token", [{
      anomalia_id: "com-1", comune_id: "town-first", note_operatore: "captured single",
    }]);
    expect(mocks.comuneItems).toHaveBeenCalledTimes(1);
    await act(async () => { apply.resolve({ applied_count: 1, updated_utenze: 4, closed_anomalies: 5 }); });
    expect(within(wizard()).getByText("Correzione applicata: 4 utenza aggiornata, 5 anomalie comune chiuse.")).toBeInTheDocument();
    expect(mocks.list).toHaveBeenCalledTimes(2);
    expect(mocks.summary).toHaveBeenCalledTimes(2);
    expect(mocks.comuneItems).toHaveBeenCalledTimes(2);
    expect(mocks.list.mock.invocationCallOrder[1]).toBeLessThan(mocks.comuneItems.mock.invocationCallOrder[1]);
    expect(mocks.cfItems).not.toHaveBeenCalled();
    expect(mocks.particellaItems).not.toHaveBeenCalled();
    expect(mocks.adeSummary).toHaveBeenCalledTimes(1);
    await act(async () => { load.resolve(response([comuneItem()])); });
    expect(radio("com-1", "town-second")).toBeChecked();
    expect(note()).toHaveValue("latest note");
    expect(singleButton()).toBeDisabled();
    await act(async () => { list.resolve({ items: [], total: 0 }); });
    expect(singleButton()).toBeDisabled();
    await act(async () => { summary.resolve({ buckets: [], total: 0 }); });
    expect(singleButton()).toBeEnabled();
  });

  test("batch locks single applies but permits draft controls while mutation is pending and releases after all refreshes", async () => {
    mocks.comuneItems.mockResolvedValue(response([comuneItem(), comuneItem("com-2")]));
    await mountComune();
    const apply = deferred<CatAnomaliaComuneWizardApplyResponse>();
    const list = deferred<{ items: never[]; total: number }>();
    const load = deferred<CatAnomaliaComuneWizardListResponse>();
    mocks.applyComune.mockReturnValueOnce(apply.promise);
    mocks.list.mockReturnValueOnce(list.promise);
    mocks.comuneItems.mockReturnValueOnce(load.promise);
    fireEvent.click(batchButton());
    expect(batchButton()).toBeDisabled();
    expect(singleButton()).toBeDisabled();
    expect(singleButton("com-2")).toBeDisabled();
    expect(within(wizard()).getByRole("button", { name: "Pulisci selezioni" })).toBeEnabled();
    clearSelection();
    fireEvent.click(radio("com-2", "town-second"));
    expect(mocks.applyComune).toHaveBeenCalledExactlyOnceWith("token", [
      { anomalia_id: "com-1", comune_id: "town-first", note_operatore: "Correzione comune batch da console anomalie" },
      { anomalia_id: "com-2", comune_id: "town-first", note_operatore: "Correzione comune batch da console anomalie" },
    ]);
    await act(async () => { apply.resolve({ applied_count: 2, updated_utenze: 2, closed_anomalies: 4 }); });
    expect(within(wizard()).getByText("Batch applicato: 2 utenze aggiornate, 4 anomalie comune chiuse.")).toBeInTheDocument();
    expect(within(wizard()).getByRole("button", { name: "Pulisci selezioni" })).toBeDisabled();
    await act(async () => { load.resolve(response([comuneItem(), comuneItem("com-2")])); });
    expect(radio()).toBeChecked();
    expect(radio("com-2", "town-second")).toBeChecked();
    expect(batchButton()).toBeDisabled();
    await act(async () => { list.resolve({ items: [], total: 0 }); });
    expect(batchButton()).toBeEnabled();
    expect(singleButton()).toBeEnabled();
  });

  test.each([
    [new Error("Single rejected"), "Single rejected"],
    [{ detail: "offline" }, "Errore correzione comune"],
  ])("single failure %j preserves selection and note, skips refresh and supports retry", async (reason, message) => {
    await mountComune();
    mocks.applyComune.mockRejectedValueOnce(reason);
    fireEvent.click(radio("com-1", "town-second"));
    fireEvent.change(note(), { target: { value: " retry note " } });
    fireEvent.click(singleButton());
    expect(await screen.findByText(message)).toBeInTheDocument();
    expect(singleButton()).toBeEnabled();
    expect(radio("com-1", "town-second")).toBeChecked();
    expect(note()).toHaveValue(" retry note ");
    expect(mocks.comuneItems).toHaveBeenCalledTimes(1);
    expect(mocks.list).toHaveBeenCalledTimes(1);
    fireEvent.click(singleButton());
    await screen.findByText("Correzione applicata: 2 utenza aggiornata, 3 anomalie comune chiuse.");
    expect(screen.queryByText(message)).not.toBeInTheDocument();
    await waitFor(() => expect(singleButton()).toBeEnabled());
  });

  test.each([
    [new Error("Batch rejected"), "Batch rejected"],
    ["offline", "Errore batch correzione comuni"],
  ])("batch failure %j preserves selection, skips refresh and clears on a successful retry", async (reason, message) => {
    await mountComune();
    mocks.applyComune.mockRejectedValueOnce(reason);
    fireEvent.click(batchButton());
    expect(await screen.findByText(message)).toBeInTheDocument();
    expect(batchButton()).toBeEnabled();
    expect(singleButton()).toBeEnabled();
    expect(radio()).toBeChecked();
    expect(mocks.comuneItems).toHaveBeenCalledTimes(1);
    expect(mocks.list).toHaveBeenCalledTimes(1);
    fireEvent.click(batchButton());
    await screen.findByText("Batch applicato: 2 utenze aggiornate, 3 anomalie comune chiuse.");
    expect(screen.queryByText(message)).not.toBeInTheDocument();
    await waitFor(() => expect(batchButton()).toBeEnabled());
  });

  test.each(["single", "batch"])("a token lost before %s apply leaves existing error feedback untouched", async (mode) => {
    await mountComune();
    mocks.applyComune.mockRejectedValueOnce(new Error("Existing Comune error"));
    fireEvent.click(singleButton());
    await screen.findByText("Existing Comune error");
    mocks.token.mockReturnValue(null);
    fireEvent.click(mode === "single" ? singleButton() : batchButton());
    expect(mocks.applyComune).toHaveBeenCalledTimes(1);
    expect(within(wizard()).getByText("Existing Comune error")).toBeInTheDocument();
    expect(singleButton()).toBeEnabled();
    expect(batchButton()).toBeEnabled();
  });

  test("a new batch clears prior single success immediately and shows zero response counts literally", async () => {
    await mountComune();
    fireEvent.click(singleButton());
    await screen.findByText("Correzione applicata: 2 utenza aggiornata, 3 anomalie comune chiuse.");
    await waitFor(() => expect(batchButton()).toBeEnabled());
    const apply = deferred<CatAnomaliaComuneWizardApplyResponse>();
    mocks.applyComune.mockReturnValueOnce(apply.promise);
    fireEvent.click(batchButton());
    expect(screen.queryByText("Correzione applicata: 2 utenza aggiornata, 3 anomalie comune chiuse.")).not.toBeInTheDocument();
    await act(async () => { apply.resolve({ applied_count: 0, updated_utenze: 0, closed_anomalies: 0 }); });
    expect(within(wizard()).getByText("Batch applicato: 0 utenze aggiornate, 0 anomalie comune chiuse.")).toBeInTheDocument();
    expect(batchButton()).toBeEnabled();
  });

  test.each(["single", "batch"])("Comune reload failure after %s success retains both success and reload error", async (mode) => {
    await mountComune();
    mocks.comuneItems.mockRejectedValueOnce(new Error("Post-apply Comune load failed"));
    fireEvent.click(mode === "single" ? singleButton() : batchButton());
    await screen.findByText("Post-apply Comune load failed");
    const expected = mode === "single"
      ? "Correzione applicata: 2 utenza aggiornata, 3 anomalie comune chiuse."
      : "Batch applicato: 2 utenze aggiornate, 3 anomalie comune chiuse.";
    expect(within(wizard()).getByText(expected)).toBeInTheDocument();
    expect(singleButton()).toBeEnabled();
    expect(batchButton()).toBeEnabled();
  });

  test("overview refresh failure is independent of a successful Comune batch and empty refreshed Comune queue", async () => {
    await mountComune();
    mocks.list.mockRejectedValueOnce(new Error("Overview unavailable"));
    mocks.comuneItems.mockResolvedValueOnce(response([]));
    fireEvent.click(batchButton());
    await screen.findByText("Overview unavailable");
    expect(within(wizard()).getByText("Batch applicato: 2 utenze aggiornate, 3 anomalie comune chiuse.")).toBeInTheDocument();
    expect(within(wizard()).getByText("Nessuna anomalia comune aperta")).toBeInTheDocument();
    expect(batchButton()).toHaveTextContent("Applica batch (0)");
    expect(screen.queryByText("Utenza com-1")).not.toBeInTheDocument();
  });

  test("a token lost during batch mutation prevents refreshed requests but retains the success", async () => {
    await mountComune();
    const apply = deferred<CatAnomaliaComuneWizardApplyResponse>();
    mocks.applyComune.mockReturnValueOnce(apply.promise);
    fireEvent.click(batchButton());
    mocks.token.mockReturnValue(null);
    await act(async () => { apply.resolve({ applied_count: 1, updated_utenze: 1, closed_anomalies: 2 }); });
    expect(within(wizard()).getByText("Batch applicato: 1 utenze aggiornate, 2 anomalie comune chiuse.")).toBeInTheDocument();
    expect(mocks.comuneItems).toHaveBeenCalledTimes(1);
    expect(mocks.list).toHaveBeenCalledTimes(1);
    expect(batchButton()).toBeEnabled();
  });

  test("original overlapping Comune loads allow older candidate rows to replace newer rows without pruning retained drafts", async () => {
    await mountComune();
    const older = deferred<CatAnomaliaComuneWizardListResponse>();
    const newer = deferred<CatAnomaliaComuneWizardListResponse>();
    mocks.comuneItems.mockReturnValueOnce(older.promise).mockReturnValueOnce(newer.promise);
    fireEvent.change(screen.getByLabelText("Anno"), { target: { value: "2025" } });
    fireEvent.change(screen.getByLabelText("Anno"), { target: { value: "2024" } });
    await act(async () => { newer.resolve(response([comuneItem("newer")])); });
    expect(screen.getByText("Utenza newer")).toBeInTheDocument();
    expect(within(wizard()).queryByText("Sincronizzazione...")).not.toBeInTheDocument();
    await act(async () => { older.resolve(response([comuneItem("older")])); });
    expect(screen.getByText("Utenza older")).toBeInTheDocument();
    expect(screen.queryByText("Utenza newer")).not.toBeInTheDocument();
    expect(screen.getByLabelText("Anno")).toHaveValue("2024");
  });

  test("a pending batch refresh retains captured year while public selection and note edits remain latest", async () => {
    await mountComune();
    const apply = deferred<CatAnomaliaComuneWizardApplyResponse>();
    mocks.applyComune.mockReturnValueOnce(apply.promise);
    fireEvent.click(batchButton());
    fireEvent.change(screen.getByLabelText("Anno"), { target: { value: "2025" } });
    fireEvent.click(radio("com-1", "town-second"));
    fireEvent.change(note(), { target: { value: "latest pending note" } });
    await waitFor(() => expect(mocks.comuneItems).toHaveBeenCalledTimes(2));
    expect(mocks.comuneItems).toHaveBeenNthCalledWith(2, "token", {
      status: "aperta", anno: 2025, distretto: undefined, page: 1, pageSize: 25,
    });
    await act(async () => { apply.resolve({ applied_count: 1, updated_utenze: 1, closed_anomalies: 2 }); });
    expect(mocks.comuneItems).toHaveBeenNthCalledWith(3, "token", {
      status: "aperta", anno: undefined, distretto: undefined, page: 1, pageSize: 25,
    });
    expect(radio("com-1", "town-second")).toBeChecked();
    expect(note()).toHaveValue("latest pending note");
    expect(screen.getByLabelText("Anno")).toHaveValue("2025");
  });

  test("a pending single still runs its captured Comune refresh after tab exit, then entry resets page and messages", async () => {
    mocks.comuneItems.mockResolvedValue(response([comuneItem()], 26));
    await mountComune();
    fireEvent.click(within(wizard()).getByRole("button", { name: "Successiva" }));
    await waitFor(() => expect(mocks.comuneItems).toHaveBeenCalledTimes(2));
    const apply = deferred<CatAnomaliaComuneWizardApplyResponse>();
    mocks.applyComune.mockReturnValueOnce(apply.promise);
    fireEvent.click(singleButton());
    selectManualTab();
    expect(screen.queryByText("Wizard comune invalido")).not.toBeInTheDocument();
    await act(async () => { apply.resolve({ applied_count: 1, updated_utenze: 1, closed_anomalies: 2 }); });
    expect(mocks.comuneItems).toHaveBeenCalledTimes(3);
    expect(mocks.comuneItems).toHaveBeenLastCalledWith("token", expect.objectContaining({ page: 2 }));
    selectComuneTab();
    await screen.findByText("Utenza com-1");
    await waitFor(() => expect(mocks.comuneItems).toHaveBeenCalledTimes(4));
    expect(mocks.comuneItems).toHaveBeenLastCalledWith("token", {
      status: "aperta", anno: undefined, distretto: undefined, page: 1, pageSize: 25,
    });
    expect(within(wizard()).queryByText("Correzione applicata: 1 utenza aggiornata, 2 anomalie comune chiuse.")).not.toBeInTheDocument();
  });

  test("single then batch can overlap and the original scalar busy ID can release an outstanding batch", async () => {
    await mountComune();
    const single = deferred<CatAnomaliaComuneWizardApplyResponse>();
    const batch = deferred<CatAnomaliaComuneWizardApplyResponse>();
    mocks.applyComune.mockReturnValueOnce(single.promise).mockReturnValueOnce(batch.promise);
    fireEvent.click(singleButton());
    expect(singleButton()).toBeDisabled();
    expect(batchButton()).toBeEnabled();
    fireEvent.click(batchButton());
    expect(batchButton()).toBeDisabled();
    expect(singleButton()).toBeDisabled();
    await act(async () => { single.resolve({ applied_count: 1, updated_utenze: 1, closed_anomalies: 1 }); });
    expect(batchButton()).toBeEnabled();
    expect(singleButton()).toBeEnabled();
    await act(async () => { batch.resolve({ applied_count: 1, updated_utenze: 2, closed_anomalies: 2 }); });
    expect(within(wizard()).getByText("Batch applicato: 2 utenze aggiornate, 2 anomalie comune chiuse.")).toBeInTheDocument();
    expect(mocks.comuneItems).toHaveBeenCalledTimes(3);
  });
});
