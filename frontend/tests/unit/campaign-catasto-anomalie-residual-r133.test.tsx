import type { ReactNode } from "react";
import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import CatastoAnomaliePage from "@/app/catasto/anomalie/page";
import type { ApplicationUser } from "@/types/api";
import type {
  CatAnomalia,
  CatAnomaliaCfWizardItem,
  CatAnomaliaComuneCandidate,
  CatAnomaliaComuneWizardItem,
  CatAnomaliaParticellaWizardItem,
} from "@/types/catasto";

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
}));

vi.mock("next/navigation", () => ({ useRouter: () => mocks.router, useSearchParams: () => mocks.params }));
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
vi.mock("@/lib/api", () => ({ getElaborazioneBatches: mocks.batches, listApplicationUsers: mocks.users }));
vi.mock("@/features/operazioni/api/client", () => ({
  getReportCategories: mocks.categories,
  getReportSeverities: mocks.severities,
  createReport: mocks.createReport,
}));
vi.mock("@/components/catasto/catasto-page", () => ({
  CatastoPage: (props: { children: ReactNode }) => <>{props.children}</>,
}));
vi.mock("@/components/elaborazioni/workspace-modal", () => ({ ElaborazioneWorkspaceModal: () => null }));
vi.mock("@/components/catasto/workspace-modal", () => ({ CatastoWorkspaceModal: () => null }));

function anomaly(id = "a1", overrides: Partial<CatAnomalia> = {}): CatAnomalia {
  return {
    id, tipo: "VAL-99-custom", severita: "error", status: "aperta", descrizione: `Anomalia ${id}`,
    particella_id: "parcel-1", utenza_id: "utenza-1", anno_campagna: 2026, assigned_to: null,
    note_operatore: null, segnalazione_id: null, dati_json: { source: id },
    created_at: "2026-10-08T12:00:00Z", updated_at: "2026-10-08T12:00:00Z", ...overrides,
  };
}

function user(id: number, username: string): ApplicationUser {
  return { id, username, role: "admin", is_active: true, module_catasto: true } as ApplicationUser;
}

function cfItem(overrides: Partial<CatAnomaliaCfWizardItem> = {}): CatAnomaliaCfWizardItem {
  return {
    anomalia_id: "cf-1", utenza_id: null, particella_id: null, anno_campagna: null, tipo: "VAL-02-cf_invalido",
    severita: "error", descrizione: null, status: "aperta", denominazione: "Rossi Mario", codice_fiscale: null,
    codice_fiscale_raw: null, num_distretto: null, nome_comune: null, sezione_catastale: null, foglio: null,
    particella: null, subalterno: null, error_code: null, suggested_codice_fiscale: null,
    created_at: "2026-10-08T12:00:00Z", ...overrides,
  };
}

function comuneCandidate(overrides: Partial<CatAnomaliaComuneCandidate> = {}): CatAnomaliaComuneCandidate {
  return {
    id: "comune-1", nome_comune: "Oristano", nome_comune_legacy: null, codice_catastale: null,
    cod_comune_capacitas: 165, codice_comune_formato_numerico: null, codice_comune_numerico_2017_2025: null,
    sigla_provincia: null, match_score: 88, ...overrides,
  };
}

function comuneItem(overrides: Partial<CatAnomaliaComuneWizardItem> = {}): CatAnomaliaComuneWizardItem {
  return {
    anomalia_id: "comune-anomalia", utenza_id: null, anno_campagna: null, tipo: "VAL-04-comune_invalido",
    severita: "warning", descrizione: null, status: "aperta", denominazione: null, nome_comune: null,
    cod_comune_capacitas: null, source_cod_comune_capacitas: null, num_distretto: null, sezione_catastale: null,
    foglio: null, particella: null, subalterno: null, candidates: [comuneCandidate()],
    created_at: "2026-10-08T12:00:00Z", ...overrides,
  };
}

function particellaItem(overrides: Partial<CatAnomaliaParticellaWizardItem> = {}): CatAnomaliaParticellaWizardItem {
  return {
    anomalia_id: "particella-anomalia", utenza_id: null, anno_campagna: null, tipo: "VAL-05-particella_assente",
    severita: "warning", descrizione: null, status: "aperta", denominazione: null, nome_comune: null,
    sezione_catastale: null, foglio: null, particella: null, subalterno: null, cod_comune_capacitas: null,
    num_distretto: null, candidates: [], created_at: "2026-10-08T12:00:00Z", ...overrides,
  };
}

