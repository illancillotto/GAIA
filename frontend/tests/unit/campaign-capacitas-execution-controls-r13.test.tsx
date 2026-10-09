import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { ElaborazioniCapacitasWorkspace } from "@/components/elaborazioni/capacitas-workspace";
import type {
  CapacitasParticelleSyncJob,
  CapacitasParticelleSyncJobCreateInput,
  CapacitasTerreniJob,
  CapacitasTerreniJobCreateInput,
} from "@/types/api";

type Family = "terreni" | "particelle";
type Kind = "speed" | "parallel";

const mocks = vi.hoisted(() => ({
  token: vi.fn(),
  credentials: vi.fn(),
  terreni: vi.fn(),
  particelle: vi.fn(),
  history: vi.fn(),
  incass: vi.fn(),
  createTerreni: vi.fn<(token: string, input: CapacitasTerreniJobCreateInput) => Promise<CapacitasTerreniJob>>(),
  createParticelle: vi.fn<(token: string, input: CapacitasParticelleSyncJobCreateInput) => Promise<CapacitasParticelleSyncJob>>(),
}));

vi.mock("@/lib/auth", async (importOriginal) => ({
  ...await importOriginal<typeof import("@/lib/auth")>(),
  getStoredAccessToken: mocks.token,
}));
vi.mock("@/lib/api", async (importOriginal) => ({
  ...await importOriginal<typeof import("@/lib/api")>(),
  listCapacitasCredentials: mocks.credentials,
  listCapacitasTerreniJobs: mocks.terreni,
  listCapacitasParticelleSyncJobs: mocks.particelle,
  listCapacitasAnagraficaHistoryJobs: mocks.history,
  listCapacitasInCassSyncJobs: mocks.incass,
  createCapacitasTerreniJob: mocks.createTerreni,
  createCapacitasParticelleSyncJob: mocks.createParticelle,
}));

const families: Family[] = ["terreni", "particelle"];
const kinds: Kind[] = ["speed", "parallel"];
const configurations = [
  { speed: false, parallel: false },
  { speed: true, parallel: false },
  { speed: false, parallel: true },
  { speed: true, parallel: true },
];
const inactiveClass = "rounded-lg border border-gray-100 bg-gray-50 px-4 py-3 text-left text-sm font-semibold text-gray-700 transition hover:border-[#1D4E35]/30 hover:bg-[#f5faf5]";
const activeClass = "rounded-lg border border-[#1D4E35] bg-[#eef7ef] px-4 py-3 text-left text-sm font-semibold text-[#1D4E35]";
const descriptionClass = "mt-1 block text-xs font-normal text-gray-500";
const descriptions = {
  terreni: {
    speed: ["Usa una pausa piu aggressiva tra richieste e righe.", "Riduce la pausa automatica del job Terreni."],
    parallel: ["Divide il batch su due worker concorrenti.", "Apre 2 sessioni Capacitas dedicate per il job."],
  },
  particelle: {
    speed: ["Porta la pausa diurna da 900ms a 450ms.", "Pausa dimezzata per questo job."],
    parallel: ["Divide il job su 2 worker.", "Usa 2 sessioni Capacitas dedicate."],
  },
};
const batchItems = [{ label: "Uras 1/680", comune: "Uras", foglio: "1", particella: "680", sezione: "", sub: "" }];

function terreniJob(id = 91): CapacitasTerreniJob {
  return {
    id, credential_id: 7, requested_by_user_id: null, status: "pending", mode: "batch",
    payload_json: null, result_json: null, error_detail: null, started_at: null,
    completed_at: null, created_at: "2026-10-09T12:00:00Z", updated_at: "2026-10-09T12:00:00Z",
  };
}

function particelleJob(id = 92): CapacitasParticelleSyncJob {
  return {
    id, credential_id: 8, requested_by_user_id: null, status: "pending", mode: "progressive",
    payload_json: null, result_json: null, error_detail: null, started_at: null,
    completed_at: null, created_at: "2026-10-09T12:00:00Z", updated_at: "2026-10-09T12:00:00Z",
  };
}

function deferred<Value>() {
  let resolve!: (value: Value) => void;
  const promise = new Promise<Value>((fulfill) => { resolve = fulfill; });
  return { promise, resolve };
}

