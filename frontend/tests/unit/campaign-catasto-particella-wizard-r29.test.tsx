import type { ReactNode } from "react";
import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import CatastoAnomaliePage from "@/app/catasto/anomalie/page";
import type {
  CatAnomaliaParticellaCandidate,
  CatAnomaliaParticellaWizardApplyResponse,
  CatAnomaliaParticellaWizardItem,
  CatAnomaliaParticellaWizardListResponse,
} from "@/types/catasto";

const mocks = vi.hoisted(() => ({
  params: new URLSearchParams("tab=particella"),
  router: { replace: vi.fn() },
  token: vi.fn(),
  list: vi.fn(),
  summary: vi.fn(),
  particellaItems: vi.fn(),
  applyParticella: vi.fn(),
  cfItems: vi.fn(),
  comuneItems: vi.fn(),
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
  catastoGetParticellaWizardItems: mocks.particellaItems,
  catastoApplyParticellaWizard: mocks.applyParticella,
  catastoGetCfWizardItems: mocks.cfItems,
  catastoGetComuneWizardItems: mocks.comuneItems,
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

function candidate(id = "parcel-first", overrides: Partial<CatAnomaliaParticellaCandidate> = {}): CatAnomaliaParticellaCandidate {
  return {
    id,
    cod_comune_capacitas: 101,
    codice_catastale: "H501",
    nome_comune: `Comune ${id}`,
    sezione_catastale: "B",
    foglio: "23",
    particella: "45",
    subalterno: "3",
    num_distretto: "7",
    nome_distretto: "Distretto sette",
    ha_anagrafica: true,
    match_score: 0.2,
    ...overrides,
  };
}

function parcelItem(id = "par-1", overrides: Partial<CatAnomaliaParticellaWizardItem> = {}): CatAnomaliaParticellaWizardItem {
  return {
    anomalia_id: id,
    utenza_id: "utenza-1",
    anno_campagna: 2026,
    tipo: "VAL-05-particella_assente",
    severita: "error",
    descrizione: "Particella da collegare",
    status: "aperta",
    denominazione: `Utenza ${id}`,
    nome_comune: "Comune originale",
    cod_comune_capacitas: 90,
    num_distretto: 7,
    sezione_catastale: "A",
    foglio: "12",
    particella: "34",
    subalterno: "1",
    candidates: [candidate(), candidate("parcel-second", { foglio: "99", match_score: 0.9, ha_anagrafica: false })],
    created_at: "2026-10-11T11:00:00Z",
    ...overrides,
  };
}

function response(items: CatAnomaliaParticellaWizardItem[], total = items.length, page = 1): CatAnomaliaParticellaWizardListResponse {
  return { items, total, page, page_size: 25 };
}

function deferred<Value>() {
  let resolve!: (value: Value) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<Value>((fulfill, fail) => { resolve = fulfill; reject = fail; });
  return { promise, resolve, reject };
}

function wizard() {
  return screen.getByText("Wizard particella assente").closest<HTMLDivElement>("article")!;
}

function row(id = "par-1") {
  return screen.getByText(`Utenza ${id}`).closest<HTMLDivElement>("div.rounded-2xl")!;
}

function radio(id = "par-1", parcel = "parcel-first") {
  return within(row(id)).getByRole("radio", { name: new RegExp(`Comune ${parcel} `) });
}

function singleButton(id = "par-1") {
  return within(row(id)).getByRole("button", { name: /Applica solo questa riga|Applicazione\.\.\./ });
}

function batchButton() {
  return within(wizard()).getByRole("button", { name: /Applica batch|Applicazione batch/ });
}

function note() {
  return screen.getByLabelText("Nota batch applicata alle correzioni");
}

function selectTop() {
  fireEvent.click(within(wizard()).getByRole("button", { name: "Seleziona top candidate" }));
}

function clearSelection() {
  fireEvent.click(within(wizard()).getByRole("button", { name: "Pulisci selezioni" }));
}

function selectTab(name: RegExp) {
  fireEvent.click(within(screen.getByRole("navigation", { name: "Code anomalie" })).getByRole("button", { name }));
}

async function mountParticella() {
  const view = render(<CatastoAnomaliePage />);
  await screen.findByText("Utenza par-1");
  await waitFor(() => expect(within(wizard()).queryByText("Sincronizzazione...")).not.toBeInTheDocument());
  await waitFor(() => expect(screen.getByRole("button", { name: "Reset contesto" })).toBeEnabled());
  return view;
}

beforeEach(() => {
  vi.resetAllMocks();
  mocks.params = new URLSearchParams("tab=particella");
  mocks.token.mockReturnValue("token");
  mocks.list.mockResolvedValue({ items: [], total: 0, page: 1, page_size: 50 });
  mocks.summary.mockResolvedValue({ buckets: [], total: 0 });
  mocks.particellaItems.mockResolvedValue(response([parcelItem()]));
  mocks.applyParticella.mockResolvedValue({ applied_count: 1, updated_utenze: 2, closed_anomalies: 3 });
  mocks.cfItems.mockResolvedValue({ items: [], total: 0 });
  mocks.comuneItems.mockResolvedValue({ items: [], total: 0 });
  mocks.adeSummary.mockResolvedValue({});
  mocks.adeCandidates.mockResolvedValue({ items: [], total: 0 });
  mocks.batches.mockResolvedValue([]);
  mocks.users.mockResolvedValue({ items: [] });
  mocks.categories.mockResolvedValue([]);
  mocks.severities.mockResolvedValue([]);
});

afterEach(cleanup);

describe("R29 original Particella public selection and correction lifecycle", () => {
  test("loads the literal open25 query and selects response-first rather than score-highest with exact preview", async () => {
    await mountParticella();
    expect(mocks.particellaItems).toHaveBeenCalledExactlyOnceWith("token", {
      status: "aperta", anno: undefined, distretto: undefined, page: 1, pageSize: 25,
    });
    expect(radio()).toBeChecked();
    expect(radio("par-1", "parcel-second")).not.toBeChecked();
    expect(batchButton()).toHaveTextContent("Applica batch (1)");
    expect(note()).toHaveValue("Collegamento particella batch da console anomalie");
    const before = within(row()).getByText("Prima").parentElement!;
    const after = within(row()).getByText("Dopo").parentElement!;
    expect(within(before).getByText("Riferimento:")).toHaveTextContent("A / 12 / 34 / 1");
    expect(within(before).getByText("Particella collegata:")).toHaveTextContent("assente");
    expect(within(after).getByText("Comune:")).toHaveTextContent("Comune parcel-first");
    expect(within(after).getByText("Riferimento:")).toHaveTextContent("B / 23 / 45 / 3");
    expect(mocks.cfItems).not.toHaveBeenCalled();
    expect(mocks.comuneItems).not.toHaveBeenCalled();
    expect(mocks.page).toHaveBeenCalledWith(expect.objectContaining({ requiredModule: "catasto", requiredRoles: ["admin", "super_admin"] }));
  });

  test.each(["workspace=particella", "tab=particella&workspace=cf"])("resolves URL %s into the Particelle tab", async (query) => {
    mocks.params = new URLSearchParams(query);
    await mountParticella();
    expect(within(screen.getByRole("navigation", { name: "Code anomalie" })).getByRole("button", { name: /Particelle/ })).toHaveAttribute("aria-pressed", "true");
  });

  test("manual tab takes precedence until public navigation sets canonical type and URL", async () => {
    mocks.params = new URLSearchParams("tab=manuale&workspace=particella");
    render(<CatastoAnomaliePage />);
    await waitFor(() => expect(screen.getByRole("button", { name: "Reset contesto" })).toBeEnabled());
    expect(mocks.particellaItems).not.toHaveBeenCalled();
    selectTab(/Particelle/);
    await screen.findByText("Utenza par-1");
    const url = new URL(mocks.router.replace.mock.calls.at(-1)![0], "http://localhost");
    expect(url.searchParams.get("tab")).toBe("particella");
    expect(url.searchParams.get("tipo")).toBe("VAL-05-particella_assente");
  });

  test("uses year and raw district but ignores overview closed status, severity and page", async () => {
    mocks.params = new URLSearchParams("tab=particella&status=chiusa&severita=warning&anno=2025&distretto=09&page=3");
    await mountParticella();
    expect(mocks.particellaItems).toHaveBeenCalledExactlyOnceWith("token", {
      status: "aperta", anno: 2025, distretto: "09", page: 1, pageSize: 25,
    });
    expect(mocks.list).toHaveBeenCalledWith("token", expect.objectContaining({ status: "chiusa", severita: "warning", page: 3 }));
  });

  test("initial deferred load disables batch/top/clear but not note before rendering the empty queue", async () => {
    const load = deferred<CatAnomaliaParticellaWizardListResponse>();
    mocks.particellaItems.mockReturnValueOnce(load.promise);
    render(<CatastoAnomaliePage />);
    expect(within(wizard()).getByText("Caricamento workspace particelle...")).toBeInTheDocument();
    expect(batchButton()).toBeDisabled();
    expect(within(wizard()).getByRole("button", { name: "Seleziona top candidate" })).toBeDisabled();
    expect(within(wizard()).getByRole("button", { name: "Pulisci selezioni" })).toBeDisabled();
    expect(note()).toBeEnabled();
    await act(async () => { load.resolve(response([])); });
    expect(within(wizard()).getByText("Nessuna anomalia particella aperta")).toBeInTheDocument();
    expect(within(wizard()).getByText("0 righe su 0")).toBeInTheDocument();
    expect(within(wizard()).queryByRole("button", { name: "Successiva" })).not.toBeInTheDocument();
  });

  test("rows without candidates cannot preview or apply and clear/top only operate on candidate drafts", async () => {
    mocks.particellaItems.mockResolvedValue(response([parcelItem(), parcelItem("par-2", { candidates: [] })]));
    await mountParticella();
    expect(within(row("par-2")).queryByText("Anteprima prima / dopo")).not.toBeInTheDocument();
    expect(within(row("par-2")).queryByRole("button", { name: "Applica solo questa riga" })).not.toBeInTheDocument();
    fireEvent.click(radio("par-1", "parcel-second"));
    expect(radio("par-1", "parcel-second")).toBeChecked();
    clearSelection();
    expect(batchButton()).toHaveTextContent("Applica batch (0)");
    expect(batchButton()).toBeDisabled();
    fireEvent.click(batchButton());
    expect(mocks.applyParticella).not.toHaveBeenCalled();
    expect(within(row()).queryByText("Anteprima prima / dopo")).not.toBeInTheDocument();
    selectTop();
    expect(radio()).toBeChecked();
    fireEvent.click(radio("par-1", "parcel-second"));
    selectTop();
    expect(radio()).toBeChecked();
    expect(batchButton()).toHaveTextContent("Applica batch (1)");
  });

  test("radio groups are independent and changing candidate updates the literal after-preview", async () => {
    mocks.particellaItems.mockResolvedValue(response([parcelItem(), parcelItem("par-2")]));
    await mountParticella();
    fireEvent.click(radio("par-1", "parcel-second"));
    expect(radio()).not.toBeChecked();
    expect(radio("par-2")).toBeChecked();
    const after = within(row()).getByText("Dopo").parentElement!;
    expect(within(after).getByText("Comune:")).toHaveTextContent("Comune parcel-second");
    expect(within(after).getByText("Riferimento:")).toHaveTextContent("B / 99 / 45 / 3");
    expect(within(row()).getByText("Assente")).toBeInTheDocument();
    expect(batchButton()).toHaveTextContent("Applica batch (2)");
  });

  test("nullable row and candidate display fields retain nullish zero versus fallback behavior", async () => {
    mocks.particellaItems.mockResolvedValue(response([parcelItem("par-1", {
      nome_comune: null, cod_comune_capacitas: 0, num_distretto: 0, anno_campagna: null,
      sezione_catastale: null, foglio: null, particella: null, subalterno: null,
      candidates: [candidate("parcel-first", { nome_comune: null, codice_catastale: null, num_distretto: null, sezione_catastale: null, subalterno: null })],
    })]));
    await mountParticella();
    const before = within(row()).getByText("Prima").parentElement!;
    const after = within(row()).getByText("Dopo").parentElement!;
    expect(within(before).getByText("Comune:")).toHaveTextContent("Comune: —");
    expect(within(before).getByText("Riferimento:")).toHaveTextContent("Riferimento: —");
    expect(within(after).getByText("Comune:")).toHaveTextContent("Comune: —");
    expect(within(after).getByText("Riferimento:")).toHaveTextContent("23 / 45");
    expect(within(after).getByText("Distretto:")).toHaveTextContent("Distretto: —");
    expect(within(row()).getByText("Codice comune:")).toHaveTextContent("Codice comune: 0");
  });

  test("local without-candidates view hides selected rows but batch still applies them in response order", async () => {
    mocks.particellaItems.mockResolvedValue(response([parcelItem(), parcelItem("par-2", { candidates: [] }), parcelItem("par-3")]));
    await mountParticella();
    const loads = mocks.particellaItems.mock.calls.length;
    fireEvent.change(within(wizard()).getByLabelText("Vista"), { target: { value: "without_candidates" } });
    expect(screen.queryByText("Utenza par-1")).not.toBeInTheDocument();
    expect(screen.getByText("Utenza par-2")).toBeInTheDocument();
    expect(batchButton()).toHaveTextContent("Applica batch (2)");
    expect(mocks.particellaItems).toHaveBeenCalledTimes(loads);
    fireEvent.click(batchButton());
    await waitFor(() => expect(mocks.applyParticella).toHaveBeenCalledExactlyOnceWith("token", [
      { anomalia_id: "par-1", particella_id: "parcel-first", note_operatore: "Collegamento particella batch da console anomalie" },
      { anomalia_id: "par-3", particella_id: "parcel-first", note_operatore: "Collegamento particella batch da console anomalie" },
    ]));
    await waitFor(() => expect(batchButton()).toBeEnabled());
  });

  test("local without-candidates view can be empty while the queue and batch selection remain nonempty", async () => {
    await mountParticella();
    fireEvent.change(within(wizard()).getByLabelText("Vista"), { target: { value: "without_candidates" } });
    expect(within(wizard()).getByText("Nessuna riga nella vista corrente")).toBeInTheDocument();
    expect(within(wizard()).getByText("1 righe su 1")).toBeInTheDocument();
    expect(batchButton()).toBeEnabled();
    fireEvent.change(within(wizard()).getByLabelText("Vista"), { target: { value: "all" } });
    expect(radio()).toBeChecked();
  });

  test("a pending reload preserves an intervening radio choice and refills cleared drafts from the new first candidate", async () => {
    mocks.particellaItems.mockResolvedValue(response([parcelItem(), parcelItem("par-2")]));
    await mountParticella();
    clearSelection();
    const load = deferred<CatAnomaliaParticellaWizardListResponse>();
    mocks.particellaItems.mockReturnValueOnce(load.promise);
    fireEvent.change(screen.getByLabelText("Anno"), { target: { value: "2025" } });
    expect(batchButton()).toBeDisabled();
    expect(radio("par-1", "parcel-second")).toBeEnabled();
    fireEvent.click(radio("par-1", "parcel-second"));
    await act(async () => { load.resolve(response([parcelItem(), parcelItem("par-2", { candidates: [candidate("parcel-new")] })])); });
    expect(radio("par-1", "parcel-second")).toBeChecked();
    expect(radio("par-2", "parcel-new")).toBeChecked();
  });

  test("off-page drafts persist but batch serializes only current selected rows in response order", async () => {
    mocks.particellaItems.mockResolvedValueOnce(response([parcelItem()], 26));
    await mountParticella();
    fireEvent.click(radio("par-1", "parcel-second"));
    mocks.particellaItems.mockResolvedValueOnce(response([
      parcelItem("par-3", { candidates: [candidate("parcel-third")] }),
      parcelItem("par-2", { candidates: [candidate("parcel-other")] }),
      parcelItem("par-4", { candidates: [] }),
    ], 26, 2));
    fireEvent.click(within(wizard()).getByRole("button", { name: "Successiva" }));
    await screen.findByText("Utenza par-3");
    fireEvent.click(batchButton());
    await waitFor(() => expect(mocks.applyParticella).toHaveBeenCalledExactlyOnceWith("token", [
      { anomalia_id: "par-3", particella_id: "parcel-third", note_operatore: "Collegamento particella batch da console anomalie" },
      { anomalia_id: "par-2", particella_id: "parcel-other", note_operatore: "Collegamento particella batch da console anomalie" },
    ]));
    await waitFor(() => expect(batchButton()).toBeEnabled());
    mocks.particellaItems.mockResolvedValueOnce(response([parcelItem()], 26));
    fireEvent.click(within(wizard()).getByRole("button", { name: "Precedente" }));
    await screen.findByText("Utenza par-1");
    expect(radio("par-1", "parcel-second")).toBeChecked();
  });

  test("stale truthy draft remains in batch even when its candidate disappears, until explicitly cleared", async () => {
    await mountParticella();
    fireEvent.click(radio("par-1", "parcel-second"));
    mocks.particellaItems.mockResolvedValueOnce(response([parcelItem("par-1", { candidates: [] })]));
    fireEvent.change(screen.getByLabelText("Distretto"), { target: { value: "8" } });
    await screen.findByText("Nessuna candidata trovata con i dati correnti. Questa riga resta in triage manuale.");
    expect(within(row()).queryByText("Anteprima prima / dopo")).not.toBeInTheDocument();
    expect(batchButton()).toHaveTextContent("Applica batch (1)");
    selectTop();
    fireEvent.click(batchButton());
    await waitFor(() => expect(mocks.applyParticella).toHaveBeenCalledExactlyOnceWith("token", [{
      anomalia_id: "par-1", particella_id: "parcel-second", note_operatore: "Collegamento particella batch da console anomalie",
    }]));
    await waitFor(() => expect(batchButton()).toBeEnabled());
    clearSelection();
    expect(batchButton()).toBeDisabled();
  });

  test("wizard pagination leaves overview URL page unchanged and year/district/reset restore page one", async () => {
    mocks.particellaItems.mockResolvedValue(response([parcelItem()], 51));
    await mountParticella();
    const urls = mocks.router.replace.mock.calls.length;
    fireEvent.click(within(wizard()).getByRole("button", { name: "Successiva" }));
    await waitFor(() => expect(mocks.particellaItems).toHaveBeenLastCalledWith("token", {
      status: "aperta", anno: undefined, distretto: undefined, page: 2, pageSize: 25,
    }));
    expect(mocks.router.replace).toHaveBeenCalledTimes(urls);
    fireEvent.change(screen.getByLabelText("Anno"), { target: { value: "2025" } });
    await waitFor(() => expect(mocks.particellaItems).toHaveBeenLastCalledWith("token", {
      status: "aperta", anno: 2025, distretto: undefined, page: 1, pageSize: 25,
    }));
    fireEvent.click(within(wizard()).getByRole("button", { name: "Successiva" }));
    fireEvent.change(screen.getByLabelText("Distretto"), { target: { value: "07" } });
    await waitFor(() => expect(mocks.particellaItems).toHaveBeenLastCalledWith("token", {
      status: "aperta", anno: 2025, distretto: "07", page: 1, pageSize: 25,
    }));
    await waitFor(() => expect(screen.getByRole("button", { name: "Reset contesto" })).toBeEnabled());
    fireEvent.click(screen.getByRole("button", { name: "Reset contesto" }));
    await waitFor(() => expect(mocks.particellaItems).toHaveBeenLastCalledWith("token", {
      status: "aperta", anno: undefined, distretto: undefined, page: 1, pageSize: 25,
    }));
  });

  test("empty later page with positive total reloads page one without replacing old candidates before recovery", async () => {
    mocks.particellaItems.mockResolvedValueOnce(response([parcelItem()], 26));
    await mountParticella();
    const recovery = deferred<CatAnomaliaParticellaWizardListResponse>();
    mocks.particellaItems.mockResolvedValueOnce(response([], 1, 2)).mockReturnValueOnce(recovery.promise);
    fireEvent.click(within(wizard()).getByRole("button", { name: "Successiva" }));
    await waitFor(() => expect(mocks.particellaItems).toHaveBeenCalledTimes(3));
    expect(mocks.particellaItems).toHaveBeenNthCalledWith(2, "token", expect.objectContaining({ page: 2 }));
    expect(mocks.particellaItems).toHaveBeenNthCalledWith(3, "token", expect.objectContaining({ page: 1 }));
    expect(radio()).toBeChecked();
    await act(async () => { recovery.resolve(response([parcelItem("par-2")], 1)); });
    expect(screen.queryByText("Utenza par-1")).not.toBeInTheDocument();
    expect(within(wizard()).getByRole("button", { name: "Successiva" })).toBeDisabled();
  });

  test.each([0, 4])("an empty first page total%s does not retry and has no candidate actions", async (total) => {
    mocks.particellaItems.mockResolvedValue(response([], total));
    render(<CatastoAnomaliePage />);
    await screen.findByText("Nessuna anomalia particella aperta");
    expect(mocks.particellaItems).toHaveBeenCalledTimes(1);
    expect(batchButton()).toBeDisabled();
  });

  test.each([
    ["  validated  ", "validated"],
    ["   ", "Collegamento particella da console anomalie"],
  ])("single apply trims note %j, sends selected ID and reports backend counters without inferring full success", async (input, expected) => {
    mocks.applyParticella.mockResolvedValue({ applied_count: 0, updated_utenze: 0, closed_anomalies: 2 });
    await mountParticella();
    fireEvent.click(radio("par-1", "parcel-second"));
    fireEvent.change(note(), { target: { value: input } });
    fireEvent.click(singleButton());
    await screen.findByText("Collegamento applicato: 0 utenza aggiornata, 2 anomalie particella chiuse.");
    expect(mocks.applyParticella).toHaveBeenCalledExactlyOnceWith("token", [{
      anomalia_id: "par-1", particella_id: "parcel-second", note_operatore: expected,
    }]);
    await waitFor(() => expect(singleButton()).toBeEnabled());
    expect(mocks.particellaItems).toHaveBeenCalledTimes(2);
    expect(mocks.list).toHaveBeenCalledTimes(2);
    expect(mocks.summary).toHaveBeenCalledTimes(2);
    expect(mocks.cfItems).not.toHaveBeenCalled();
    expect(mocks.comuneItems).not.toHaveBeenCalled();
  });

  test.each([
    ["  batch checked  ", "batch checked"],
    ["   ", "Collegamento particella batch da console anomalie"],
  ])("batch apply trims note %j and trusts partial backend counts", async (input, expected) => {
    mocks.particellaItems.mockResolvedValue(response([parcelItem(), parcelItem("par-2")]));
    mocks.applyParticella.mockResolvedValue({ applied_count: 1, updated_utenze: 1, closed_anomalies: 0 });
    await mountParticella();
    fireEvent.change(note(), { target: { value: input } });
    fireEvent.click(batchButton());
    await screen.findByText("Batch applicato: 1 utenze aggiornate, 0 anomalie particella chiuse.");
    expect(mocks.applyParticella).toHaveBeenCalledExactlyOnceWith("token", [
      { anomalia_id: "par-1", particella_id: "parcel-first", note_operatore: expected },
      { anomalia_id: "par-2", particella_id: "parcel-first", note_operatore: expected },
    ]);
    await waitFor(() => expect(batchButton()).toBeEnabled());
    expect(radio()).toBeChecked();
    expect(radio("par-2")).toBeChecked();
  });

  test.each(["single", "batch"])("%s pending apply snapshots its payload, disables intended controls and remains busy through refresh", async (mode) => {
    mocks.particellaItems.mockResolvedValue(response([parcelItem(), parcelItem("par-2")]));
    await mountParticella();
    const apply = deferred<CatAnomaliaParticellaWizardApplyResponse>();
    const load = deferred<CatAnomaliaParticellaWizardListResponse>();
    mocks.applyParticella.mockReturnValueOnce(apply.promise);
    mocks.particellaItems.mockReturnValueOnce(load.promise);
    fireEvent.click(mode === "single" ? singleButton() : batchButton());
    expect(singleButton()).toBeDisabled();
    if (mode === "batch") {
      expect(singleButton("par-2")).toBeDisabled();
      expect(batchButton()).toBeDisabled();
    } else {
      expect(singleButton("par-2")).toBeEnabled();
      expect(batchButton()).toBeEnabled();
    }
    expect(within(wizard()).getByRole("button", { name: "Pulisci selezioni" })).toBeEnabled();
    expect(radio("par-1", "parcel-second")).toBeEnabled();
    expect(mocks.particellaItems).toHaveBeenCalledTimes(1);
    fireEvent.click(radio("par-1", "parcel-second"));
    fireEvent.change(note(), { target: { value: "changed while pending" } });
    expect(mocks.applyParticella.mock.calls[0][1][0]).toEqual({
      anomalia_id: "par-1", particella_id: "parcel-first", note_operatore: "Collegamento particella batch da console anomalie",
    });
    await act(async () => { apply.resolve({ applied_count: 1, updated_utenze: 2, closed_anomalies: 3 }); });
    expect(within(wizard()).getByText(/applicato: 2 utenz/)).toBeInTheDocument();
    expect(within(wizard()).getByText("Sincronizzazione...")).toBeInTheDocument();
    expect(singleButton()).toBeDisabled();
    expect(batchButton()).toBeDisabled();
    await act(async () => { load.resolve(response([parcelItem(), parcelItem("par-2")])); });
    expect(singleButton()).toBeEnabled();
    expect(batchButton()).toBeEnabled();
    expect(radio("par-1", "parcel-second")).toBeChecked();
  });

  test.each([
    ["single", new Error("individual rejected"), "individual rejected"],
    ["single", "opaque", "Errore collegamento particella"],
    ["batch", new Error("batch rejected"), "batch rejected"],
    ["batch", "opaque", "Errore batch collegamento particelle"],
  ])("%s rejection preserves drafts and does not reload (%j)", async (mode, failure, expected) => {
    await mountParticella();
    mocks.applyParticella.mockRejectedValueOnce(failure);
    fireEvent.click(mode === "single" ? singleButton() : batchButton());
    await screen.findByText(expected);
    expect(singleButton()).toBeEnabled();
    expect(batchButton()).toBeEnabled();
    expect(radio()).toBeChecked();
    expect(mocks.particellaItems).toHaveBeenCalledTimes(1);
    expect(mocks.list).toHaveBeenCalledTimes(1);
    expect(within(wizard()).queryByText(/applicato:/)).not.toBeInTheDocument();
  });

  test("a second attempt clears prior status/error immediately and retains the new success across a failed wizard refresh", async () => {
    await mountParticella();
    mocks.applyParticella.mockRejectedValueOnce(new Error("first rejection"));
    fireEvent.click(singleButton());
    await screen.findByText("first rejection");
    const apply = deferred<CatAnomaliaParticellaWizardApplyResponse>();
    mocks.applyParticella.mockReturnValueOnce(apply.promise);
    mocks.particellaItems.mockRejectedValueOnce(new Error("refresh unavailable"));
    fireEvent.click(singleButton());
    expect(screen.queryByText("first rejection")).not.toBeInTheDocument();
    await act(async () => { apply.resolve({ applied_count: 1, updated_utenze: 2, closed_anomalies: 3 }); });
    expect(screen.getByText("refresh unavailable")).toBeInTheDocument();
    expect(screen.getByText("Collegamento applicato: 2 utenza aggiornata, 3 anomalie particella chiuse.")).toBeInTheDocument();
    expect(singleButton()).toBeEnabled();
    const retry = deferred<CatAnomaliaParticellaWizardApplyResponse>();
    mocks.applyParticella.mockReturnValueOnce(retry.promise);
    fireEvent.click(batchButton());
    expect(screen.queryByText("refresh unavailable")).not.toBeInTheDocument();
    expect(within(wizard()).queryByText(/applicato:/)).not.toBeInTheDocument();
    await act(async () => { retry.reject(new Error("last rejection")); });
    expect(screen.getByText("last rejection")).toBeInTheDocument();
  });

  test("overview refresh failure coexists with successful batch status and a completed wizard reload", async () => {
    await mountParticella();
    mocks.list.mockRejectedValueOnce(new Error("overview unavailable"));
    fireEvent.click(batchButton());
    await screen.findByText("Batch applicato: 2 utenze aggiornate, 3 anomalie particella chiuse.");
    await screen.findByText("overview unavailable");
    await waitFor(() => expect(batchButton()).toBeEnabled());
    expect(mocks.particellaItems).toHaveBeenCalledTimes(2);
    expect(radio()).toBeChecked();
  });

  test.each([
    [new Error("load unavailable"), "load unavailable"],
    ["opaque", "Errore caricamento workspace particelle"],
  ])("load error keeps old candidates until a successful context reload clears the error (%j)", async (failure, expected) => {
    await mountParticella();
    mocks.particellaItems.mockRejectedValueOnce(failure);
    fireEvent.change(screen.getByLabelText("Anno"), { target: { value: "2025" } });
    await screen.findByText(expected);
    expect(radio()).toBeChecked();
    expect(batchButton()).toBeEnabled();
    fireEvent.change(screen.getByLabelText("Distretto"), { target: { value: "8" } });
    await waitFor(() => expect(screen.queryByText(expected)).not.toBeInTheDocument());
    expect(radio()).toBeChecked();
  });

  test.each(["single", "batch"])("missing token at %s action is a no-op without mutation or refresh", async (mode) => {
    await mountParticella();
    mocks.token.mockReturnValue(null);
    fireEvent.click(mode === "single" ? singleButton() : batchButton());
    expect(mocks.applyParticella).not.toHaveBeenCalled();
    expect(mocks.particellaItems).toHaveBeenCalledTimes(1);
    expect(singleButton()).toBeEnabled();
    expect(batchButton()).toBeEnabled();
  });

  test("missing token during initial mount leaves the workspace idle without calls", async () => {
    mocks.token.mockReturnValue(null);
    await act(async () => { render(<CatastoAnomaliePage />); });
    expect(screen.getByText("Nessuna anomalia particella aperta")).toBeInTheDocument();
    expect(mocks.particellaItems).not.toHaveBeenCalled();
    expect(mocks.list).not.toHaveBeenCalled();
    expect(mocks.summary).not.toHaveBeenCalled();
    expect(batchButton()).toBeDisabled();
  });

  test("single then batch overlap shares one busy ID and the earlier completion releases it while batch is pending", async () => {
    await mountParticella();
    const single = deferred<CatAnomaliaParticellaWizardApplyResponse>();
    const batch = deferred<CatAnomaliaParticellaWizardApplyResponse>();
    mocks.applyParticella.mockReturnValueOnce(single.promise).mockReturnValueOnce(batch.promise);
    fireEvent.click(singleButton());
    expect(singleButton()).toBeDisabled();
    expect(batchButton()).toBeEnabled();
    fireEvent.click(batchButton());
    expect(batchButton()).toBeDisabled();
    expect(singleButton()).toBeDisabled();
    expect(mocks.applyParticella).toHaveBeenCalledTimes(2);
    await act(async () => { single.resolve({ applied_count: 1, updated_utenze: 1, closed_anomalies: 1 }); });
    expect(screen.getByText("Collegamento applicato: 1 utenza aggiornata, 1 anomalie particella chiuse.")).toBeInTheDocument();
    expect(singleButton()).toBeEnabled();
    expect(batchButton()).toBeEnabled();
    expect(mocks.particellaItems).toHaveBeenCalledTimes(2);
    await act(async () => { batch.resolve({ applied_count: 1, updated_utenze: 2, closed_anomalies: 3 }); });
    expect(screen.getByText("Batch applicato: 2 utenze aggiornate, 3 anomalie particella chiuse.")).toBeInTheDocument();
    expect(screen.queryByText("Collegamento applicato: 1 utenza aggiornata, 1 anomalie particella chiuse.")).not.toBeInTheDocument();
    expect(mocks.particellaItems).toHaveBeenCalledTimes(3);
  });

  test("pending mutation retains old year and Particella loaders after context change and tab leave", async () => {
    await mountParticella();
    const apply = deferred<CatAnomaliaParticellaWizardApplyResponse>();
    mocks.applyParticella.mockReturnValueOnce(apply.promise);
    fireEvent.click(singleButton());
    mocks.particellaItems.mockResolvedValueOnce(response([parcelItem("par-context")]));
    fireEvent.change(screen.getByLabelText("Anno"), { target: { value: "2025" } });
    await screen.findByText("Utenza par-context");
    expect(mocks.particellaItems).toHaveBeenNthCalledWith(2, "token", expect.objectContaining({ anno: 2025 }));
    selectTab(/Triage manuale/);
    expect(screen.queryByText("Wizard particella assente")).not.toBeInTheDocument();
    mocks.particellaItems.mockResolvedValueOnce(response([parcelItem("par-late")]));
    await act(async () => { apply.resolve({ applied_count: 1, updated_utenze: 2, closed_anomalies: 3 }); });
    expect(mocks.particellaItems).toHaveBeenNthCalledWith(3, "token", {
      status: "aperta", anno: undefined, distretto: undefined, page: 1, pageSize: 25,
    });
    expect(mocks.list).toHaveBeenLastCalledWith("token", expect.objectContaining({ anno: undefined }));
    expect(screen.getByLabelText("Anno")).toHaveValue("2025");
    const reopening = deferred<CatAnomaliaParticellaWizardListResponse>();
    mocks.particellaItems.mockReturnValueOnce(reopening.promise);
    selectTab(/Particelle/);
    expect(screen.getByText("Utenza par-late")).toBeInTheDocument();
    expect(within(wizard()).queryByText(/applicato:/)).not.toBeInTheDocument();
    expect(mocks.particellaItems).toHaveBeenNthCalledWith(4, "token", expect.objectContaining({ anno: 2025 }));
    await act(async () => { reopening.resolve(response([parcelItem()])); });
    expect(screen.getByText("Utenza par-1")).toBeInTheDocument();
  });

  test("out-of-order context responses use completion order rather than latest-request protection", async () => {
    await mountParticella();
    const older = deferred<CatAnomaliaParticellaWizardListResponse>();
    const newer = deferred<CatAnomaliaParticellaWizardListResponse>();
    mocks.particellaItems.mockReturnValueOnce(older.promise).mockReturnValueOnce(newer.promise);
    fireEvent.change(screen.getByLabelText("Anno"), { target: { value: "2025" } });
    fireEvent.change(screen.getByLabelText("Anno"), { target: { value: "2024" } });
    expect(mocks.particellaItems).toHaveBeenNthCalledWith(2, "token", expect.objectContaining({ anno: 2025 }));
    expect(mocks.particellaItems).toHaveBeenNthCalledWith(3, "token", expect.objectContaining({ anno: 2024 }));
    await act(async () => { newer.resolve(response([parcelItem("par-new")])); });
    expect(screen.getByText("Utenza par-new")).toBeInTheDocument();
    expect(within(wizard()).queryByText("Sincronizzazione...")).not.toBeInTheDocument();
    await act(async () => { older.resolve(response([parcelItem("par-old")])); });
    expect(screen.queryByText("Utenza par-new")).not.toBeInTheDocument();
    expect(screen.getByText("Utenza par-old")).toBeInTheDocument();
    expect(screen.getByLabelText("Anno")).toHaveValue("2024");
  });

  test("leaving and reopening tab resets status/page but retains note, local filter and candidate draft", async () => {
    await mountParticella();
    fireEvent.click(radio("par-1", "parcel-second"));
    fireEvent.change(note(), { target: { value: "persistent note" } });
    fireEvent.click(singleButton());
    await screen.findByText("Collegamento applicato: 2 utenza aggiornata, 3 anomalie particella chiuse.");
    await waitFor(() => expect(singleButton()).toBeEnabled());
    fireEvent.change(within(wizard()).getByLabelText("Vista"), { target: { value: "without_candidates" } });
    selectTab(/Triage manuale/);
    expect(screen.queryByText("Wizard particella assente")).not.toBeInTheDocument();
    selectTab(/Particelle/);
    await waitFor(() => expect(mocks.particellaItems).toHaveBeenCalledTimes(3));
    await waitFor(() => expect(within(wizard()).queryByText("Sincronizzazione...")).not.toBeInTheDocument());
    expect(note()).toHaveValue("persistent note");
    expect(within(wizard()).getByLabelText("Vista")).toHaveValue("without_candidates");
    expect(within(wizard()).queryByText(/applicato:/)).not.toBeInTheDocument();
    fireEvent.change(within(wizard()).getByLabelText("Vista"), { target: { value: "all" } });
    expect(radio("par-1", "parcel-second")).toBeChecked();
    expect(mocks.particellaItems).toHaveBeenLastCalledWith("token", expect.objectContaining({ page: 1 }));
  });
});