function setItems(items: CatAnomalia[], total = items.length) {
  mocks.list.mockResolvedValue({ items, total, page: 1, page_size: 50 });
}

async function mountManual() {
  const view = render(<CatastoAnomaliePage />);
  await screen.findByRole("button", { name: "Salva nota" });
  await waitFor(() => expect(screen.getByRole("button", { name: "Reset contesto" })).toBeEnabled());
  return view;
}

function detail() {
  return screen.getByText("Dettaglio anomalia selezionata").closest("article")!;
}

function field(label: string) {
  return within(detail()).getByText(label, { exact: false }).querySelector("span")!;
}

function optionTexts(label: string) {
  return Array.from((screen.getByLabelText(label) as HTMLSelectElement).options).map((option) => option.textContent);
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
  mocks.adeSummary.mockResolvedValue({ total_unmatched: 0, pending: 0, last_checked_at: null, buckets: [] });
  mocks.adeCandidates.mockResolvedValue({ items: [], total: 0 });
  mocks.batches.mockResolvedValue([]);
  mocks.users.mockResolvedValue({ items: [] });
  mocks.categories.mockResolvedValue([{ id: "cat-1", name: "Catasto" }]);
  mocks.severities.mockResolvedValue([{ id: "sev-1", name: "Alta" }]);
  mocks.update.mockResolvedValue({});
});

afterEach(cleanup);

describe("R133 manual register context and URL canonicalization", () => {
  test("hides comune and particella wizard families in the without-wizard view", async () => {
    mocks.params = new URLSearchParams("tab=manuale&manual=without_wizard");
    setItems([
      anomaly("cf", { tipo: "VAL-02-cf_invalido" }),
      anomaly("comune", { tipo: "VAL-04-comune_invalido" }),
      anomaly("particella", { tipo: "VAL-05-particella_assente" }),
      anomaly("manual"),
    ]);
    await mountManual();
    const table = screen.getByRole("table");
    expect(within(table).getByText("Anomalia manual")).toBeInTheDocument();
    expect(within(table).queryByText("Anomalia cf")).not.toBeInTheDocument();
    expect(within(table).queryByText("Anomalia comune")).not.toBeInTheDocument();
    expect(within(table).queryByText("Anomalia particella")).not.toBeInTheDocument();
    expect(screen.getByText("1 righe visibili nella pagina corrente")).toBeInTheDocument();
  });

  test("an empty status context is sent as undefined and dropped from the canonical URL", async () => {
    mocks.params = new URLSearchParams("tab=manuale&status=");
    await mountManual();
    expect(mocks.list).toHaveBeenCalledWith("token", expect.objectContaining({ status: undefined }));
    expect(mocks.summary).toHaveBeenCalledWith("token", expect.objectContaining({ status: undefined }));
    expect(mocks.router.replace).toHaveBeenCalledWith("/catasto/anomalie?tab=manuale");
  });

  test("an already canonical URL is not replaced", async () => {
    mocks.params = new URLSearchParams("status=aperta&tab=manuale");
    await mountManual();
    expect(mocks.router.replace).not.toHaveBeenCalled();
  });

  test("a fully default context replaces the URL with the bare console path", async () => {
    mocks.params = new URLSearchParams("status=");
    render(<CatastoAnomaliePage />);
    await waitFor(() => expect(mocks.router.replace).toHaveBeenCalledWith("/catasto/anomalie"));
    await waitFor(() => expect(screen.getByRole("button", { name: "Reset contesto" })).toBeEnabled());
  });

  test("aggregates summary buckets into queue counts and the manual remainder", async () => {
    mocks.summary.mockResolvedValue({
      total: 20,
      buckets: [
        { tipo: "VAL-02-cf_invalido", label: "CF", severita: "warning", count: 3 },
        { tipo: "VAL-03-cf_mancante", label: "CF", severita: "error", count: 2 },
        { tipo: "VAL-04-comune_invalido", label: "Comune", severita: "info", count: 4 },
        { tipo: "VAL-05-particella_assente", label: "Particella", severita: "warning", count: 1 },
      ],
    });
    await mountManual();
    const nav = screen.getByRole("navigation", { name: "Code anomalie" });
    expect(within(nav).getByRole("button", { name: "CF / P.IVA5" })).toBeInTheDocument();
    expect(within(nav).getByRole("button", { name: "Comuni4" })).toBeInTheDocument();
    expect(within(nav).getByRole("button", { name: "Particelle1" })).toBeInTheDocument();
    expect(within(nav).getByRole("button", { name: "Triage manuale10" })).toBeInTheDocument();
    expect(screen.getByText("Code correggibili").parentElement).toHaveTextContent("10");
    expect(screen.getByText("senza wizard dedicato").parentElement).toHaveTextContent("10");
  });

  test("the overview previous-page control returns to the first backend page", async () => {
    setItems([anomaly()], 120);
    await mountManual();
    fireEvent.click(screen.getByRole("button", { name: "Successiva" }));
    await waitFor(() => expect(mocks.list).toHaveBeenLastCalledWith("token", expect.objectContaining({ page: 2 })));
    await waitFor(() => expect(screen.getByRole("button", { name: "Precedente" })).toBeEnabled());
    fireEvent.click(screen.getByRole("button", { name: "Precedente" }));
    await waitFor(() => expect(mocks.list).toHaveBeenLastCalledWith("token", expect.objectContaining({ page: 1 })));
  });

  test("selection clears when the local view filters every row away", async () => {
    setItems([anomaly("a1", { note_operatore: "lavorata" }), anomaly("a2", { status: "chiusa" })]);
    await mountManual();
    fireEvent.click(within(screen.getByRole("table")).getByText("Anomalia a2"));
    await waitFor(() => expect(within(detail()).getByText("a2")).toBeInTheDocument());
    fireEvent.change(screen.getByLabelText("Vista manuale"), { target: { value: "unworked" } });
    expect(await screen.findByText("Nessuna anomalia")).toBeInTheDocument();
    expect(screen.queryByText("Dettaglio anomalia selezionata")).not.toBeInTheDocument();
  });
});

