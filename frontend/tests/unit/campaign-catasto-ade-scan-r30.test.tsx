import type { ReactNode } from "react";
import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import CatastoAnomaliePage from "@/app/catasto/anomalie/page";
import { formatDateTime } from "@/lib/presentation";
import type { ElaborazioneBatch } from "@/types/api";
import type { CatAdeStatusScanCandidate, CatAdeStatusScanRunResponse, CatAdeStatusScanSummary } from "@/types/catasto";

const mocks = vi.hoisted(() => ({
  params: new URLSearchParams("tab=ade"),
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
  run: vi.fn(),
  users: vi.fn(),
  categories: vi.fn(),
  severities: vi.fn(),
  page: vi.fn(),
  workspace: vi.fn(),
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
  catastoRunAdeStatusScan: mocks.run,
}));
vi.mock("@/lib/api", () => ({ getElaborazioneBatches: mocks.batches, listApplicationUsers: mocks.users }));
vi.mock("@/features/operazioni/api/client", () => ({ getReportCategories: mocks.categories, getReportSeverities: mocks.severities }));
vi.mock("@/components/catasto/catasto-page", () => ({
  CatastoPage: (props: { children: ReactNode; requiredRoles: string[]; requiredModule: string }) => {
    mocks.page(props);
    return <>{props.children}</>;
  },
}));
vi.mock("@/components/elaborazioni/workspace-modal", () => ({
  ElaborazioneWorkspaceModal: (props: { open: boolean; href: string | null; title: string; description: string | null; onClose: () => void }) => {
    mocks.workspace(props);
    return props.open ? <div role="dialog" aria-label={props.title} data-href={props.href}>
      <p>{props.description}</p>
      <button type="button" onClick={props.onClose}>Chiudi batch</button>
    </div> : null;
  },
}));
vi.mock("@/components/catasto/workspace-modal", () => ({ CatastoWorkspaceModal: () => null }));

const prefix = "Visure storiche AdE particelle non collegate";

function summary(overrides: Partial<CatAdeStatusScanSummary> = {}): CatAdeStatusScanSummary {
  return { total_unmatched: 31, pending: 4, last_checked_at: null, buckets: [], ...overrides };
}

function candidate(id = "first", overrides: Partial<CatAdeStatusScanCandidate> = {}): CatAdeStatusScanCandidate {
  return {
    ruolo_particella_id: id, anno_tributario: 2026, comune_nome: `Comune ${id}`, comune_codice: "H501",
    sezione: null, foglio: "12", particella: "34", subalterno: null, match_reason: null,
    ade_scan_status: null, ade_scan_classification: null, ade_scan_checked_at: null, ade_scan_document_id: null,
    ...overrides,
  };
}

function batch(id = "first", overrides: Partial<ElaborazioneBatch> = {}): ElaborazioneBatch {
  return {
    id, user_id: 1, name: `${prefix} ${id}`, status: "completed", total_items: 10, completed_items: 7,
    failed_items: 3, skipped_items: 0, not_found_items: 0, source_filename: null, current_operation: null,
    report_json_path: null, report_md_path: null, created_at: "2026-10-11T10:00:00Z", started_at: null,
    completed_at: null, ...overrides,
  };
}

function deferred<Value>() {
  let resolve!: (value: Value) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<Value>((fulfill, fail) => { resolve = fulfill; reject = fail; });
  return { promise, resolve, reject };
}

function scan() {
  return screen.getByText("Scansione AdE particelle non collegate").closest("article")!;
}

function refresh() {
  return within(scan()).getByRole("button", { name: "Aggiorna" });
}

function run() {
  return within(scan()).getByRole("button", { name: /Metti in coda tutte le visure|Preparazione\.\.\./ });
}

function selectTab(name: RegExp) {
  fireEvent.click(within(screen.getByRole("navigation", { name: "Code anomalie" })).getByRole("button", { name }));
}

