import { StrictMode, type ReactNode } from "react";
import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { ElaborazioniCapacitasWorkspace } from "@/components/elaborazioni/capacitas-workspace";
import type { CapacitasCredential } from "@/types/api";

const mocks = vi.hoisted(() => ({
  token: vi.fn(), credentials: vi.fn(), authError: vi.fn(),
  terreniJobs: vi.fn(), particelleJobs: vi.fn(), historyJobs: vi.fn(), incassJobs: vi.fn(),
  createTerreni: vi.fn(), createParticelle: vi.fn(), createHistory: vi.fn(), createIncass: vi.fn(),
}));

vi.mock("@/lib/auth", () => ({ getStoredAccessToken: mocks.token }));
vi.mock("@/lib/api", () => ({
  listCapacitasCredentials: mocks.credentials,
  listCapacitasTerreniJobs: mocks.terreniJobs,
  listCapacitasParticelleSyncJobs: mocks.particelleJobs,
  listCapacitasAnagraficaHistoryJobs: mocks.historyJobs,
  listCapacitasInCassSyncJobs: mocks.incassJobs,
  createCapacitasTerreniJob: mocks.createTerreni,
  createCapacitasParticelleSyncJob: mocks.createParticelle,
  createCapacitasAnagraficaHistoryJob: mocks.createHistory,
  createCapacitasInCassSyncJob: mocks.createIncass,
  isAuthError: mocks.authError,
}));
vi.mock("@/components/app/protected-page", () => ({
  ProtectedPage: ({ children }: { children: ReactNode }) => <>{children}</>,
}));
vi.mock("@/components/elaborazioni/workspace-modal", () => ({ ElaborazioneWorkspaceModal: () => null }));

const families = ["terreni", "particelle", "history", "incass"] as const;
type Family = typeof families[number];
type CredentialIds = Record<Family, number | undefined>;

const panels = {
  terreni: { tab: "Terreni batch", title: "Lookup territorio e sync Terreni", submit: "Avvia job batch" },
  particelle: { tab: "Sync particelle", title: "Sincronizzazione progressiva particelle GAIA", submit: "Avvia sync progressiva" },
  history: { tab: "Storico anagrafico", title: "Import storico anagrafiche Capacitas", submit: "Avvia import storico" },
  incass: { tab: "Avvisi pagamenti", title: "Sincronizzazione avvisi di pagamento sugli utenti", submit: "Avvia sync avvisi" },
};
const createMocks = {
  terreni: mocks.createTerreni, particelle: mocks.createParticelle,
  history: mocks.createHistory, incass: mocks.createIncass,
};
const listMocks = {
  terreni: mocks.terreniJobs, particelle: mocks.particelleJobs,
  history: mocks.historyJobs, incass: mocks.incassJobs,
};
const SUBJECT = "00000000-0000-4000-8000-000000000016";
const IDXANA = "48A9749E-96BF-4617-A019-046BF4CECA16";
const batchItems = [{ label: "Uras 1/680", comune: "Uras", foglio: "1", particella: "680", sezione: "", sub: "" }];

function credential(id: number, active = true): CapacitasCredential {
  return {
    id, label: `Account ${id}`, username: `operator-${id}`, active,
    allowed_hours_start: 0, allowed_hours_end: 24, last_used_at: null, last_error: null,
    consecutive_failures: 0, created_at: "2026-10-09T12:00:00Z", updated_at: "2026-10-09T12:00:00Z",
  };
}

function deferred<Value>() {
  let resolve!: (value: Value) => void;
  let reject!: (error: unknown) => void;
  const promise = new Promise<Value>((fulfill, fail) => { resolve = fulfill; reject = fail; });
  return { promise, resolve, reject };
}

function panel(family: Family) {
  const navigation = screen.getByRole("navigation", { name: "Sezioni Capacitas" });
  fireEvent.click(within(navigation).getByRole("button", { name: new RegExp(`^${panels[family].tab}`) }));
  const article = screen.getByText(panels[family].title).closest("article");
  expect(article).not.toBeNull();
  return within(article!);
}

function selection(family: Family) {
  return panel(family).getByRole<HTMLSelectElement>("combobox", { name: "Credenziale" });
}

function select(family: Family, value: string) {
  fireEvent.change(selection(family), { target: { value } });
  expect(selection(family)).toHaveValue(value);
}