function control(kind: Kind): HTMLButtonElement {
  return screen.getByRole<HTMLButtonElement>("button", { name: kind === "speed" ? /^Doppia velocita/ : /^Parallelo x2/ });
}

function assertControl(family: Family, kind: Kind, active: boolean) {
  const button = control(kind);
  const title = kind === "speed"
    ? active ? "Doppia velocita attiva" : "Doppia velocita"
    : active ? "Parallelo x2 attivo" : "Parallelo x2";
  const description = descriptions[family][kind][active ? 1 : 0];
  expect(button.tagName).toBe("BUTTON");
  expect(button).toHaveAttribute("type", "button");
  expect(button.className).toBe(active ? activeClass : inactiveClass);
  expect(button).toBeEnabled();
  for (const attribute of ["disabled", "aria-pressed", "tabindex"]) {
    expect(button).not.toHaveAttribute(attribute);
  }
  expect(button.childNodes).toHaveLength(2);
  expect(Array.from(button.children, (child) => child.tagName)).toEqual(["SPAN", "SPAN"]);
  expect(button.children[0].className).toBe("block");
  expect(button.children[0].textContent).toBe(title);
  expect(button.children[1].className).toBe(descriptionClass);
  expect(button.children[1].textContent).toBe(description);
  expect(button).toHaveAccessibleName(`${title}${description}`);
}

function assertOptions(family: Family, speed: boolean, parallel: boolean) {
  assertControl(family, "speed", speed);
  assertControl(family, "parallel", parallel);
  const speedButton = control("speed");
  const parallelButton = control("parallel");
  const grid = speedButton.parentElement!;
  expect(parallelButton.parentElement).toBe(grid);
  expect(speedButton.nextElementSibling).toBe(parallelButton);
  if (family === "terreni") {
    expect(grid.className).toBe("grid gap-4 xl:grid-cols-4");
    expect(Array.from(grid.children)).toEqual([
      speedButton, parallelButton, screen.getByLabelText(/^Pausa richieste \(ms\)/).closest("label"),
      screen.getByRole("button", { name: /^Auto-resume/ }),
    ]);
  } else {
    expect(grid.className).toBe("grid gap-4 md:grid-cols-2 xl:grid-cols-7");
    expect(Array.from(grid.children)).toEqual([
      screen.getByLabelText("Credenziale").closest("label"), screen.getByLabelText("Limite run").closest("label"),
      screen.getByLabelText("Solo particelle dovute").closest("label"), screen.getByLabelText("Scarica certificati").closest("label"),
      screen.getByLabelText("Scarica dettagli").closest("label"), speedButton, parallelButton,
    ]);
  }
}

async function mount(family: Family) {
  render(<ElaborazioniCapacitasWorkspace embedded initialSection={family} />);
  await screen.findByText(family === "terreni" ? "Nessun job registrato" : "Nessun job particelle registrato");
  await screen.findByRole("option", { name: "Operatore Particelle · particelle" });
  expect(screen.getByLabelText("Credenziale")).toHaveValue("");
}

function selectFamily(family: Family) {
  fireEvent.click(screen.getByRole("button", { name: family === "terreni" ? /^Terreni batch/ : /^Sync particelle/ }));
}

async function prepare(family: Family) {
  fireEvent.change(screen.getByLabelText("Credenziale"), { target: { value: family === "terreni" ? "7" : "8" } });
  fireEvent.click(screen.getByLabelText("Scarica certificati"));
  if (family === "terreni") {
    fireEvent.click(screen.getByLabelText("Continua se una riga fallisce"));
    fireEvent.click(screen.getByLabelText("Scarica dettagli terreno"));
    fireEvent.change(screen.getByLabelText(/^Pausa richieste \(ms\)/), { target: { value: "123" } });
    fireEvent.click(screen.getByRole("button", { name: /^Auto-resume/ }));
    const contents = "comune,foglio,particella\nUras,1,680";
    const file = new File([contents], "terreni.csv", { type: "text/csv" });
    Object.defineProperty(file, "text", { value: () => Promise.resolve(contents) });
    fireEvent.change(screen.getByLabelText("File batch"), { target: { files: [file] } });
    await waitFor(() => expect(submitButton(family)).toBeEnabled());
  } else {
    fireEvent.click(screen.getByLabelText("Solo particelle dovute"));
    fireEvent.click(screen.getByLabelText("Scarica dettagli"));
    fireEvent.change(screen.getByLabelText("Limite run"), { target: { value: " 12 " } });
  }
}

