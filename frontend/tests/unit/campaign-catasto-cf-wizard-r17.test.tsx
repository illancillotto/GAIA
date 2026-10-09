import type { ReactNode } from "react";
import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import CatastoAnomaliePage from "@/app/catasto/anomalie/page";
import type { CatAnomaliaCfWizardItem, CatAnomaliaCfWizardListResponse } from "@/types/catasto";

const mocks = vi.hoisted(() => ({
  params: new URLSearchParams("tab=cf"),
  router: { replace: vi.fn() },
  token: vi.fn(),
  list: vi.fn(),
  summary: vi.fn(),
  cfItems: vi.fn(),
  applyCf: vi.fn(),
  comuneItems: vi.fn(),
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
  catastoGetCfWizardItems: mocks.cfItems,
  catastoApplyCfWizard: mocks.applyCf,
  catastoGetComuneWizardItems: mocks.comuneItems,
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
vi.mock("@/components/elaborazioni/workspace-modal", () => ({
  ElaborazioneWorkspaceModal: () => null,
}));
vi.mock("@/components/catasto/workspace-modal", () => ({
  CatastoWorkspaceModal: () => null,
}));

function cfItem(id = "cf-1", overrides: Partial<CatAnomaliaCfWizardItem> = {}): CatAnomaliaCfWizardItem {
  return {
    anomalia_id: id,
    utenza_id: "utenza-1",
    particella_id: "parcel-1",
    anno_campagna: 2026,
    tipo: "VAL-02-cf_invalido",
    severita: "error",
    descrizione: "Codice fiscale da correggere",
    status: "aperta",
    denominazione: `Utenza ${id}`,
    codice_fiscale: "OLD-CF",
    codice_fiscale_raw: "old raw",
    num_distretto: 7,
    nome_comune: "Comune originale",
    sezione_catastale: "A",
    foglio: "12",
    particella: "34",
    subalterno: "2",
    error_code: "INVALID_LENGTH",
    suggested_codice_fiscale: "RSSMRA80A01H501U",
    created_at: "2026-10-09T09:00:00Z",
    ...overrides,
  };
}

function cfResponse(items: CatAnomaliaCfWizardItem[], total = items.length, page = 1): CatAnomaliaCfWizardListResponse {
  return { items, total, page, page_size: 25 };
}

function deferred<Value>() {
  let resolve!: (value: Value) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<Value>((fulfill, fail) => { resolve = fulfill; reject = fail; });
  return { promise, resolve, reject };
}

function wizard() {
  return screen.getByText("Wizard codice fiscale").closest("article")!;
}

function correction(denominazione = "Utenza cf-1") {
  return within(screen.getByText(denominazione).closest("div.rounded-2xl")!).getByLabelText("Correzione CF / P.IVA");
}

function applyButton(denominazione = "Utenza cf-1") {
  return within(screen.getByText(denominazione).closest("div.rounded-2xl")!).getByRole("button", { name: /Applica correzione|Applicazione\.\.\./ });
}

async function mountCf() {
  const view = render(<CatastoAnomaliePage />);
  await screen.findByText("Utenza cf-1");
  await waitFor(() => expect(within(wizard()).queryByText("Sincronizzazione...")).not.toBeInTheDocument());
  await waitFor(() => expect(screen.getByRole("button", { name: "Reset contesto" })).toBeEnabled());
  return view;
}

function selectTab(label: string) {
  fireEvent.click(within(screen.getByRole("navigation", { name: "Code anomalie" })).getByRole("button", { name: new RegExp(label) }));
}

beforeEach(() => {
  vi.resetAllMocks();
  mocks.params = new URLSearchParams("tab=cf");
  mocks.token.mockReturnValue("token");
  mocks.list.mockResolvedValue({ items: [], total: 0, page: 1, page_size: 50 });
  mocks.summary.mockResolvedValue({ buckets: [], total: 0 });
  mocks.cfItems.mockResolvedValue(cfResponse([cfItem()]));
  mocks.applyCf.mockResolvedValue({ applied_count: 1, updated_utenze: 2, closed_anomalies: 3 });
  mocks.comuneItems.mockResolvedValue({ items: [], total: 0 });
  mocks.particellaItems.mockResolvedValue({ items: [], total: 0 });
  mocks.adeSummary.mockResolvedValue({});
  mocks.adeCandidates.mockResolvedValue({ items: [], total: 0 });
  mocks.batches.mockResolvedValue([]);
  mocks.users.mockResolvedValue({ items: [] });
  mocks.categories.mockResolvedValue([]);
  mocks.severities.mockResolvedValue([]);
});

afterEach(cleanup);

describe("R17 original Catasto CF wizard public transitions", () => {
  test("loads the open CF queue with a literal request and leaves the other wizards idle", async () => {
    await mountCf();
    expect(mocks.cfItems).toHaveBeenCalledExactlyOnceWith("token", {
      status: "aperta", anno: undefined, distretto: undefined, page: 1, pageSize: 25,
    });
    expect(within(wizard()).getByText("1 righe su 1")).toBeInTheDocument();
    expect(correction()).toHaveValue("RSSMRA80A01H501U");
    expect(mocks.comuneItems).not.toHaveBeenCalled();
    expect(mocks.particellaItems).not.toHaveBeenCalled();
    expect(mocks.page).toHaveBeenCalledWith(expect.objectContaining({
      requiredModule: "catasto", requiredRoles: ["admin", "super_admin"],
    }));
  });

  test.each(["", "workspace=cf", "tab=cf&workspace=comune", "tab=unknown&workspace=cf"])(
    "activates CF from public URL context %s", async (query) => {
      mocks.params = new URLSearchParams(query);
      await mountCf();
      expect(mocks.cfItems).toHaveBeenCalledTimes(1);
      expect(within(screen.getByRole("navigation", { name: "Code anomalie" })).getByRole("button", { name: /CF \/ P.IVA/ })).toHaveAttribute("aria-pressed", "true");
    },
  );

  test("an explicit manual tab keeps CF idle until its own navigation button is selected", async () => {
    mocks.params = new URLSearchParams("tab=manuale&workspace=cf");
    render(<CatastoAnomaliePage />);
    await waitFor(() => expect(screen.getByRole("button", { name: "Reset contesto" })).toBeEnabled());
    expect(mocks.cfItems).not.toHaveBeenCalled();
    expect(screen.queryByText("Wizard codice fiscale")).not.toBeInTheDocument();
    selectTab("CF / P.IVA");
    await screen.findByText("Utenza cf-1");
    expect(mocks.cfItems).toHaveBeenCalledExactlyOnceWith("token", {
      status: "aperta", anno: undefined, distretto: undefined, page: 1, pageSize: 25,
    });
  });

  test("only year and district affect CF requests and CF page starts at one independently of overview URL page", async () => {
    mocks.params = new URLSearchParams("tab=cf&tipo=VAL-03-cf_mancante&severita=warning&status=chiusa&anno=2025&distretto=09&page=3");
    mocks.list.mockResolvedValue({ items: [], total: 0, page: 3, page_size: 50 });
    await mountCf();
    expect(mocks.cfItems).toHaveBeenCalledExactlyOnceWith("token", {
      status: "aperta", anno: 2025, distretto: "09", page: 1, pageSize: 25,
    });
    expect(mocks.list).toHaveBeenCalledWith("token", expect.objectContaining({
      tipo: "VAL-03-cf_mancante", severita: "warning", status: "chiusa", page: 3,
    }));
    const url = new URL(mocks.router.replace.mock.calls.at(-1)![0], "http://localhost");
    expect(url.searchParams.get("tab")).toBeNull();
    expect(url.searchParams.get("page")).toBe("3");
  });

  test("shows the initial loading state and then the empty queue without pagination", async () => {
    const load = deferred<CatAnomaliaCfWizardListResponse>();
    mocks.cfItems.mockReturnValue(load.promise);
    render(<CatastoAnomaliePage />);
    expect(within(wizard()).getByText("Sincronizzazione...")).toBeInTheDocument();
    expect(within(wizard()).getByText("Caricamento workspace CF...")).toBeInTheDocument();
    expect(within(wizard()).queryByText("Nessuna anomalia CF aperta")).not.toBeInTheDocument();
    await act(async () => { load.resolve(cfResponse([])); });
    expect(within(wizard()).getByText("Nessuna anomalia CF aperta")).toBeInTheDocument();
    expect(within(wizard()).getByText("0 righe su 0")).toBeInTheDocument();
    expect(within(wizard()).queryByRole("button", { name: "Successiva" })).not.toBeInTheDocument();
  });

  test("initializes drafts by nullish suggestion/current/empty precedence and renders absent metadata", async () => {
    mocks.cfItems.mockResolvedValue(cfResponse([
      cfItem(),
      cfItem("cf-2", { suggested_codice_fiscale: null, codice_fiscale: "CURRENT-2" }),
      cfItem("cf-3", { suggested_codice_fiscale: "", codice_fiscale: "IGNORED-3" }),
      cfItem("cf-4", {
        denominazione: null, suggested_codice_fiscale: null, codice_fiscale: null,
        codice_fiscale_raw: null, error_code: null, num_distretto: 0, nome_comune: null,
        sezione_catastale: null, foglio: null, particella: null, subalterno: null, anno_campagna: null,
      }),
    ]));
    await mountCf();
    expect(correction()).toHaveValue("RSSMRA80A01H501U");
    expect(correction("Utenza cf-2")).toHaveValue("CURRENT-2");
    expect(correction("Utenza cf-3")).toHaveValue("");
    expect(correction("Utenza senza denominazione")).toHaveValue("");
    const missing = within(screen.getByText("Utenza senza denominazione").closest("div.rounded-2xl")!);
    expect(missing.getByText("Dato mancante")).toBeInTheDocument();
    expect(missing.getByText("0")).toBeInTheDocument();
    expect(missing.getAllByText("—")).toHaveLength(5);
    expect(missing.queryByRole("button", { name: /Usa suggerito/ })).not.toBeInTheDocument();
    expect(within(wizard()).getAllByText("A / 12 / 34 / 2")).toHaveLength(3);
  });

  test("uppercases typed edits, restores the raw suggestion on selection and normalizes the literal apply payload", async () => {
    mocks.cfItems.mockResolvedValue(cfResponse([cfItem("cf-1", { suggested_codice_fiscale: "  hint-low  " })]));
    await mountCf();
    expect(correction()).toHaveValue("  hint-low  ");
    fireEvent.change(correction(), { target: { value: "  typed-low  " } });
    expect(correction()).toHaveValue("  TYPED-LOW  ");
    fireEvent.click(within(wizard()).getByRole("button", { name: "Usa suggerito: hint-low" }));
    expect(correction()).toHaveValue("  hint-low  ");
    fireEvent.click(applyButton());
    await waitFor(() => expect(mocks.applyCf).toHaveBeenCalledExactlyOnceWith("token", [{
      anomalia_id: "cf-1", codice_fiscale: "HINT-LOW",
      note_operatore: "Correzione da console anomalie per VAL-02-cf_invalido",
    }]));
    expect(await screen.findByText("Correzione applicata: 2 utenza aggiornata, 3 anomalie CF chiuse.")).toBeInTheDocument();
    await waitFor(() => expect(applyButton()).toBeEnabled());
  });

  test("preserves nonempty drafts, refills empty drafts and reads edits made while a reload is pending", async () => {
    mocks.cfItems.mockResolvedValue(cfResponse([
      cfItem(), cfItem("cf-2", { suggested_codice_fiscale: "SECOND" }),
    ]));
    await mountCf();
    fireEvent.change(correction(), { target: { value: "first edit" } });
    fireEvent.change(correction("Utenza cf-2"), { target: { value: "" } });
    const reload = deferred<CatAnomaliaCfWizardListResponse>();
    mocks.cfItems.mockReturnValueOnce(reload.promise);
    fireEvent.change(screen.getByLabelText("Anno"), { target: { value: "2025" } });
    expect(within(wizard()).getByText("Sincronizzazione...")).toBeInTheDocument();
    expect(correction()).toHaveValue("FIRST EDIT");
    fireEvent.change(correction(), { target: { value: "pending edit" } });
    await act(async () => { reload.resolve(cfResponse([
      cfItem("cf-1", { suggested_codice_fiscale: "NEW-FIRST" }),
      cfItem("cf-2", { suggested_codice_fiscale: "NEW-SECOND" }),
    ])); });
    expect(correction()).toHaveValue("PENDING EDIT");
    expect(correction("Utenza cf-2")).toHaveValue("NEW-SECOND");
  });

  test("retains a draft while its anomaly is absent on another page and when it returns", async () => {
    mocks.cfItems.mockResolvedValueOnce(cfResponse([cfItem()], 26));
    await mountCf();
    fireEvent.change(correction(), { target: { value: "retained" } });
    mocks.cfItems.mockResolvedValueOnce(cfResponse([cfItem("cf-2")], 26, 2));
    fireEvent.click(within(wizard()).getByRole("button", { name: "Successiva" }));
    await screen.findByText("Utenza cf-2");
    expect(screen.queryByText("Utenza cf-1")).not.toBeInTheDocument();
    mocks.cfItems.mockResolvedValueOnce(cfResponse([cfItem("cf-1", { suggested_codice_fiscale: "REPLACEMENT" })], 26));
    fireEvent.click(within(wizard()).getByRole("button", { name: "Precedente" }));
    await screen.findByText("Utenza cf-1");
    expect(correction()).toHaveValue("RETAINED");
  });

  test("paginates CF independently, resets for context changes and does not add CF page to the URL", async () => {
    mocks.cfItems.mockResolvedValue(cfResponse([cfItem()], 51));
    await mountCf();
    expect(within(wizard()).getByText("Pagina 1 di 3")).toBeInTheDocument();
    expect(within(wizard()).getByRole("button", { name: "Precedente" })).toBeDisabled();
    const urlCalls = mocks.router.replace.mock.calls.length;
    fireEvent.click(within(wizard()).getByRole("button", { name: "Successiva" }));
    await waitFor(() => expect(mocks.cfItems).toHaveBeenLastCalledWith("token", {
      status: "aperta", anno: undefined, distretto: undefined, page: 2, pageSize: 25,
    }));
    expect(mocks.router.replace).toHaveBeenCalledTimes(urlCalls);
    fireEvent.change(screen.getByLabelText("Anno"), { target: { value: "2025" } });
    await waitFor(() => expect(mocks.cfItems).toHaveBeenLastCalledWith("token", {
      status: "aperta", anno: 2025, distretto: undefined, page: 1, pageSize: 25,
    }));
    fireEvent.click(within(wizard()).getByRole("button", { name: "Successiva" }));
    await waitFor(() => expect(mocks.cfItems).toHaveBeenLastCalledWith("token", expect.objectContaining({ page: 2 })));
    fireEvent.change(screen.getByLabelText("Distretto"), { target: { value: "07" } });
    await waitFor(() => expect(mocks.cfItems).toHaveBeenLastCalledWith("token", {
      status: "aperta", anno: 2025, distretto: "07", page: 1, pageSize: 25,
    }));
    await waitFor(() => expect(screen.getByRole("button", { name: "Reset contesto" })).toBeEnabled());
    fireEvent.click(screen.getByRole("button", { name: "Reset contesto" }));
    await waitFor(() => expect(mocks.cfItems).toHaveBeenLastCalledWith("token", {
      status: "aperta", anno: undefined, distretto: undefined, page: 1, pageSize: 25,
    }));
  });

  test("recovers an empty later page from page one before replacing previously loaded rows", async () => {
    mocks.cfItems.mockResolvedValueOnce(cfResponse([cfItem()], 26));
    await mountCf();
    const recovery = deferred<CatAnomaliaCfWizardListResponse>();
    mocks.cfItems.mockResolvedValueOnce(cfResponse([], 1, 2)).mockReturnValueOnce(recovery.promise);
    fireEvent.click(within(wizard()).getByRole("button", { name: "Successiva" }));
    await waitFor(() => expect(mocks.cfItems).toHaveBeenCalledTimes(3));
    expect(mocks.cfItems).toHaveBeenNthCalledWith(2, "token", {
      status: "aperta", anno: undefined, distretto: undefined, page: 2, pageSize: 25,
    });
    expect(mocks.cfItems).toHaveBeenNthCalledWith(3, "token", {
      status: "aperta", anno: undefined, distretto: undefined, page: 1, pageSize: 25,
    });
    expect(correction()).toHaveValue("RSSMRA80A01H501U");
    await act(async () => { recovery.resolve(cfResponse([cfItem("cf-2")], 1)); });
    expect(screen.queryByText("Utenza cf-1")).not.toBeInTheDocument();
    expect(within(wizard()).getByText("1 righe su 1")).toBeInTheDocument();
    expect(within(wizard()).getByRole("button", { name: "Successiva" })).toBeDisabled();
  });

  test("does not repeat an empty first-page response even with a positive total", async () => {
    mocks.cfItems.mockResolvedValue(cfResponse([], 5));
    render(<CatastoAnomaliePage />);
    await screen.findByText("Nessuna anomalia CF aperta");
    await waitFor(() => expect(within(wizard()).getByText("0 righe su 5")).toBeInTheDocument());
    expect(mocks.cfItems).toHaveBeenCalledTimes(1);
  });

  test.each([
    [new Error("CF fetch refused"), "CF fetch refused"],
    ["offline", "Errore caricamento workspace CF"],
  ])("shows load failure %j, releases loading and clears it after a successful reload", async (reason, message) => {
    mocks.cfItems.mockRejectedValueOnce(reason);
    render(<CatastoAnomaliePage />);
    expect(await screen.findByText(message)).toBeInTheDocument();
    expect(within(wizard()).queryByText("Caricamento workspace CF...")).not.toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Distretto"), { target: { value: "8" } });
    await screen.findByText("Utenza cf-1");
    expect(screen.queryByText(message)).not.toBeInTheDocument();
    expect(applyButton()).toBeEnabled();
  });

  test("a failed reload preserves previously loaded rows and unsaved drafts", async () => {
    await mountCf();
    fireEvent.change(correction(), { target: { value: "kept" } });
    mocks.cfItems.mockRejectedValueOnce(new Error("Refresh unavailable"));
    fireEvent.change(screen.getByLabelText("Anno"), { target: { value: "2024" } });
    expect(await screen.findByText("Refresh unavailable")).toBeInTheDocument();
    expect(correction()).toHaveValue("KEPT");
    expect(within(wizard()).getByText("1 righe su 1")).toBeInTheDocument();
  });

  test("a missing initial token leaves CF idle and still loads unauthenticated report lookups", async () => {
    mocks.token.mockReturnValue(null);
    render(<CatastoAnomaliePage />);
    await waitFor(() => expect(mocks.categories).toHaveBeenCalledTimes(1));
    expect(mocks.cfItems).not.toHaveBeenCalled();
    expect(mocks.list).not.toHaveBeenCalled();
    expect(mocks.adeSummary).not.toHaveBeenCalled();
    expect(mocks.users).not.toHaveBeenCalled();
    expect(within(wizard()).getByText("Nessuna anomalia CF aperta")).toBeInTheDocument();
    expect(within(wizard()).queryByText("Sincronizzazione...")).not.toBeInTheDocument();
  });

  test.each(["", "   "])("rejects blank draft %j before mutation or refresh", async (draft) => {
    await mountCf();
    fireEvent.change(correction(), { target: { value: draft } });
    fireEvent.click(applyButton());
    expect(within(wizard()).getByText("Inserisci un codice fiscale o una partita IVA valida prima di applicare la correzione.")).toBeInTheDocument();
    expect(mocks.applyCf).not.toHaveBeenCalled();
    expect(mocks.cfItems).toHaveBeenCalledTimes(1);
    expect(mocks.list).toHaveBeenCalledTimes(1);
    expect(applyButton()).toBeEnabled();
  });

  test("a token lost before apply preserves existing validation feedback and performs no mutation", async () => {
    await mountCf();
    fireEvent.change(correction(), { target: { value: "" } });
    fireEvent.click(applyButton());
    mocks.token.mockReturnValue(null);
    fireEvent.change(correction(), { target: { value: "new draft" } });
    fireEvent.click(applyButton());
    expect(mocks.applyCf).not.toHaveBeenCalled();
    expect(correction()).toHaveValue("NEW DRAFT");
    expect(within(wizard()).getByText("Inserisci un codice fiscale o una partita IVA valida prima di applicare la correzione.")).toBeInTheDocument();
    expect(applyButton()).toBeEnabled();
  });

  test("captures the draft before mutation and waits for every parallel refresh before releasing its row", async () => {
    mocks.cfItems.mockResolvedValue(cfResponse([cfItem(), cfItem("cf-2")]));
    await mountCf();
    const apply = deferred<{ applied_count: number; updated_utenze: number; closed_anomalies: number }>();
    const list = deferred<{ items: never[]; total: number }>();
    const summary = deferred<{ buckets: never[]; total: number }>();
    const reload = deferred<CatAnomaliaCfWizardListResponse>();
    mocks.applyCf.mockReturnValueOnce(apply.promise);
    mocks.list.mockReturnValueOnce(list.promise);
    mocks.summary.mockReturnValueOnce(summary.promise);
    mocks.cfItems.mockReturnValueOnce(reload.promise);
    fireEvent.change(correction(), { target: { value: "  captured value  " } });
    fireEvent.click(applyButton());
    expect(mocks.applyCf).toHaveBeenCalledExactlyOnceWith("token", [{
      anomalia_id: "cf-1", codice_fiscale: "CAPTURED VALUE",
      note_operatore: "Correzione da console anomalie per VAL-02-cf_invalido",
    }]);
    expect(applyButton()).toBeDisabled();
    expect(applyButton("Utenza cf-2")).toBeEnabled();
    expect(correction()).toBeEnabled();
    fireEvent.change(correction(), { target: { value: "pending latest" } });
    expect(mocks.list).toHaveBeenCalledTimes(1);
    expect(mocks.cfItems).toHaveBeenCalledTimes(1);
    await act(async () => { apply.resolve({ applied_count: 1, updated_utenze: 4, closed_anomalies: 6 }); });
    expect(within(wizard()).getByText("Correzione applicata: 4 utenza aggiornata, 6 anomalie CF chiuse.")).toBeInTheDocument();
    expect(mocks.list).toHaveBeenCalledTimes(2);
    expect(mocks.summary).toHaveBeenCalledTimes(2);
    expect(mocks.cfItems).toHaveBeenCalledTimes(2);
    expect(mocks.list.mock.invocationCallOrder[1]).toBeLessThan(mocks.cfItems.mock.invocationCallOrder[1]);
    expect(mocks.comuneItems).not.toHaveBeenCalled();
    expect(mocks.particellaItems).not.toHaveBeenCalled();
    expect(mocks.adeSummary).toHaveBeenCalledTimes(1);
    await act(async () => { reload.resolve(cfResponse([cfItem(), cfItem("cf-2")])); });
    expect(correction()).toHaveValue("PENDING LATEST");
    expect(applyButton()).toBeDisabled();
    await act(async () => { list.resolve({ items: [], total: 0 }); });
    expect(applyButton()).toBeDisabled();
    await act(async () => { summary.resolve({ buckets: [], total: 0 }); });
    expect(applyButton()).toBeEnabled();
  });

  test.each([
    [new Error("CF apply refused"), "CF apply refused"],
    [{ reason: "offline" }, "Errore applicazione correzione CF"],
  ])("releases a failed apply %j, preserves its draft and allows a retry", async (reason, message) => {
    await mountCf();
    mocks.applyCf.mockRejectedValueOnce(reason);
    fireEvent.change(correction(), { target: { value: "retry me" } });
    fireEvent.click(applyButton());
    expect(await screen.findByText(message)).toBeInTheDocument();
    expect(correction()).toHaveValue("RETRY ME");
    expect(applyButton()).toBeEnabled();
    expect(mocks.cfItems).toHaveBeenCalledTimes(1);
    expect(mocks.list).toHaveBeenCalledTimes(1);
    fireEvent.click(applyButton());
    expect(await screen.findByText("Correzione applicata: 2 utenza aggiornata, 3 anomalie CF chiuse.")).toBeInTheDocument();
    await waitFor(() => expect(applyButton()).toBeEnabled());
    expect(screen.queryByText(message)).not.toBeInTheDocument();
    expect(mocks.applyCf).toHaveBeenNthCalledWith(2, "token", [{
      anomalia_id: "cf-1", codice_fiscale: "RETRY ME",
      note_operatore: "Correzione da console anomalie per VAL-02-cf_invalido",
    }]);
  });

  test("validation clears a prior success and the next pending apply clears prior feedback", async () => {
    await mountCf();
    fireEvent.click(applyButton());
    await screen.findByText("Correzione applicata: 2 utenza aggiornata, 3 anomalie CF chiuse.");
    await waitFor(() => expect(applyButton()).toBeEnabled());
    fireEvent.change(correction(), { target: { value: "" } });
    fireEvent.click(applyButton());
    expect(screen.queryByText("Correzione applicata: 2 utenza aggiornata, 3 anomalie CF chiuse.")).not.toBeInTheDocument();
    const apply = deferred<{ applied_count: number; updated_utenze: number; closed_anomalies: number }>();
    mocks.applyCf.mockReturnValueOnce(apply.promise);
    fireEvent.change(correction(), { target: { value: "valid" } });
    fireEvent.click(applyButton());
    expect(screen.queryByText("Inserisci un codice fiscale o una partita IVA valida prima di applicare la correzione.")).not.toBeInTheDocument();
    expect(applyButton()).toBeDisabled();
    await act(async () => { apply.resolve({ applied_count: 0, updated_utenze: 0, closed_anomalies: 0 }); });
    expect(within(wizard()).getByText("Correzione applicata: 0 utenza aggiornata, 0 anomalie CF chiuse.")).toBeInTheDocument();
    expect(applyButton()).toBeEnabled();
  });

  test("a CF reload error after successful apply leaves both the success and reload error visible", async () => {
    await mountCf();
    mocks.cfItems.mockRejectedValueOnce(new Error("Post-apply CF reload failed"));
    fireEvent.click(applyButton());
    expect(await screen.findByText("Post-apply CF reload failed")).toBeInTheDocument();
    expect(within(wizard()).getByText("Correzione applicata: 2 utenza aggiornata, 3 anomalie CF chiuse.")).toBeInTheDocument();
    expect(applyButton()).toBeEnabled();
    expect(correction()).toHaveValue("RSSMRA80A01H501U");
  });

  test("an overview reload error is handled separately and does not relabel a successful CF mutation", async () => {
    await mountCf();
    mocks.list.mockRejectedValueOnce(new Error("Post-apply overview failed"));
    fireEvent.click(applyButton());
    expect(await screen.findByText("Post-apply overview failed")).toBeInTheDocument();
    expect(within(wizard()).getByText("Correzione applicata: 2 utenza aggiornata, 3 anomalie CF chiuse.")).toBeInTheDocument();
    expect(within(wizard()).queryByText("Errore applicazione correzione CF")).not.toBeInTheDocument();
    expect(applyButton()).toBeEnabled();
  });

  test("applies a missing-CF row with its own anomaly type and removes it when the refreshed queue is empty", async () => {
    mocks.cfItems.mockResolvedValueOnce(cfResponse([cfItem("cf-1", { tipo: "VAL-03-cf_mancante" })]));
    await mountCf();
    mocks.cfItems.mockResolvedValueOnce(cfResponse([]));
    fireEvent.change(correction(), { target: { value: "  12345678901  " } });
    fireEvent.click(applyButton());
    await screen.findByText("Nessuna anomalia CF aperta");
    expect(mocks.applyCf).toHaveBeenCalledExactlyOnceWith("token", [{
      anomalia_id: "cf-1", codice_fiscale: "12345678901",
      note_operatore: "Correzione da console anomalie per VAL-03-cf_mancante",
    }]);
    expect(screen.queryByText("Utenza cf-1")).not.toBeInTheDocument();
    expect(within(wizard()).getByText("Correzione applicata: 2 utenza aggiornata, 3 anomalie CF chiuse.")).toBeInTheDocument();
  });

  test("a token lost during mutation prevents refresh requests while retaining the mutation result", async () => {
    await mountCf();
    const apply = deferred<{ applied_count: number; updated_utenze: number; closed_anomalies: number }>();
    mocks.applyCf.mockReturnValueOnce(apply.promise);
    fireEvent.click(applyButton());
    mocks.token.mockReturnValue(null);
    await act(async () => { apply.resolve({ applied_count: 1, updated_utenze: 1, closed_anomalies: 1 }); });
    expect(within(wizard()).getByText("Correzione applicata: 1 utenza aggiornata, 1 anomalie CF chiuse.")).toBeInTheDocument();
    expect(mocks.cfItems).toHaveBeenCalledTimes(1);
    expect(mocks.list).toHaveBeenCalledTimes(1);
    expect(applyButton()).toBeEnabled();
  });

  test("original overlapping loads let an older response replace newer rows and clear busy with another request pending", async () => {
    await mountCf();
    const older = deferred<CatAnomaliaCfWizardListResponse>();
    const newer = deferred<CatAnomaliaCfWizardListResponse>();
    mocks.cfItems.mockReturnValueOnce(older.promise).mockReturnValueOnce(newer.promise);
    fireEvent.change(screen.getByLabelText("Anno"), { target: { value: "2025" } });
    fireEvent.change(screen.getByLabelText("Anno"), { target: { value: "2024" } });
    expect(mocks.cfItems).toHaveBeenNthCalledWith(2, "token", {
      status: "aperta", anno: 2025, distretto: undefined, page: 1, pageSize: 25,
    });
    expect(mocks.cfItems).toHaveBeenNthCalledWith(3, "token", {
      status: "aperta", anno: 2024, distretto: undefined, page: 1, pageSize: 25,
    });
    await act(async () => { newer.resolve(cfResponse([cfItem("newer")])); });
    expect(screen.getByText("Utenza newer")).toBeInTheDocument();
    expect(within(wizard()).queryByText("Sincronizzazione...")).not.toBeInTheDocument();
    await act(async () => { older.resolve(cfResponse([cfItem("older")])); });
    expect(screen.getByText("Utenza older")).toBeInTheDocument();
    expect(screen.queryByText("Utenza newer")).not.toBeInTheDocument();
    expect(screen.getByLabelText("Anno")).toHaveValue("2024");
  });

  test("a pending apply refreshes with its captured context after the public year field changes", async () => {
    await mountCf();
    const apply = deferred<{ applied_count: number; updated_utenze: number; closed_anomalies: number }>();
    mocks.applyCf.mockReturnValueOnce(apply.promise);
    fireEvent.click(applyButton());
    fireEvent.change(screen.getByLabelText("Anno"), { target: { value: "2025" } });
    await waitFor(() => expect(mocks.cfItems).toHaveBeenCalledTimes(2));
    expect(mocks.cfItems).toHaveBeenNthCalledWith(2, "token", {
      status: "aperta", anno: 2025, distretto: undefined, page: 1, pageSize: 25,
    });
    await act(async () => { apply.resolve({ applied_count: 1, updated_utenze: 2, closed_anomalies: 3 }); });
    expect(mocks.cfItems).toHaveBeenNthCalledWith(3, "token", {
      status: "aperta", anno: undefined, distretto: undefined, page: 1, pageSize: 25,
    });
    expect(mocks.list).toHaveBeenLastCalledWith("token", expect.objectContaining({ anno: undefined }));
    expect(screen.getByLabelText("Anno")).toHaveValue("2025");
    expect(applyButton()).toBeEnabled();
  });

  test("a pending apply still runs its captured CF refresh after leaving the CF tab", async () => {
    await mountCf();
    const apply = deferred<{ applied_count: number; updated_utenze: number; closed_anomalies: number }>();
    mocks.applyCf.mockReturnValueOnce(apply.promise);
    fireEvent.click(applyButton());
    selectTab("Triage manuale");
    expect(screen.queryByText("Wizard codice fiscale")).not.toBeInTheDocument();
    await act(async () => { apply.resolve({ applied_count: 1, updated_utenze: 2, closed_anomalies: 3 }); });
    expect(mocks.cfItems).toHaveBeenCalledTimes(2);
    selectTab("CF / P.IVA");
    await screen.findByText("Utenza cf-1");
    await waitFor(() => expect(mocks.cfItems).toHaveBeenCalledTimes(3));
    expect(within(wizard()).queryByText("Correzione applicata: 2 utenza aggiornata, 3 anomalie CF chiuse.")).not.toBeInTheDocument();
    expect(applyButton()).toBeEnabled();
  });

  test("distinct rows can apply concurrently and the original scalar busy state is released by either completion", async () => {
    mocks.cfItems.mockResolvedValue(cfResponse([cfItem(), cfItem("cf-2")]));
    await mountCf();
    const first = deferred<{ applied_count: number; updated_utenze: number; closed_anomalies: number }>();
    const second = deferred<{ applied_count: number; updated_utenze: number; closed_anomalies: number }>();
    mocks.applyCf.mockReturnValueOnce(first.promise).mockReturnValueOnce(second.promise);
    fireEvent.click(applyButton());
    expect(applyButton()).toBeDisabled();
    fireEvent.change(correction("Utenza cf-2"), { target: { value: "second value" } });
    fireEvent.click(applyButton("Utenza cf-2"));
    expect(applyButton()).toBeEnabled();
    expect(applyButton("Utenza cf-2")).toBeDisabled();
    expect(mocks.applyCf).toHaveBeenNthCalledWith(2, "token", [{
      anomalia_id: "cf-2", codice_fiscale: "SECOND VALUE",
      note_operatore: "Correzione da console anomalie per VAL-02-cf_invalido",
    }]);
    await act(async () => { first.resolve({ applied_count: 1, updated_utenze: 1, closed_anomalies: 2 }); });
    expect(applyButton("Utenza cf-2")).toBeEnabled();
    expect(within(wizard()).getByText("Correzione applicata: 1 utenza aggiornata, 2 anomalie CF chiuse.")).toBeInTheDocument();
    await act(async () => { second.resolve({ applied_count: 1, updated_utenze: 3, closed_anomalies: 4 }); });
    expect(within(wizard()).getByText("Correzione applicata: 3 utenza aggiornata, 4 anomalie CF chiuse.")).toBeInTheDocument();
    expect(mocks.cfItems).toHaveBeenCalledTimes(3);
  });
});