async function mount(strict = false) {
  const workspace = <ElaborazioniCapacitasWorkspace embedded />;
  render(strict ? <StrictMode>{workspace}</StrictMode> : workspace);
  await screen.findByText("Nessun job particelle registrato");
  await waitFor(() => {
    for (const family of families) expect(listMocks[family]).toHaveBeenCalledTimes(strict ? 2 : 1);
  });
}

// Edits use the mounted public controls while the credential request is pending.
// Payload expectations below are literals; they never call the runtime mapper.
async function editOtherFields() {
  let controls = panel("terreni");
  fireEvent.click(controls.getByLabelText("Continua se una riga fallisce"));
  fireEvent.click(controls.getByLabelText("Scarica certificati"));
  fireEvent.click(controls.getByLabelText("Scarica dettagli terreno"));
  fireEvent.change(controls.getByLabelText(/^Pausa richieste \(ms\)/), { target: { value: "123" } });
  const contents = "comune,foglio,particella\nUras,1,680";
  const file = new File([contents], "credential-r16.csv", { type: "text/csv" });
  Object.defineProperty(file, "text", { value: () => Promise.resolve(contents) });
  fireEvent.change(controls.getByLabelText("File batch"), { target: { files: [file] } });
  await waitFor(() => expect(controls.getByRole("button", { name: panels.terreni.submit })).toBeEnabled());

  controls = panel("particelle");
  fireEvent.change(controls.getByLabelText("Limite run"), { target: { value: "12" } });
  fireEvent.click(controls.getByLabelText("Solo particelle dovute"));
  fireEvent.click(controls.getByLabelText("Scarica dettagli"));

  controls = panel("history");
  fireEvent.change(controls.getByLabelText("Lista subject_id"), { target: { value: SUBJECT } });
  fireEvent.change(controls.getByLabelText("Lista IDXANA"), { target: { value: IDXANA } });
  fireEvent.click(controls.getByLabelText("Continua se una riga fallisce"));

  controls = panel("incass");
  fireEvent.change(controls.getByLabelText("Limite soggetti"), { target: { value: "23" } });
  fireEvent.change(controls.getByLabelText("Pausa richieste (ms)"), { target: { value: "321" } });
  fireEvent.click(controls.getByLabelText("Salva dettaglio avviso"));
  fireEvent.click(controls.getByLabelText("Scarica ricevute PEC su NAS"));
  fireEvent.click(controls.getByLabelText("Continua se un soggetto fallisce"));
}

function assertOtherFields() {
  let controls = panel("terreni");
  expect(controls.getByText("credential-r16.csv")).toBeVisible();
  expect(controls.getByLabelText(/^Pausa richieste \(ms\)/)).toHaveValue("123");
  for (const label of ["Continua se una riga fallisce", "Scarica certificati", "Scarica dettagli terreno"]) {
    expect(controls.getByLabelText(label)).not.toBeChecked();
  }
  controls = panel("particelle");
  expect(controls.getByLabelText("Limite run")).toHaveValue("12");
  expect(controls.getByLabelText("Solo particelle dovute")).not.toBeChecked();
  expect(controls.getByLabelText("Scarica dettagli")).not.toBeChecked();
  expect(controls.getByLabelText("Scarica certificati")).toBeChecked();
  controls = panel("history");
  expect(controls.getByLabelText("Lista subject_id")).toHaveValue(SUBJECT);
  expect(controls.getByLabelText("Lista IDXANA")).toHaveValue(IDXANA);
  expect(controls.getByLabelText("Continua se una riga fallisce")).not.toBeChecked();
  controls = panel("incass");
  expect(controls.getByLabelText("Limite soggetti")).toHaveValue("23");
  expect(controls.getByLabelText("Pausa richieste (ms)")).toHaveValue("321");
  expect(controls.getByLabelText("Salva dettaglio avviso")).not.toBeChecked();
  expect(controls.getByLabelText("Scarica ricevute PEC su NAS")).toBeChecked();
  expect(controls.getByLabelText("Continua se un soggetto fallisce")).not.toBeChecked();
}