function assertPrepared(family: Family) {
  expect(screen.getByLabelText("Credenziale")).toHaveValue(family === "terreni" ? "7" : "8");
  expect(screen.getByLabelText("Scarica certificati")).not.toBeChecked();
  if (family === "terreni") {
    expect(screen.getByLabelText("Continua se una riga fallisce")).not.toBeChecked();
    expect(screen.getByLabelText("Scarica dettagli terreno")).not.toBeChecked();
    expect(screen.getByLabelText(/^Pausa richieste \(ms\)/)).toHaveValue("123");
    expect(screen.getByRole("button", { name: /^Auto-resume attivo/ })).toBeEnabled();
    expect(screen.getByText("terreni.csv")).toBeVisible();
    expect(submitButton(family)).toBeEnabled();
  } else {
    expect(screen.getByLabelText("Solo particelle dovute")).not.toBeChecked();
    expect(screen.getByLabelText("Scarica dettagli")).not.toBeChecked();
    expect(screen.getByLabelText("Limite run")).toHaveValue(" 12 ");
  }
}

function setOptions(speed: boolean, parallel: boolean) {
  if (speed) fireEvent.click(control("speed"));
  if (parallel) fireEvent.click(control("parallel"));
}

function submitButton(family: Family) {
  return screen.getByRole("button", { name: family === "terreni" ? "Avvia job batch" : "Avvia sync progressiva" });
}

function createMock(family: Family) {
  return family === "terreni" ? mocks.createTerreni : mocks.createParticelle;
}

function listMock(family: Family) {
  return family === "terreni" ? mocks.terreni : mocks.particelle;
}

function payload(family: Family, speed: boolean, parallel: boolean) {
  const execution = { fetch_certificati: false, fetch_details: false, double_speed: speed, parallel_workers: parallel ? 2 : 1 };
  return family === "terreni"
    ? { credential_id: 7, continue_on_error: false, ...execution, throttle_ms: 123, auto_resume: true, items: batchItems }
    : { credential_id: 8, only_due: false, limit: 12, ...execution };
}

function confirmation(family: Family, speed: boolean, parallel: boolean) {
  const velocity = speed ? "doppia velocita" : "velocita standard";
  const workers = parallel ? 2 : 1;
  return family === "terreni"
    ? `Job batch #91 creato con 1 righe in ${velocity} e ${workers} worker · pausa 123ms · auto-resume attivo.`
    : `Job progressivo particelle #92 creato in ${velocity} con ${workers} worker e avviato in background.`;
}

async function submitAndAssert(family: Family, speed: boolean, parallel: boolean, call = 1) {
  fireEvent.click(submitButton(family));
  expect(createMock(family)).toHaveBeenCalledTimes(call);
  expect(createMock(family)).toHaveBeenNthCalledWith(call, "session-token", payload(family, speed, parallel));
  expect(await screen.findByText(confirmation(family, speed, parallel))).toBeVisible();
  await waitFor(() => expect(submitButton(family)).toBeEnabled());
}

beforeEach(() => {
  vi.resetAllMocks();
  mocks.token.mockReturnValue("session-token");
  mocks.credentials.mockResolvedValue([
    { id: 7, label: "Operatore Terreni", username: "terreni", active: true },
    { id: 8, label: "Operatore Particelle", username: "particelle", active: true },
  ]);
  for (const list of [mocks.terreni, mocks.particelle, mocks.history, mocks.incass]) list.mockResolvedValue([]);
  mocks.createTerreni.mockResolvedValue(terreniJob());
  mocks.createParticelle.mockResolvedValue(particelleJob());
});

afterEach(() => { cleanup(); });