describe("R133 manual detail fallbacks and lookups", () => {
  test("renders nullable anomaly fields with fallbacks in detail and report draft", async () => {
    setItems([anomaly("bare", {
      descrizione: null, anno_campagna: null, utenza_id: null, particella_id: null, dati_json: null,
      note_operatore: "  ",
    })]);
    await mountManual();
    expect(field("Anno:")).toHaveTextContent("—");
    expect(field("Utenza collegata:")).toHaveTextContent("—");
    expect(field("Particella collegata:")).toHaveTextContent("—");
    expect(within(detail()).getByText("Nessuna descrizione disponibile.")).toBeInTheDocument();
    expect(within(detail()).getByText("Nessuna particella collegata per questa anomalia.")).toBeInTheDocument();
    expect(within(detail()).getByText("{}")).toBeInTheDocument();
    expect(screen.getByLabelText("Titolo")).toHaveValue("VAL-99-custom · Anomalia Catasto");
    expect(screen.getByLabelText("Descrizione")).toHaveValue("Anomalia Catasto bare");
    expect(within(detail()).getByText("Ultima nota salvata: nessuna")).toBeInTheDocument();
  });

  test("a linked report shows its link and hides the report creation form", async () => {
    setItems([anomaly("linked", { segnalazione_id: "report-9" })]);
    await mountManual();
    expect(within(detail()).getByRole("link", { name: "Apri segnalazione" })).toHaveAttribute("href", "/operazioni/segnalazioni/report-9");
    expect(screen.queryByText("Crea segnalazione operativa")).not.toBeInTheDocument();
  });

  test("shows the current assignee by username or by raw ID when not assignable", async () => {
    mocks.users.mockResolvedValue({ items: [user(7, "mario")] });
    setItems([anomaly("a1", { assigned_to: 7 }), anomaly("a2", { assigned_to: 9 })]);
    await mountManual();
    await waitFor(() => expect(within(detail()).getByText("Assegnazione corrente: mario · admin")).toBeInTheDocument());
    expect(screen.getByLabelText("Assegna a")).toHaveValue("7");
    fireEvent.click(within(screen.getByRole("table")).getByText("Anomalia a2"));
    expect(await within(detail()).findByText("Assegnazione corrente: ID 9")).toBeInTheDocument();
    expect(screen.getByLabelText("Assegna a")).toHaveValue("");
  });

  test("saving an emptied assignment sends undefined and reports Error and non-Error failures", async () => {
    mocks.users.mockResolvedValue({ items: [user(7, "mario")] });
    setItems([anomaly("a1", { assigned_to: 7 })]);
    await mountManual();
    await waitFor(() => expect(screen.getByLabelText("Assegna a")).toHaveValue("7"));
    fireEvent.change(screen.getByLabelText("Assegna a"), { target: { value: "" } });
    fireEvent.click(screen.getByRole("button", { name: "Salva assegnazione" }));
    expect(await within(detail()).findByText("Assegnazione aggiornata.")).toBeInTheDocument();
    expect(mocks.update).toHaveBeenCalledWith("token", "a1", { assigned_to: undefined });

    mocks.update.mockRejectedValueOnce(new Error("assegnazione rifiutata"));
    fireEvent.click(screen.getByRole("button", { name: "Salva assegnazione" }));
    expect(await within(detail()).findByText("assegnazione rifiutata")).toBeInTheDocument();

    mocks.update.mockRejectedValueOnce("offline");
    fireEvent.click(screen.getByRole("button", { name: "Salva assegnazione" }));
    expect(await within(detail()).findByText("Errore aggiornamento assegnazione")).toBeInTheDocument();
  });

  test("panel ignore and reopen actions update the selected anomaly status", async () => {
    await mountManual();
    fireEvent.click(screen.getByRole("button", { name: "Ignora da pannello" }));
    await waitFor(() => expect(mocks.update).toHaveBeenCalledWith("token", "a1", { status: "ignora" }));
    await waitFor(() => expect(screen.getByRole("button", { name: "Riapri da pannello" })).toBeEnabled());
    fireEvent.click(screen.getByRole("button", { name: "Riapri da pannello" }));
    await waitFor(() => expect(mocks.update).toHaveBeenCalledWith("token", "a1", { status: "aperta" }));
  });

  test("a created report without number is confirmed generically and linked", async () => {
    mocks.createReport.mockResolvedValueOnce({ report: { id: "report-2" } });
    await mountManual();
    fireEvent.change(screen.getByLabelText("Categoria"), { target: { value: "cat-1" } });
    fireEvent.change(screen.getByLabelText("Gravità"), { target: { value: "sev-1" } });
    fireEvent.click(screen.getByRole("button", { name: "Crea segnalazione" }));
    expect(await within(detail()).findByText("Segnalazione operativa creata.")).toBeInTheDocument();
    expect(mocks.update).toHaveBeenCalledWith("token", "a1", { segnalazione_id: "report-2" });
  });

  test("a non-Error report creation failure shows the generic message", async () => {
    mocks.createReport.mockRejectedValueOnce("offline");
    await mountManual();
    fireEvent.change(screen.getByLabelText("Categoria"), { target: { value: "cat-1" } });
    fireEvent.change(screen.getByLabelText("Gravità"), { target: { value: "sev-1" } });
    fireEvent.click(screen.getByRole("button", { name: "Crea segnalazione" }));
    expect(await within(detail()).findByText("Errore creazione segnalazione")).toBeInTheDocument();
    expect(mocks.update).not.toHaveBeenCalled();
  });

  test("report lookup options fall back from name to code to id", async () => {
    mocks.categories.mockResolvedValue([{ id: "cat-code", code: "CAT" }, { id: "cat-id" }]);
    mocks.severities.mockResolvedValue([{ id: "sev-code", code: "SEV" }, { id: "sev-id" }]);
    await mountManual();
    await waitFor(() => expect(optionTexts("Categoria")).toEqual(["Seleziona categoria", "CAT", "cat-id"]));
    expect(optionTexts("Gravità")).toEqual(["Seleziona gravità", "SEV", "sev-id"]);
  });

  test("non-array report lookups leave only the placeholder options", async () => {
    mocks.categories.mockResolvedValue({ items: [{ id: "ignored" }] });
    mocks.severities.mockResolvedValue(null);
    await mountManual();
    await waitFor(() => expect(mocks.severities).toHaveBeenCalled());
    expect(optionTexts("Categoria")).toEqual(["Seleziona categoria"]);
    expect(optionTexts("Gravità")).toEqual(["Seleziona gravità"]);
  });

  test("rejected report lookups and users leave empty selectors", async () => {
    mocks.categories.mockRejectedValue(new Error("lookup down"));
    mocks.severities.mockResolvedValue([{ id: "sev-1", name: "Alta" }]);
    mocks.users.mockRejectedValue(new Error("users down"));
    await mountManual();
    await waitFor(() => expect(mocks.users).toHaveBeenCalled());
    expect(optionTexts("Categoria")).toEqual(["Seleziona categoria"]);
    expect(optionTexts("Gravità")).toEqual(["Seleziona gravità"]);
    expect(optionTexts("Assegna a")).toEqual(["Non assegnata"]);
  });
});