function expectedPayloads(ids: CredentialIds) {
  return {
    terreni: {
      credential_id: ids.terreni, continue_on_error: false, fetch_certificati: false,
      fetch_details: false, double_speed: false, parallel_workers: 1, throttle_ms: 123,
      auto_resume: false, items: batchItems,
    },
    particelle: {
      credential_id: ids.particelle, only_due: false, limit: 12, fetch_certificati: true,
      fetch_details: false, double_speed: false, parallel_workers: 1,
    },
    history: {
      credential_id: ids.history, continue_on_error: false, auto_resume: true,
      items: [{ subject_id: SUBJECT, idxana: null }, { subject_id: null, idxana: IDXANA }],
    },
    incass: {
      credential_id: ids.incass, limit: 23, include_details: false, include_partitario: true,
      include_mailing_list: true, download_mailing_receipts: true, continue_on_error: false, throttle_ms: 321,
    },
  };
}

async function submitAll(ids: CredentialIds, call = 1) {
  const expected = expectedPayloads(ids);
  for (const family of families) {
    const otherListCounts = families.map((other) => listMocks[other].mock.calls.length);
    const previousLists = listMocks[family].mock.calls.length;
    fireEvent.click(panel(family).getByRole("button", { name: panels[family].submit }));
    expect(createMocks[family]).toHaveBeenCalledTimes(call);
    expect(createMocks[family]).toHaveBeenNthCalledWith(call, "session-token", expected[family]);
    expect(createMocks[family].mock.calls[call - 1][1]).toStrictEqual(expected[family]);
    await waitFor(() => expect(listMocks[family]).toHaveBeenCalledTimes(previousLists + 1));
    for (const [index, other] of families.entries()) {
      if (other !== family) expect(listMocks[other]).toHaveBeenCalledTimes(otherListCounts[index]);
    }
    expect(listMocks[family]).toHaveBeenLastCalledWith(
      ...(family === "incass" ? ["session-token", { limit: 300 }] : ["session-token"]),
    );
    expect(createMocks[family].mock.invocationCallOrder[call - 1]).toBeLessThan(
      listMocks[family].mock.invocationCallOrder[previousLists],
    );
    await waitFor(() => expect(screen.getByRole("button", { name: panels[family].submit })).toBeEnabled());
    const messages = {
      terreni: "Job batch #160 creato con 1 righe in velocita standard e 1 worker · pausa 123ms.",
      particelle: "Job progressivo particelle #161 creato in velocita standard con 1 worker e avviato in background.",
      history: "Job storico #162 creato con 2 righe e avviato in background.",
      incass: "Job avvisi #163 creato e avviato in background.",
    };
    expect(screen.getByText(messages[family])).toBeVisible();
  }
  assertOtherFields();
}

beforeEach(() => {
  vi.resetAllMocks();
  mocks.token.mockReturnValue("session-token");
  mocks.credentials.mockResolvedValue([]);
  mocks.authError.mockReturnValue(false);
  for (const family of families) {
    listMocks[family].mockResolvedValue([]);
    createMocks[family].mockResolvedValue({ id: 160 + families.indexOf(family) });
  }
});

afterEach(() => { cleanup(); vi.useRealTimers(); });