async function mountAde() {
  const view = render(<CatastoAnomaliePage />);
  await waitFor(() => expect(refresh()).toBeEnabled());
  await waitFor(() => expect(screen.getByRole("button", { name: "Reset contesto" })).toBeEnabled());
  return view;
}

function batchNames() {
  return within(scan()).getByRole("table").querySelectorAll("tbody tr td:first-child button");
}

beforeEach(() => {
  vi.resetAllMocks();
  mocks.params = new URLSearchParams("tab=ade");
  mocks.token.mockReturnValue("token");
  mocks.list.mockResolvedValue({ items: [], total: 0, page: 1, page_size: 50 });
  mocks.summary.mockResolvedValue({ buckets: [], total: 0 });
  mocks.cfItems.mockResolvedValue({ items: [], total: 0 });
  mocks.comuneItems.mockResolvedValue({ items: [], total: 0 });
  mocks.particellaItems.mockResolvedValue({ items: [], total: 0 });
  mocks.adeSummary.mockResolvedValue(summary());
  mocks.adeCandidates.mockResolvedValue({ items: [candidate()], total: 31 });
  mocks.batches.mockResolvedValue([]);
  mocks.run.mockResolvedValue({ batch_id: "queued", created: 2, skipped: 0 });
  mocks.users.mockResolvedValue({ items: [] });
  mocks.categories.mockResolvedValue([]);
  mocks.severities.mockResolvedValue([]);
});

afterEach(cleanup);