describe("R133 wizard nullable presentation", () => {
  test("CF wizard shows a dash for a missing district", async () => {
    mocks.params = new URLSearchParams("tab=cf");
    mocks.cfItems.mockResolvedValue({ items: [cfItem()], total: 1 });
    render(<CatastoAnomaliePage />);
    const name = await screen.findByText("Rossi Mario");
    const card = name.closest("div.rounded-2xl")!;
    expect(within(card as HTMLElement).getByText("Distretto:").querySelector("span")).toHaveTextContent("—");
  });

  test("comune wizard falls back for unnamed utenze and sparse candidates", async () => {
    mocks.params = new URLSearchParams("tab=comune");
    mocks.comuneItems.mockResolvedValue({ items: [comuneItem()], total: 1 });
    render(<CatastoAnomaliePage />);
    const name = await screen.findByText("Utenza senza denominazione");
    const card = name.closest("div.rounded-2xl") as HTMLElement;
    expect(within(card).getByText("Codice catastale:").querySelector("span")).toHaveTextContent("—");
    expect(within(card).getByText("Legacy:").querySelector("span")).toHaveTextContent("—");
    expect(within(card).getByText("Provincia:").querySelector("span")).toHaveTextContent("—");
  });

  test("particella wizard falls back for unnamed utenze, codes and districts", async () => {
    mocks.params = new URLSearchParams("tab=particella");
    mocks.particellaItems.mockResolvedValue({ items: [particellaItem()], total: 1 });
    render(<CatastoAnomaliePage />);
    const name = await screen.findByText("Utenza senza denominazione");
    const card = name.closest("div.rounded-2xl") as HTMLElement;
    expect(within(card).getByText("Codice comune:").querySelector("span")).toHaveTextContent("—");
    expect(within(card).getByText("Distretto:").querySelector("span")).toHaveTextContent("—");
  });
});