describe.each(families)("R13 original %s public execution controls", (family) => {
  test.each(configurations)("preserves exact native DOM and payload with speed=$speed parallel=$parallel", async ({ speed, parallel }) => {
    await mount(family);
    await prepare(family);
    setOptions(speed, parallel);
    assertOptions(family, speed, parallel);
    assertPrepared(family);
    await submitAndAssert(family, speed, parallel);
    assertOptions(family, speed, parallel);
    assertPrepared(family);
    expect(createMock(family === "terreni" ? "particelle" : "terreni")).not.toHaveBeenCalled();
  });

  test.each(kinds)("composes two %s clicks queued before the same render without losing the other option", async (kind) => {
    await mount(family);
    await prepare(family);
    fireEvent.click(control(kind === "speed" ? "parallel" : "speed"));
    const button = control(kind);
    const originalTitle = button.children[0].textContent;
    act(() => {
      button.dispatchEvent(new MouseEvent("click", { bubbles: true }));
      expect(button.children[0].textContent).toBe(originalTitle);
      button.dispatchEvent(new MouseEvent("click", { bubbles: true }));
      expect(button.children[0].textContent).toBe(originalTitle);
    });
    const speed = kind === "parallel";
    const parallel = kind === "speed";
    assertOptions(family, speed, parallel);
    assertPrepared(family);
    await submitAndAssert(family, speed, parallel);
  });

  test("retains captured create options while pending edits change the UI and the next payload", async () => {
    await mount(family);
    await prepare(family);
    setOptions(true, true);
    const pendingTerreni = deferred<CapacitasTerreniJob>();
    const pendingParticelle = deferred<CapacitasParticelleSyncJob>();
    if (family === "terreni") mocks.createTerreni.mockReturnValueOnce(pendingTerreni.promise);
    else mocks.createParticelle.mockReturnValueOnce(pendingParticelle.promise);
    fireEvent.click(submitButton(family));
    expect(createMock(family)).toHaveBeenCalledExactlyOnceWith("session-token", payload(family, true, true));
    expect(screen.getByRole("button", { name: "Avvio..." })).toBeDisabled();
    assertOptions(family, true, true);
    fireEvent.click(control("speed"));
    fireEvent.click(control("parallel"));
    assertOptions(family, false, false);
    expect(createMock(family)).toHaveBeenCalledExactlyOnceWith("session-token", payload(family, true, true));
    expect(listMock(family)).toHaveBeenCalledTimes(1);
    expect(screen.queryByText(confirmation(family, true, true))).not.toBeInTheDocument();
    await act(async () => {
      if (family === "terreni") pendingTerreni.resolve(terreniJob());
      else pendingParticelle.resolve(particelleJob());
    });
    expect(await screen.findByText(confirmation(family, true, true))).toBeVisible();
    expect(listMock(family)).toHaveBeenCalledTimes(2);
    expect(listMock(family)).toHaveBeenNthCalledWith(2, "session-token");
    expect(listMock(family).mock.invocationCallOrder[1]).toBeGreaterThan(createMock(family).mock.invocationCallOrder[0]);
    assertOptions(family, false, false);
    assertPrepared(family);
    await submitAndAssert(family, false, false, 2);
    expect(createMock(family)).toHaveBeenNthCalledWith(1, "session-token", payload(family, true, true));
    expect(listMock(family)).toHaveBeenCalledTimes(3);
    assertOptions(family, false, false);
  });
});

describe("R13 original cross-family execution persistence", () => {
  test.each(families)("keeps independent selections and unrelated fields when starting from %s", async (first) => {
    const second = first === "terreni" ? "particelle" : "terreni";
    await mount(first);
    await prepare(first);
    setOptions(first === "terreni", first === "particelle");
    selectFamily(second);
    assertOptions(second, false, false);
    await prepare(second);
    setOptions(second === "terreni", second === "particelle");
    selectFamily(first);
    assertOptions(first, first === "terreni", first === "particelle");
    assertPrepared(first);
    await submitAndAssert(first, first === "terreni", first === "particelle");
    expect(createMock(second)).not.toHaveBeenCalled();
    selectFamily(second);
    assertOptions(second, second === "terreni", second === "particelle");
    assertPrepared(second);
    await submitAndAssert(second, second === "terreni", second === "particelle");
    expect(createMock(first)).toHaveBeenCalledTimes(1);
    selectFamily(first);
    assertOptions(first, first === "terreni", first === "particelle");
    assertPrepared(first);
  });
});