describe("R30 original AdE public loading and batch presentation", () => {
  test("loads token summary, fixed-eight candidates and user batches without context filters", async () => {
    mocks.params = new URLSearchParams("tab=ade&anno=2025&distretto=09&status=chiusa&severita=warning&page=3");
    await mountAde();
    expect(mocks.adeSummary).toHaveBeenCalledExactlyOnceWith("token");
    expect(mocks.adeCandidates).toHaveBeenCalledExactlyOnceWith("token", { limit: 8 });
    expect(mocks.batches).toHaveBeenCalledExactlyOnceWith("token");
    expect(mocks.list).toHaveBeenCalledWith("token", expect.objectContaining({ anno: 2025, distretto: "09", status: "chiusa", page: 3 }));
    expect(mocks.cfItems).not.toHaveBeenCalled();
    expect(mocks.comuneItems).not.toHaveBeenCalled();
    expect(mocks.particellaItems).not.toHaveBeenCalled();
    expect(mocks.page).toHaveBeenCalledWith(expect.objectContaining({ requiredRoles: ["admin", "super_admin"], requiredModule: "catasto" }));
    expect(within(screen.getByRole("navigation", { name: "Code anomalie" })).getByRole("button", { name: "Scansione AdE31" })).toHaveAttribute("aria-pressed", "true");
  });

  test("starts all three requests concurrently and commits none until the slowest completes", async () => {
    const slow = deferred<ElaborazioneBatch[]>();
    mocks.batches.mockReturnValueOnce(slow.promise);
    render(<CatastoAnomaliePage />);
    expect(mocks.adeSummary).toHaveBeenCalledOnce();
    expect(mocks.adeCandidates).toHaveBeenCalledOnce();
    expect(mocks.batches).toHaveBeenCalledOnce();
    expect(refresh()).toBeDisabled();
    expect(run()).toBeDisabled();
    await act(async () => { await Promise.resolve(); });
    expect(within(scan()).queryByText("Comune first Fg. 12 Part. 34")).not.toBeInTheDocument();
    expect(within(scan()).getByText("Non collegate").parentElement).toHaveTextContent("—");
    await act(async () => { slow.resolve([batch()]); });
    expect(refresh()).toBeEnabled();
    expect(within(scan()).getByText("Comune first Fg. 12 Part. 34")).toBeInTheDocument();
    expect(within(scan()).getByText("Non collegate").parentElement).toHaveTextContent("31");
  });

  test("shows summary zeroes, formatted timestamp and only the first six buckets in response order", async () => {
    mocks.adeSummary.mockResolvedValue(summary({ total_unmatched: 0, pending: 0, last_checked_at: "2026-10-10T10:00:00Z", buckets: Array.from({ length: 8 }, (_, index) => ({ status: `state${index}`, classification: `kind${index}`, count: index + 1 })) }));
    await mountAde();
    expect(within(scan()).getByText("Non collegate").parentElement).toHaveTextContent("0");
    expect(within(scan()).getByText("In coda SISTER").parentElement).toHaveTextContent("0");
    expect(within(scan()).getByText(formatDateTime("2026-10-10T10:00:00Z"))).toBeInTheDocument();
    const labels = within(scan()).getAllByText(/state\d \/ kind\d/).map((element) => element.textContent);
    expect(labels).toEqual(Array.from({ length: 6 }, (_, index) => `state${index} / kind${index}`));
    expect(within(scan()).queryByText("state6 / kind6")).not.toBeInTheDocument();
  });

  test("renders candidate optional fields, PDF and fallbacks without client sorting or truncation", async () => {
    mocks.adeCandidates.mockResolvedValue({ items: [candidate("z", { sezione: "B", subalterno: "3", match_reason: "non collegata", ade_scan_status: "completed", ade_scan_document_id: "pdf" }), candidate("a"), ...Array.from({ length: 7 }, (_, index) => candidate(`extra${index}`))], total: 100 });
    await mountAde();
    expect(within(scan()).getByText("Comune z sez. B Fg. 12 Part. 34 Sub. 3")).toBeInTheDocument();
    expect(within(scan()).getByText("Motivo: non collegata · Stato AdE: completed · PDF acquisito")).toBeInTheDocument();
    expect(within(scan()).getAllByText("Motivo: — · Stato AdE: non scansionata")).toHaveLength(8);
    expect(within(scan()).getAllByText(/^Comune /).map((element) => element.textContent)).toEqual(["Comune z sez. B Fg. 12 Part. 34 Sub. 3", "Comune a Fg. 12 Part. 34", ...Array.from({ length: 7 }, (_, index) => `Comune extra${index} Fg. 12 Part. 34`)]);
  });

  test("renders original empty summary, candidates and batches without an active action", async () => {
    mocks.adeCandidates.mockResolvedValue({ items: [], total: 0 });
    await mountAde();
    expect(within(scan()).getByText("Mai eseguita")).toBeInTheDocument();
    expect(within(scan()).getByText("Nessun esito AdE salvato.")).toBeInTheDocument();
    expect(within(scan()).getByText("Nessuna candidata immediatamente disponibile.")).toBeInTheDocument();
    expect(within(scan()).getByText("Nessun batch scansione AdE trovato per l'utente corrente.")).toBeInTheDocument();
    expect(within(scan()).queryByRole("button", { name: "Apri batch attivo" })).not.toBeInTheDocument();
  });

  test("filters case-sensitive literal name prefixes before newest-first top-six with stable ties", async () => {
    const matched = Array.from({ length: 8 }, (_, index) => batch(`b${index}`, { created_at: `2026-10-${String(index + 1).padStart(2, "0")}T10:00:00Z` }));
    matched[6].created_at = matched[7].created_at;
    const excluded = [batch("null", { name: null }), batch("empty", { name: "" }), batch("case", { name: prefix.toLowerCase() }), batch("leading", { name: ` ${prefix}` }), batch("middle", { name: `altro ${prefix}` })];
    mocks.batches.mockResolvedValue([...excluded, ...matched]);
    await mountAde();
    expect(Array.from(batchNames(), (element) => element.textContent)).toEqual(["b6", "b7", "b5", "b4", "b3", "b2"].map((id) => `${prefix} ${id}`));
    expect(matched.map((item) => item.id)).toEqual(Array.from({ length: 8 }, (_, index) => `b${index}`));
    expect(within(scan()).queryByRole("button", { name: "Apri batch attivo" })).not.toBeInTheDocument();
  });

  test("keeps invalid-date ties in response order and accepts the bare prefix and undelimited suffix", async () => {
    mocks.batches.mockResolvedValue([batch("bare", { name: prefix, created_at: "invalid-date" }), batch("suffix", { name: `${prefix}SUFFIX`, created_at: "invalid-date" })]);
    await mountAde();
    expect(Array.from(batchNames(), (element) => element.textContent)).toEqual([prefix, `${prefix}SUFFIX`]);
    expect(within(scan()).getAllByText("invalid-date")).toHaveLength(2);
  });

  test.each(["pending", "processing"] as const)("chooses newest %s before another running batch but ignores completed", async (status) => {
    mocks.batches.mockResolvedValue([batch("older", { status: "processing", created_at: "2026-10-01T10:00:00Z" }), batch("newest", { status: "completed", created_at: "2026-10-11T10:00:00Z" }), batch("active", { status, created_at: "2026-10-10T10:00:00Z", not_found_items: 2, skipped_items: 1, current_operation: "Operazione reale" })]);
    await mountAde();
    const activeRow = within(scan()).getByRole("button", { name: `${prefix} active` }).closest("tr")!;
    expect(activeRow).toHaveTextContent("ok 7ko 3n.d. 2skip 1");
    expect(activeRow).toHaveTextContent("Operazione reale");
    fireEvent.click(within(scan()).getByRole("button", { name: "Apri batch attivo" }));
    expect(screen.getByRole("dialog")).toHaveAttribute("data-href", "/elaborazioni/batches/active");
  });

  test("an older active batch outside the six visible batches does not produce an active action", async () => {
    mocks.batches.mockResolvedValue([batch("old-running", { status: "pending", created_at: "2026-09-01T10:00:00Z" }), ...Array.from({ length: 6 }, (_, index) => batch(`done${index}`))]);
    await mountAde();
    expect(batchNames()).toHaveLength(6);
    expect(within(scan()).queryByRole("button", { name: "Apri batch attivo" })).not.toBeInTheDocument();
  });

  test.each(["failed", "cancelled"] as const)("%s is rendered but never treated as active", async (status) => {
    mocks.batches.mockResolvedValue([batch("terminal", { status })]);
    await mountAde();
    expect(within(scan()).queryByRole("button", { name: "Apri batch attivo" })).not.toBeInTheDocument();
    expect(within(scan()).getByRole("table")).toHaveTextContent(status === "failed" ? "Fallito" : "Annullato");
  });

  test.each(["name", "action"])("opens via %s and closes the child boundary without losing the scan data or reloading", async (source) => {
    mocks.batches.mockResolvedValue([batch()]);
    await mountAde();
    const button = source === "name" ? within(scan()).getByRole("button", { name: `${prefix} first` }) : within(scan()).getByRole("button", { name: "Apri batch" });
    fireEvent.click(button);
    expect(screen.getByRole("dialog", { name: `${prefix} first` })).toHaveAttribute("data-href", "/elaborazioni/batches/first");
    expect(screen.getByRole("dialog")).toHaveTextContent("Dettaglio operativo del batch visure AdE con stato richieste, errori e CAPTCHA manuali.");
    fireEvent.click(screen.getByRole("button", { name: "Chiudi batch" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(mocks.workspace).toHaveBeenLastCalledWith(expect.objectContaining({ open: false, href: null, title: "Dettaglio batch", description: null }));
    expect(mocks.batches).toHaveBeenCalledOnce();
    expect(within(scan()).getByText("Comune first Fg. 12 Part. 34")).toBeInTheDocument();
  });
});

describe("R30 original AdE command, failures and asynchronous lifecycle", () => {
  test.each([
    [2, 0, "Batch scansione AdE creato: 2 richieste messe in coda."],
    [2, 3, "Batch scansione AdE creato: 2 richieste messe in coda, 3 saltate."],
    [0, 0, "Nessuna nuova particella da mettere in coda."],
    [0, 3, "Nessuna nuova particella da mettere in coda."],
  ])("created=%s skipped=%s sends empty payload and refreshes only AdE", async (created, skipped, message) => {
    mocks.run.mockResolvedValue({ batch_id: "queued", created, skipped });
    await mountAde();
    fireEvent.click(run());
    await screen.findByText(message);
    await waitFor(() => expect(run()).toBeEnabled());
    expect(mocks.run).toHaveBeenCalledExactlyOnceWith("token", {});
    expect(mocks.adeSummary).toHaveBeenCalledTimes(2);
    expect(mocks.adeCandidates).toHaveBeenCalledTimes(2);
    expect(mocks.batches).toHaveBeenCalledTimes(2);
    expect(mocks.list).toHaveBeenCalledOnce();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  test("keeps both buttons disabled through deferred command and refresh and does not duplicate the command", async () => {
    const command = deferred<CatAdeStatusScanRunResponse>();
    const load = deferred<CatAdeStatusScanSummary>();
    mocks.run.mockReturnValueOnce(command.promise);
    await mountAde();
    mocks.adeSummary.mockReturnValueOnce(load.promise);
    fireEvent.click(run());
    expect(run()).toBeDisabled();
    expect(refresh()).toBeDisabled();
    fireEvent.click(run());
    fireEvent.click(refresh());
    expect(mocks.run).toHaveBeenCalledOnce();
    expect(mocks.adeSummary).toHaveBeenCalledOnce();
    await act(async () => { command.resolve({ batch_id: "queued", created: 5, skipped: 1 }); });
    expect(within(scan()).getByText("Batch scansione AdE creato: 5 richieste messe in coda, 1 saltate.")).toBeInTheDocument();
    expect(run()).toBeDisabled();
    expect(mocks.adeSummary).toHaveBeenCalledTimes(2);
    await act(async () => { load.resolve(summary({ total_unmatched: 9 })); });
    expect(run()).toBeEnabled();
    expect(within(scan()).getByText("Non collegate").parentElement).toHaveTextContent("9");
  });

  test.each([new Error("worker unavailable"), "plain failure"])("command rejection %s uses original error fallback without refresh", async (error) => {
    mocks.run.mockRejectedValueOnce(error);
    await mountAde();
    fireEvent.click(run());
    await screen.findByText(error instanceof Error ? error.message : "Errore avvio scansione AdE");
    await waitFor(() => expect(run()).toBeEnabled());
    expect(mocks.adeSummary).toHaveBeenCalledOnce();
    expect(within(scan()).queryByText(/Batch scansione AdE creato/)).not.toBeInTheDocument();
  });

  test.each(["adeSummary", "adeCandidates", "batches"] as const)("refresh failure in %s preserves all prior data and a later success clears only the error", async (api) => {
    mocks.batches.mockResolvedValue([batch()]);
    await mountAde();
    mocks[api].mockRejectedValueOnce(new Error(`failed ${api}`));
    mocks.adeSummary.mockResolvedValue(summary({ total_unmatched: 99 }));
    mocks.adeCandidates.mockResolvedValue({ items: [candidate("new")], total: 99 });
    fireEvent.click(refresh());
    await screen.findByText(`failed ${api}`);
    expect(within(scan()).getByText("Non collegate").parentElement).toHaveTextContent("31");
    expect(within(scan()).getByText("Comune first Fg. 12 Part. 34")).toBeInTheDocument();
    expect(within(scan()).queryByText("Comune new Fg. 12 Part. 34")).not.toBeInTheDocument();
    await waitFor(() => expect(refresh()).toBeEnabled());
    fireEvent.click(refresh());
    await screen.findByText("Comune new Fg. 12 Part. 34");
    expect(within(scan()).queryByText(`failed ${api}`)).not.toBeInTheDocument();
  });

  test("initial non-Error load rejection uses the original loader fallback", async () => {
    mocks.adeSummary.mockRejectedValueOnce(null);
    await mountAde();
    expect(within(scan()).getByText("Errore caricamento scansione AdE")).toBeInTheDocument();
    expect(within(scan()).getByText("Non collegate").parentElement).toHaveTextContent("—");
    expect(within(scan()).queryByText("Nessun esito AdE salvato.")).not.toBeInTheDocument();
  });

  test("successful queue plus failed refresh displays both success and loader error; manual refresh retains success", async () => {
    await mountAde();
    mocks.batches.mockRejectedValueOnce(new Error("reload failed"));
    fireEvent.click(run());
    await screen.findByText("reload failed");
    expect(within(scan()).getByText("Batch scansione AdE creato: 2 richieste messe in coda.")).toBeInTheDocument();
    await waitFor(() => expect(refresh()).toBeEnabled());
    fireEvent.click(refresh());
    await waitFor(() => expect(within(scan()).queryByText("reload failed")).not.toBeInTheDocument());
    expect(within(scan()).getByText("Batch scansione AdE creato: 2 richieste messe in coda.")).toBeInTheDocument();
  });

  test("a new command clears the prior success and error synchronously before its pending outcome", async () => {
    await mountAde();
    mocks.batches.mockRejectedValueOnce(new Error("reload failed"));
    fireEvent.click(run());
    await screen.findByText("reload failed");
    await waitFor(() => expect(run()).toBeEnabled());
    const command = deferred<CatAdeStatusScanRunResponse>();
    mocks.run.mockReturnValueOnce(command.promise);
    fireEvent.click(run());
    expect(within(scan()).queryByText("reload failed")).not.toBeInTheDocument();
    expect(within(scan()).queryByText(/Batch scansione AdE creato/)).not.toBeInTheDocument();
    await act(async () => { command.resolve({ batch_id: null, created: 0, skipped: 0 }); });
    expect(within(scan()).getByText("Nessuna nuova particella da mettere in coda.")).toBeInTheDocument();
  });

  test("absent token skips initial AdE loading and both public actions without a synthetic error", async () => {
    mocks.token.mockReturnValue(null);
    await mountAde();
    fireEvent.click(refresh());
    fireEvent.click(run());
    expect(mocks.adeSummary).not.toHaveBeenCalled();
    expect(mocks.adeCandidates).not.toHaveBeenCalled();
    expect(mocks.batches).not.toHaveBeenCalled();
    expect(mocks.run).not.toHaveBeenCalled();
    expect(run()).toBeEnabled();
    expect(within(scan()).queryByText(/Errore/)).not.toBeInTheDocument();
  });

  test("token loss before queue or refresh is a no-op but restoration uses the new token", async () => {
    await mountAde();
    mocks.token.mockReturnValue(null);
    fireEvent.click(run());
    fireEvent.click(refresh());
    expect(mocks.run).not.toHaveBeenCalled();
    expect(mocks.adeSummary).toHaveBeenCalledOnce();
    mocks.token.mockReturnValue("replacement");
    fireEvent.click(run());
    await screen.findByText("Batch scansione AdE creato: 2 richieste messe in coda.");
    await waitFor(() => expect(run()).toBeEnabled());
    expect(mocks.run).toHaveBeenCalledExactlyOnceWith("replacement", {});
    expect(mocks.adeSummary).toHaveBeenLastCalledWith("replacement");
  });

  test("token lost during a successful queue skips its reload yet retains success and releases busy", async () => {
    const command = deferred<CatAdeStatusScanRunResponse>();
    mocks.run.mockReturnValueOnce(command.promise);
    await mountAde();
    fireEvent.click(run());
    mocks.token.mockReturnValue(null);
    await act(async () => { command.resolve({ batch_id: "queued", created: 1, skipped: 0 }); });
    expect(within(scan()).getByText("Batch scansione AdE creato: 1 richieste messe in coda.")).toBeInTheDocument();
    expect(run()).toBeEnabled();
    expect(mocks.adeSummary).toHaveBeenCalledOnce();
  });

  test("AdE loads on inactive manual tab and does not reload on context or tab changes", async () => {
    mocks.params = new URLSearchParams("tab=manuale");
    render(<CatastoAnomaliePage />);
    await waitFor(() => expect(screen.getByRole("button", { name: "Reset contesto" })).toBeEnabled());
    await waitFor(() => expect(within(screen.getByRole("navigation", { name: "Code anomalie" })).getByRole("button", { name: "Scansione AdE31" })).toBeInTheDocument());
    selectTab(/Scansione AdE/);
    expect(refresh()).toBeEnabled();
    fireEvent.change(screen.getByLabelText("Anno"), { target: { value: "2024" } });
    fireEvent.change(screen.getByLabelText("Distretto"), { target: { value: "09" } });
    await waitFor(() => expect(mocks.list).toHaveBeenLastCalledWith("token", expect.objectContaining({ anno: 2024, distretto: "09" })));
    await waitFor(() => expect(screen.getByRole("button", { name: "Reset contesto" })).toBeEnabled());
    selectTab(/Triage manuale/);
    selectTab(/Scansione AdE/);
    expect(mocks.adeSummary).toHaveBeenCalledOnce();
    expect(mocks.adeCandidates).toHaveBeenCalledOnce();
    expect(mocks.batches).toHaveBeenCalledOnce();
  });

  test("late hidden-tab load still commits and returning to AdE presents it without reload", async () => {
    const load = deferred<CatAdeStatusScanSummary>();
    mocks.adeSummary.mockReturnValueOnce(load.promise);
    render(<CatastoAnomaliePage />);
    selectTab(/Triage manuale/);
    await act(async () => { load.resolve(summary({ total_unmatched: 77 })); });
    expect(screen.queryByText("Scansione AdE particelle non collegate")).not.toBeInTheDocument();
    expect(within(screen.getByRole("navigation", { name: "Code anomalie" })).getByRole("button", { name: "Scansione AdE77" })).toBeInTheDocument();
    selectTab(/Scansione AdE/);
    expect(refresh()).toBeEnabled();
    expect(within(scan()).getByText("Non collegate").parentElement).toHaveTextContent("77");
    expect(mocks.adeSummary).toHaveBeenCalledOnce();
  });

  test("late command refresh commits while its tab is hidden and the batch child boundary persists across tabs", async () => {
    mocks.batches.mockResolvedValue([batch()]);
    const command = deferred<CatAdeStatusScanRunResponse>();
    mocks.run.mockReturnValueOnce(command.promise);
    await mountAde();
    fireEvent.click(within(scan()).getByRole("button", { name: "Apri batch" }));
    fireEvent.click(run());
    selectTab(/Triage manuale/);
    expect(screen.getByRole("dialog")).toHaveAttribute("data-href", "/elaborazioni/batches/first");
    mocks.adeCandidates.mockResolvedValue({ items: [candidate("late")], total: 1 });
    await act(async () => { command.resolve({ batch_id: "queued", created: 1, skipped: 1 }); });
    selectTab(/Scansione AdE/);
    expect(within(scan()).getByText("Comune late Fg. 12 Part. 34")).toBeInTheDocument();
    expect(within(scan()).getByText("Batch scansione AdE creato: 1 richieste messe in coda, 1 saltate.")).toBeInTheDocument();
    expect(run()).toBeEnabled();
    expect(mocks.adeSummary).toHaveBeenCalledTimes(2);
    fireEvent.click(screen.getByRole("button", { name: "Chiudi batch" }));
  });

  test("unmount does not cancel a pending command or its subsequent public AdE reload", async () => {
    const command = deferred<CatAdeStatusScanRunResponse>();
    mocks.run.mockReturnValueOnce(command.promise);
    const view = await mountAde();
    fireEvent.click(run());
    view.unmount();
    await act(async () => { command.resolve({ batch_id: "queued", created: 2, skipped: 0 }); });
    expect(mocks.adeSummary).toHaveBeenCalledTimes(2);
    expect(mocks.adeCandidates).toHaveBeenCalledTimes(2);
    expect(mocks.batches).toHaveBeenCalledTimes(2);
    expect(screen.queryByText("Scansione AdE particelle non collegate")).not.toBeInTheDocument();
  });
});