describe("R16 ORIGINAL public UI credential defaults and four create payloads", () => {
  test.each([
    { name: "empty", pool: [], count: "0/0", ids: { terreni: undefined, particelle: undefined, history: undefined, incass: undefined } },
    { name: "multiple, including inactive", pool: [credential(7, false), credential(8)], count: "1/2", ids: { terreni: undefined, particelle: undefined, history: undefined, incass: undefined } },
    { name: "active singleton", pool: [credential(9)], count: "1/1", ids: { terreni: 9, particelle: 9, history: 9, incass: 9 } },
    { name: "inactive singleton", pool: [credential(9, false)], count: "0/1", ids: { terreni: 9, particelle: 9, history: 9, incass: 9 } },
  ])("delayed initial $name preserves pending edits and all four exact payloads", async ({ pool, count, ids }) => {
    const pending = deferred<CapacitasCredential[]>();
    mocks.credentials.mockReturnValueOnce(pending.promise);
    await mount();
    for (const family of families) expect(selection(family)).toHaveValue("");
    await editOtherFields();
    expect(screen.getByText("0/0")).toBeInTheDocument();
    for (const family of families) expect(createMocks[family]).not.toHaveBeenCalled();
    await act(async () => pending.resolve(pool));
    expect(screen.getByText(count)).toBeInTheDocument();
    for (const family of families) {
      const control = selection(family);
      expect(control).toHaveValue(ids[family] === undefined ? "" : "9");
      expect(within(control).getAllByRole("option")).toHaveLength(pool.length + 1);
      for (const account of pool) {
        expect(within(control).getByRole("option", { name: `Account ${account.id} · operator-${account.id}` })).toBeEnabled();
      }
    }
    assertOtherFields();
    const harvest = screen.getByRole("navigation", { name: "Sezioni Capacitas" });
    fireEvent.click(within(harvest).getByRole("button", { name: /^Storico anagrafico/ }));
    const harvestPanel = screen.getByText("Crea job massivi inCass dai soggetti a ruolo").closest("article")!;
    expect(within(harvestPanel).getByRole("combobox", { name: "Credenziale" })).toHaveValue("");
    await submitAll(ids);
    expect(mocks.credentials).toHaveBeenCalledExactlyOnceWith("session-token");
  });

  test.each([
    { name: "Terreni and history selected", selected: ["terreni", "history"] as Family[], ids: { terreni: 7, particelle: 9, history: 8, incass: 9 } },
    { name: "particelle and inCass selected", selected: ["particelle", "incass"] as Family[], ids: { terreni: 9, particelle: 7, history: 9, incass: 8 } },
  ])("mixed deferred singleton: $name retains missing IDs in payloads and fills only empty forms", async ({ selected, ids }) => {
    const replay = deferred<CapacitasCredential[]>();
    mocks.credentials.mockResolvedValueOnce([credential(7), credential(8)]).mockReturnValueOnce(replay.promise);
    await mount(true);
    await screen.findByText("2/2");
    select(selected[0], "7");
    select(selected[1], "8");
    for (const family of families.filter((family) => !selected.includes(family))) {
      expect(selection(family)).toHaveValue("");
    }
    await editOtherFields();
    await act(async () => replay.resolve([credential(9, false)]));
    expect(screen.getByText("0/1")).toBeInTheDocument();
    for (const family of families) {
      const control = selection(family);
      expect(within(control).queryByRole("option", { name: "Account 7 · operator-7" })).not.toBeInTheDocument();
      expect(within(control).queryByRole("option", { name: "Account 8 · operator-8" })).not.toBeInTheDocument();
      // React displays the fallback option for an absent controlled value.
      // Only the actual create payload below can demonstrate retained form state.
      expect(control).toHaveValue(selected.includes(family) ? "" : "9");
    }
    assertOtherFields();
    await submitAll(ids);
    expect(mocks.credentials).toHaveBeenNthCalledWith(1, "session-token");
    expect(mocks.credentials).toHaveBeenNthCalledWith(2, "session-token");
    expect(mocks.credentials).toHaveBeenCalledTimes(2);
  });

  test.each([
    { name: "empty replacement", pool: [], count: "0/0" },
    { name: "multiple absent replacement", pool: [credential(10), credential(11, false)], count: "1/2" },
  ])("$name retains selected IDs while empty forms stay automatic", async ({ pool, count }) => {
    const replay = deferred<CapacitasCredential[]>();
    mocks.credentials.mockResolvedValueOnce([credential(7), credential(8)]).mockReturnValueOnce(replay.promise);
    await mount(true);
    await screen.findByText("2/2");
    select("terreni", "7");
    select("incass", "8");
    await editOtherFields();
    await act(async () => replay.resolve(pool));
    expect(screen.getByText(count)).toBeInTheDocument();
    for (const family of families) expect(selection(family)).toHaveValue("");
    await submitAll({ terreni: 7, particelle: undefined, history: undefined, incass: 8 });
    expect(mocks.credentials).toHaveBeenCalledTimes(2);
  });

  test("latest selection and clear during pending replay determine the four payloads", async () => {
    const replay = deferred<CapacitasCredential[]>();
    mocks.credentials.mockResolvedValueOnce([credential(7), credential(8)]).mockReturnValueOnce(replay.promise);
    await mount(true);
    await screen.findByText("2/2");
    for (const family of families) select(family, "7");
    await editOtherFields();
    select("terreni", "8");
    select("particelle", "");
    select("history", "8");
    select("incass", "");
    await act(async () => replay.resolve([credential(9)]));
    await submitAll({ terreni: 8, particelle: 9, history: 8, incass: 9 });
    // Selecting automatic after completion does not reapply the singleton default.
    select("particelle", "");
    select("incass", "");
    await submitAll({ terreni: 8, particelle: undefined, history: 8, incass: undefined }, 2);
    expect(mocks.credentials).toHaveBeenCalledTimes(2);
  });

  test("all four creates capture automatic IDs before the singleton resolves; later creates use its ID", async () => {
    const pending = deferred<CapacitasCredential[]>();
    const creates = {
      terreni: deferred<{ id: number }>(), particelle: deferred<{ id: number }>(),
      history: deferred<{ id: number }>(), incass: deferred<{ id: number }>(),
    };
    mocks.credentials.mockReturnValueOnce(pending.promise);
    await mount();
    await editOtherFields();
    const automatic = expectedPayloads({ terreni: undefined, particelle: undefined, history: undefined, incass: undefined });
    for (const family of families) {
      createMocks[family].mockReturnValueOnce(creates[family].promise);
      fireEvent.click(panel(family).getByRole("button", { name: panels[family].submit }));
      expect(createMocks[family]).toHaveBeenCalledExactlyOnceWith("session-token", automatic[family]);
      expect(createMocks[family].mock.calls[0][1]).toStrictEqual(automatic[family]);
      expect(listMocks[family]).toHaveBeenCalledTimes(1);
      expect(panel(family).getByRole("button", { name: family === "history" ? "Import in corso..." : "Avvio..." })).toBeDisabled();
    }
    await act(async () => pending.resolve([credential(9)]));
    for (const family of families) {
      expect(selection(family)).toHaveValue("9");
      expect(createMocks[family]).toHaveBeenCalledExactlyOnceWith("session-token", automatic[family]);
      expect(createMocks[family].mock.calls[0][1]).toStrictEqual(automatic[family]);
      expect(listMocks[family]).toHaveBeenCalledTimes(1);
    }
    assertOtherFields();
    for (const family of families) {
      await act(async () => creates[family].resolve({ id: 160 + families.indexOf(family) }));
      await waitFor(() => expect(listMocks[family]).toHaveBeenCalledTimes(2));
      expect(panel(family).getByRole("button", { name: panels[family].submit })).toBeEnabled();
    }
    await submitAll({ terreni: 9, particelle: 9, history: 9, incass: 9 }, 2);
    expect(mocks.credentials).toHaveBeenCalledExactlyOnceWith("session-token");
  });

  test.each([
    { failure: new Error("R16 credential outage"), message: "R16 credential outage" },
    { failure: "R16 non-Error rejection", message: "Errore caricamento credenziali Capacitas" },
  ])("delayed failure preserves latest form edits and selected payloads: $message", async ({ failure, message }) => {
    const replay = deferred<CapacitasCredential[]>();
    mocks.credentials.mockResolvedValueOnce([credential(7), credential(8)]).mockReturnValueOnce(replay.promise);
    await mount(true);
    await screen.findByText("2/2");
    select("terreni", "7");
    select("history", "8");
    await editOtherFields();
    await act(async () => replay.reject(failure));
    expect(screen.getByText("Errore operativo")).toBeInTheDocument();
    expect(screen.getAllByText(message).length).toBeGreaterThan(0);
    expect(screen.getByText("2/2")).toBeInTheDocument();
    expect(selection("terreni")).toHaveValue("7");
    expect(selection("history")).toHaveValue("8");
    expect(selection("particelle")).toHaveValue("");
    expect(selection("incass")).toHaveValue("");
    await submitAll({ terreni: 7, particelle: undefined, history: 8, incass: undefined });
    expect(mocks.credentials).toHaveBeenCalledTimes(2);
  });

  test("missing token skips credential loading and all four prepared public creates", async () => {
    mocks.token.mockReturnValue(null);
    render(<ElaborazioniCapacitasWorkspace embedded />);
    await act(async () => {});
    await editOtherFields();
    for (const family of families) {
      expect(selection(family)).toHaveValue("");
      fireEvent.click(panel(family).getByRole("button", { name: panels[family].submit }));
      expect(createMocks[family]).not.toHaveBeenCalled();
      expect(listMocks[family]).not.toHaveBeenCalled();
    }
    expect(mocks.credentials).not.toHaveBeenCalled();
    expect(screen.getByText("0/0")).toBeInTheDocument();
    assertOtherFields();
  });
});