describe("R133 next-page clamps under a double activation before re-render", () => {
  async function doubleNext() {
    const next = screen.getByRole("button", { name: "Successiva" });
    expect(next).toBeEnabled();
    await act(async () => {
      fireEvent.click(next);
      fireEvent.click(next);
    });
  }

  function pagesRequested(mock: ReturnType<typeof vi.fn>) {
    return mock.mock.calls.map((call) => (call[1] as { page: number }).page);
  }

  test("CF wizard never requests a page beyond the last one", async () => {
    mocks.params = new URLSearchParams("tab=cf");
    mocks.cfItems.mockResolvedValue({ items: [cfItem()], total: 50 });
    render(<CatastoAnomaliePage />);
    await screen.findByText("Rossi Mario");
    await doubleNext();
    await waitFor(() => expect(pagesRequested(mocks.cfItems)).toContain(2));
    expect(Math.max(...pagesRequested(mocks.cfItems))).toBe(2);
    expect(screen.getByText("Pagina 2 di 2")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Successiva" })).toBeDisabled();
  });

  test("comune wizard never requests a page beyond the last one", async () => {
    mocks.params = new URLSearchParams("tab=comune");
    mocks.comuneItems.mockResolvedValue({ items: [comuneItem()], total: 50 });
    render(<CatastoAnomaliePage />);
    await screen.findByText("Utenza senza denominazione");
    await doubleNext();
    await waitFor(() => expect(pagesRequested(mocks.comuneItems)).toContain(2));
    expect(Math.max(...pagesRequested(mocks.comuneItems))).toBe(2);
    expect(screen.getByText("Pagina 2 di 2")).toBeInTheDocument();
  });

  test("particella wizard never requests a page beyond the last one", async () => {
    mocks.params = new URLSearchParams("tab=particella");
    mocks.particellaItems.mockResolvedValue({ items: [particellaItem()], total: 50 });
    render(<CatastoAnomaliePage />);
    await screen.findByText("Utenza senza denominazione");
    await doubleNext();
    await waitFor(() => expect(pagesRequested(mocks.particellaItems)).toContain(2));
    expect(Math.max(...pagesRequested(mocks.particellaItems))).toBe(2);
    expect(screen.getByText("Pagina 2 di 2")).toBeInTheDocument();
  });

  test("overview register never requests a page beyond the last one", async () => {
    setItems([anomaly()], 100);
    await mountManual();
    await doubleNext();
    await waitFor(() => expect(pagesRequested(mocks.list)).toContain(2));
    expect(Math.max(...pagesRequested(mocks.list))).toBe(2);
    expect(screen.getByText("Pagina 2 di 2", { selector: "div" })).toBeInTheDocument();
  });
});
