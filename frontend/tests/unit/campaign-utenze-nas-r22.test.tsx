import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import UtenzeSubjectDetailPage from "@/app/utenze/[id]/page";
import type {
  AnagraficaNasFolderCandidate,
  AnagraficaSubjectDetail,
  AnagraficaSubjectImportResult,
  AnagraficaSubjectNasImportStatus,
  AnagraficaSubjectUpdateInput,
} from "@/types/api";

const api = vi.hoisted(() => ({
  subjectId: "subject-1",
  router: { push: vi.fn(), replace: vi.fn() },
  getStoredAccessToken: vi.fn(),
  getCurrentUser: vi.fn(),
  getMyPermissions: vi.fn(),
  getUtenzeSubject: vi.fn(),
  getUtenzeSubjectPaymentNotices: vi.fn(),
  getUtenzeSubjectNasImportStatus: vi.fn(),
  getUtenzeSubjectNasCandidates: vi.fn(),
  importUtenzeSubjectFromNas: vi.fn(),
  updateUtenzeSubject: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useParams: () => ({ id: api.subjectId }),
  useRouter: () => api.router,
  useSearchParams: () => new URLSearchParams(window.location.search),
}));
vi.mock("@/lib/auth", () => ({
  getStoredAccessToken: api.getStoredAccessToken,
  clearStoredAccessToken: vi.fn(),
}));
vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  getCurrentUser: api.getCurrentUser,
  getMyPermissions: api.getMyPermissions,
  getUtenzeSubject: api.getUtenzeSubject,
  getUtenzeSubjectPaymentNotices: api.getUtenzeSubjectPaymentNotices,
  getUtenzeSubjectNasImportStatus: api.getUtenzeSubjectNasImportStatus,
  getUtenzeSubjectNasCandidates: api.getUtenzeSubjectNasCandidates,
  importUtenzeSubjectFromNas: api.importUtenzeSubjectFromNas,
  updateUtenzeSubject: api.updateUtenzeSubject,
}));
vi.mock("@/components/layout/app-shell", () => ({
  AppShell: ({ children }: { children: ReactNode }) => <main>{children}</main>,
}));
vi.mock("@/components/layout/topbar", () => ({ Topbar: () => <header /> }));
vi.mock("@/components/anagrafica/AnprStatusCard", () => ({ AnprStatusCard: () => null }));
vi.mock("@/components/utenze/utenze-subject-visura-card", () => ({ UtenzeSubjectVisuraCard: () => null }));
vi.mock("@/components/utenze/utenze-meter-readings-section", () => ({
  UtenzeMeterReadingsSection: () => <section>Letture NAS fixture</section>,
}));
vi.mock("@/components/utenze/utenze-payment-notices-section", () => ({ UtenzePaymentNoticesSection: () => null }));
vi.mock("@/components/utenze/utenze-terreni-colture-section", () => ({ UtenzeTerreniColtureSection: () => null }));
vi.mock("@/components/utenze/utenze-domande-irrigue-section", () => ({ UtenzeDomandeIrrigueSection: () => null }));

function subjectFixture(overrides: Partial<AnagraficaSubjectDetail> = {}): AnagraficaSubjectDetail {
  return {
    id: "subject-1", subject_type: "person", status: "active", source_system: "campaign-r22",
    source_external_id: null, source_name_raw: "Rossi Mario", nas_folder_path: null,
    nas_folder_letter: null, requires_review: false, imported_at: null,
    created_at: "2026-10-11T00:00:00Z", updated_at: "2026-10-11T00:00:00Z",
    person: {
      subject_id: overrides.id ?? "subject-1", cognome: "Rossi", nome: "Mario", codice_fiscale: "RSSMRA80A01H501U",
      anpr_id: null, stato_anpr: null, data_decesso: null, luogo_decesso_comune: null,
      last_anpr_check_at: null, last_c030_check_at: null, data_nascita: null, comune_nascita: null,
      indirizzo: null, comune_residenza: null, cap: null, email: null, telefono: null, note: null,
      created_at: "2026-10-11T00:00:00Z", updated_at: "2026-10-11T00:00:00Z",
    },
    company: null, documents: [], audit_log: [], catasto_documents: [], ...overrides,
  };
}
function statusFixture(overrides: Partial<AnagraficaSubjectNasImportStatus> = {}): AnagraficaSubjectNasImportStatus {
  return {
    can_import_from_nas: true, missing_in_nas: false, matched_folder_path: "/archive/R/Rossi_Mario",
    matched_folder_name: "Rossi_Mario", total_files_in_nas: 5, pending_files_in_nas: 2,
    message: "NAS pronto", ...overrides,
  };
}
function candidateFixture(overrides: Partial<AnagraficaNasFolderCandidate> = {}): AnagraficaNasFolderCandidate {
  return {
    folder_name: "Prima cartella", letter: "R", nas_folder_path: "/archive/R/first",
    score: 80, subject_type: "person", confidence: 0.8, requires_review: false,
    codice_fiscale: "RSSMRA80A01H501U", partita_iva: null, ragione_sociale: null,
    cognome: "Rossi", nome: "Mario", ...overrides,
  };
}
const importResult: AnagraficaSubjectImportResult = {
  subject_id: "subject-1", matched_folder_path: "/archive/R/Rossi_Mario",
  matched_folder_name: "Rossi_Mario", warning_count: 0, created_documents: 2,
  updated_documents: 1, imported_at: "2026-10-11T00:01:00Z",
};
const importMessage = "Import NAS completato da Rossi_Mario: 2 documenti creati, 1 aggiornati.";
const pathMessage = "Percorso NAS salvato sulla scheda soggetto.";
const emptyCandidateMessage = "Nessuna cartella candidata caricata. Avvia la ricerca per vedere le opzioni trovate sul NAS.";

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}
async function resolveRequest<T>(request: ReturnType<typeof deferred<T>>, value: T) {
  await act(async () => { request.resolve(value); });
}
async function rejectRequest<T>(request: ReturnType<typeof deferred<T>>, reason: unknown) {
  await act(async () => { request.reject(reason); });
}
async function ready() {
  const view = render(<UtenzeSubjectDetailPage />);
  await screen.findByText("NAS pronto");
  await act(async () => {});
  return view;
}
function edit() {
  fireEvent.click(screen.getByRole("button", { name: "Modifica" }));
  fireEvent.click(screen.getByRole("button", { name: "Abilita modifica" }));
  expect(screen.getByText("Modalità modifica attiva")).toBeInTheDocument();
}
function pathInput() { return screen.getByLabelText("Percorso NAS selezionato"); }
function setPath(path: string) { fireEvent.change(pathInput(), { target: { value: path } }); }
function search() { fireEvent.click(screen.getByRole("button", { name: "Trova cartelle candidate" })); }
function savePath() { fireEvent.click(screen.getByRole("button", { name: "Salva percorso NAS" })); }
function headerImport() { return screen.getByRole("button", { name: "Aggiorna documenti" }); }
async function candidates(items: AnagraficaNasFolderCandidate[]) {
  api.getUtenzeSubjectNasCandidates.mockResolvedValueOnce(items);
  search();
  await waitFor(() => expect(screen.getByRole("button", { name: "Trova cartelle candidate" })).toBeEnabled());
}

beforeEach(() => {
  vi.resetAllMocks();
  api.subjectId = "subject-1";
  window.history.replaceState(null, "", "/utenze/subject-1");
  api.getStoredAccessToken.mockReturnValue("campaign-token");
  api.getCurrentUser.mockResolvedValue({ enabled_modules: ["utenze"], role: "viewer" });
  api.getMyPermissions.mockResolvedValue({ granted_keys: [] });
  api.getUtenzeSubject.mockImplementation(async (_token: string, id: string) => subjectFixture({ id }));
  api.getUtenzeSubjectPaymentNotices.mockResolvedValue([]);
  api.getUtenzeSubjectNasImportStatus.mockImplementation(async () => statusFixture());
  api.getUtenzeSubjectNasCandidates.mockResolvedValue([]);
  api.importUtenzeSubjectFromNas.mockResolvedValue(importResult);
  api.updateUtenzeSubject.mockImplementation(async (_token: string, _id: string, input: AnagraficaSubjectUpdateInput) => subjectFixture({
    id: _id, nas_folder_path: input.nas_folder_path ?? null, nas_folder_letter: input.nas_folder_letter ?? null,
  }));
});
afterEach(() => cleanup());

describe("R22 mounted NAS status and visibility", () => {
  test("status follows subject resolution without blocking the visible subject", async () => {
    const subject = deferred<AnagraficaSubjectDetail>();
    const status = deferred<AnagraficaSubjectNasImportStatus>();
    api.getUtenzeSubject.mockReturnValueOnce(subject.promise);
    api.getUtenzeSubjectNasImportStatus.mockReturnValueOnce(status.promise);
    render(<UtenzeSubjectDetailPage />);
    await screen.findByText("Caricamento scheda soggetto.");
    expect(api.getUtenzeSubjectNasImportStatus).not.toHaveBeenCalled();
    await resolveRequest(subject, subjectFixture());
    expect(screen.getByText("Rossi Mario")).toBeInTheDocument();
    expect(api.getUtenzeSubjectNasImportStatus.mock.calls).toEqual([["campaign-token", "subject-1"]]);
    expect(screen.queryByText("Stato import NAS")).not.toBeInTheDocument();
    await resolveRequest(status, statusFixture());
    expect(headerImport()).toBeEnabled();
    expect(screen.getByText("Rossi_Mario")).toBeInTheDocument();
    expect(screen.getByText("/archive/R/Rossi_Mario")).toBeInTheDocument();
  });

  test.each([
    [true, 2, true], [true, 0, false], [true, -1, false], [false, 2, false],
  ])("read-only eligibility can=%s pending=%s and edit header", async (canImport, pending, quick) => {
    api.getUtenzeSubjectNasImportStatus.mockResolvedValue(statusFixture({ can_import_from_nas: canImport, pending_files_in_nas: pending }));
    await ready();
    expect(screen.queryByRole("button", { name: "Aggiorna documenti" }) !== null).toBe(quick);
    expect(screen.queryByRole("button", { name: `Aggiorna documenti (${pending})` }) !== null).toBe(quick);
    edit();
    expect(screen.queryByRole("button", { name: "Aggiorna documenti" }) !== null).toBe(canImport);
    expect(screen.queryByRole("button", { name: "Nessun dato rilevato nel NAS, importa manualmente" }) !== null).toBe(!canImport);
  });

  test("boundary null pending falls back to zero but edit import remains available", async () => {
    api.getUtenzeSubjectNasImportStatus.mockResolvedValue({ ...statusFixture(), pending_files_in_nas: null });
    await ready();
    expect(screen.queryByRole("button", { name: /Aggiorna documenti/ })).not.toBeInTheDocument();
    edit();
    expect(headerImport()).toBeEnabled();
  });

  test("missing-in-NAS flag does not independently suppress an eligible import", async () => {
    api.getUtenzeSubjectNasImportStatus.mockResolvedValue(statusFixture({ missing_in_nas: true }));
    await ready();
    expect(headerImport()).toBeEnabled();
    expect(screen.getByRole("button", { name: "Aggiorna documenti (2)" })).toBeEnabled();
  });

  test.each([
    [new Error("NAS status offline"), "NAS status offline"], ["bad status", "Verifica NAS non disponibile"],
  ])("status rejection keeps subject and renders fail-closed summary: %s", async (error, message) => {
    api.getUtenzeSubjectNasImportStatus.mockRejectedValue(error);
    render(<UtenzeSubjectDetailPage />);
    await screen.findByText(message);
    expect(screen.getByText("Rossi Mario")).toBeInTheDocument();
    expect(screen.getByText("Non disponibile")).toBeInTheDocument();
    const card = screen.getByText("Stato import NAS").closest("article")!;
    expect(within(card).getAllByText("0")).toHaveLength(2);
    expect(screen.queryByRole("button", { name: /Aggiorna documenti/ })).not.toBeInTheDocument();
  });

  test("Scheda controls disappear on another tab while header import remains", async () => {
    await ready();
    fireEvent.click(screen.getByRole("button", { name: "Letture contatori" }));
    expect(headerImport()).toBeEnabled();
    expect(screen.queryByText("Stato import NAS")).not.toBeInTheDocument();
    expect(screen.queryByText("Override cartella NAS")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Scheda soggetto" }));
    expect(screen.getByRole("button", { name: "Aggiorna documenti (2)" })).toBeEnabled();
    expect(screen.getByText("Override cartella NAS")).toBeInTheDocument();
  });
});

describe("R22 mounted NAS import orchestration", () => {
  test.each(["header", "status card"])("%s action sends only token/id and refreshes subject/status", async (control) => {
    await ready();
    edit();
    setPath("/unsaved/path-not-an-import-argument");
    const pending = deferred<AnagraficaSubjectImportResult>();
    api.importUtenzeSubjectFromNas.mockReturnValueOnce(pending.promise);
    fireEvent.click(control === "header" ? headerImport() : screen.getByRole("button", { name: "Aggiorna documenti (2)" }));
    expect(api.importUtenzeSubjectFromNas.mock.calls).toEqual([["campaign-token", "subject-1"]]);
    expect(screen.getAllByRole("button", { name: "Aggiornamento..." })).toHaveLength(2);
    for (const button of screen.getAllByRole("button", { name: "Aggiornamento..." })) expect(button).toBeDisabled();
    expect(api.getUtenzeSubject).toHaveBeenCalledTimes(1);
    await resolveRequest(pending, importResult);
    await screen.findByText(importMessage);
    expect(api.getUtenzeSubject.mock.calls).toEqual([["campaign-token", "subject-1"], ["campaign-token", "subject-1"]]);
    expect(api.getUtenzeSubjectNasImportStatus.mock.calls).toEqual(Array.from({ length: 3 }, () => ["campaign-token", "subject-1"]));
    expect(await screen.findByText("Sola lettura")).toBeInTheDocument();
    expect(pathInput()).toHaveValue("");
    expect(headerImport()).toBeEnabled();
  });

  test("exact import→reload→explicit status→effect status order and reversed late status", async () => {
    await ready();
    const trace: string[] = [];
    const importing = deferred<AnagraficaSubjectImportResult>();
    const reloading = deferred<AnagraficaSubjectDetail>();
    const firstStatus = deferred<AnagraficaSubjectNasImportStatus>();
    const secondStatus = deferred<AnagraficaSubjectNasImportStatus>();
    api.importUtenzeSubjectFromNas.mockImplementationOnce(() => { trace.push("import"); return importing.promise; });
    api.getUtenzeSubject.mockImplementationOnce(() => { trace.push("reload"); return reloading.promise; });
    api.getUtenzeSubjectNasImportStatus
      .mockImplementationOnce(() => { trace.push("status-1"); return firstStatus.promise; })
      .mockImplementationOnce(() => { trace.push("status-2"); return secondStatus.promise; });
    fireEvent.click(headerImport());
    expect(trace).toEqual(["import"]);
    await resolveRequest(importing, importResult);
    expect(trace).toEqual(["import", "reload"]);
    expect(screen.queryByText(importMessage)).not.toBeInTheDocument();
    await resolveRequest(reloading, subjectFixture({ nas_folder_path: "/refreshed/path" }));
    expect(trace).toEqual(["import", "reload", "status-1", "status-2"]);
    await resolveRequest(secondStatus, statusFixture({ message: "Newer effect result", pending_files_in_nas: 3 }));
    expect(screen.getByText("Newer effect result")).toBeInTheDocument();
    expect(screen.queryByText(importMessage)).not.toBeInTheDocument();
    for (const button of screen.getAllByRole("button", { name: "Aggiornamento..." })) expect(button).toBeDisabled();
    await resolveRequest(firstStatus, statusFixture({ message: "Older explicit result", pending_files_in_nas: 4 }));
    expect(screen.getByText("Older explicit result")).toBeInTheDocument();
    expect(screen.queryByText("Newer effect result")).not.toBeInTheDocument();
    expect(screen.getByText(importMessage)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Aggiorna documenti (4)" })).toBeEnabled();
    expect(pathInput()).toHaveValue("/refreshed/path");
  });

  test.each([
    [new Error("Import denied"), "Import denied"], ["bad import", "Errore import documenti da NAS"],
  ])("import rejection prevents reload and status: %s", async (error, message) => {
    await ready();
    api.importUtenzeSubjectFromNas.mockRejectedValueOnce(error);
    fireEvent.click(headerImport());
    await screen.findByText(message);
    expect(api.getUtenzeSubject).toHaveBeenCalledTimes(1);
    expect(api.getUtenzeSubjectNasImportStatus).toHaveBeenCalledTimes(1);
    expect(screen.queryByText(importMessage)).not.toBeInTheDocument();
    expect(headerImport()).toBeEnabled();
  });

  test.each([
    [new Error("Reload denied"), "Reload denied"], ["bad reload", "Errore import documenti da NAS"],
  ])("successful server import with failed reload reports partial failure: %s", async (error, message) => {
    await ready();
    api.getUtenzeSubject.mockRejectedValueOnce(error);
    fireEvent.click(headerImport());
    await screen.findByText(message);
    expect(api.importUtenzeSubjectFromNas).toHaveBeenCalledTimes(1);
    expect(api.getUtenzeSubject).toHaveBeenCalledTimes(2);
    expect(api.getUtenzeSubjectNasImportStatus).toHaveBeenCalledTimes(1);
    expect(screen.queryByText(importMessage)).not.toBeInTheDocument();
    expect(screen.getByText("Rossi Mario")).toBeInTheDocument();
    expect(headerImport()).toBeEnabled();
  });

  test("status failures are absorbed after successful import and success remains visible", async () => {
    await ready();
    api.getUtenzeSubjectNasImportStatus.mockRejectedValue(new Error("Status after import offline"));
    fireEvent.click(headerImport());
    await screen.findByText(importMessage);
    expect(screen.getByText("Status after import offline")).toBeInTheDocument();
    expect(api.getUtenzeSubjectNasImportStatus).toHaveBeenCalledTimes(3);
    expect(screen.queryByRole("button", { name: /Aggiornamento/ })).not.toBeInTheDocument();
  });

  test("reload returning the same object does not schedule an extra effect request", async () => {
    const sameSubject = subjectFixture();
    api.getUtenzeSubject.mockResolvedValue(sameSubject);
    await ready();
    fireEvent.click(headerImport());
    await screen.findByText(importMessage);
    expect(api.getUtenzeSubjectNasImportStatus).toHaveBeenCalledTimes(2);
  });
});

describe("R22 mounted candidates and captured selection", () => {
  test("read-only restrictions and independent candidate busy control", async () => {
    await ready();
    expect(screen.getByRole("button", { name: "Trova cartelle candidate" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Salva percorso NAS" })).toBeDisabled();
    expect(pathInput()).toHaveAttribute("readonly");
    edit();
    const pending = deferred<AnagraficaNasFolderCandidate[]>();
    api.getUtenzeSubjectNasCandidates.mockReturnValueOnce(pending.promise);
    search();
    expect(screen.getByRole("button", { name: "Ricerca cartelle..." })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Salva percorso NAS" })).toBeEnabled();
    expect(pathInput()).not.toHaveAttribute("readonly");
    expect(headerImport()).toBeEnabled();
    expect(api.getUtenzeSubjectNasCandidates.mock.calls).toEqual([["campaign-token", "subject-1"]]);
    await resolveRequest(pending, []);
    expect(screen.getByText(emptyCandidateMessage)).toBeInTheDocument();
    expect(api.updateUtenzeSubject).not.toHaveBeenCalled();
    expect(api.importUtenzeSubjectFromNas).not.toHaveBeenCalled();
    expect(api.getUtenzeSubjectNasImportStatus).toHaveBeenCalledTimes(1);
  });

  test("first API candidate is selected without sorting/review filtering; radio and typed selection", async () => {
    await ready(); edit();
    await candidates([
      candidateFixture({ score: 1, confidence: 0.1, requires_review: true }),
      candidateFixture({ folder_name: "Seconda cartella", nas_folder_path: "/archive/S/second", score: 99 }),
    ]);
    const radios = screen.getAllByRole("radio");
    expect(radios).toHaveLength(2);
    expect(radios[0]).toHaveAccessibleName(/Prima cartella/);
    expect(radios[1]).toHaveAccessibleName(/Seconda cartella/);
    expect(radios[0]).toBeChecked();
    expect(pathInput()).toHaveValue("/archive/R/first");
    fireEvent.click(radios[1]);
    expect(radios[1]).toBeChecked();
    expect(pathInput()).toHaveValue("/archive/S/second");
    setPath("/custom/path");
    expect(radios[0]).not.toBeChecked();
    expect(radios[1]).not.toBeChecked();
    expect(api.updateUtenzeSubject).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Termina modifica" }));
    expect(radios[0]).toBeDisabled();
    expect(radios[1]).toBeDisabled();
    expect(pathInput()).toHaveAttribute("readonly");
  });

  test("existing subject path survives search and subsequent empty result", async () => {
    api.getUtenzeSubject.mockResolvedValue(subjectFixture({ nas_folder_path: "/existing/path" }));
    await ready(); edit();
    await candidates([candidateFixture()]);
    expect(pathInput()).toHaveValue("/existing/path");
    expect(screen.getByRole("radio")).not.toBeChecked();
    await candidates([]);
    expect(pathInput()).toHaveValue("/existing/path");
    expect(screen.queryByRole("radio")).not.toBeInTheDocument();
    expect(screen.getByText(emptyCandidateMessage)).toBeInTheDocument();
  });

  test("boundary empty first candidate path does not auto-select the valid second path", async () => {
    await ready(); edit();
    await candidates([candidateFixture({ nas_folder_path: "" }), candidateFixture({ nas_folder_path: "/second", folder_name: "Seconda cartella" })]);
    expect(pathInput()).toHaveValue("");
    expect(screen.getAllByRole("radio")[1]).not.toBeChecked();
  });

  test.each([
    [new Error("Candidates denied"), "Candidates denied"], ["bad candidates", "Errore caricamento cartelle NAS candidate"],
  ])("candidate failure retains old list/path and releases busy: %s", async (error, message) => {
    await ready(); edit();
    await candidates([candidateFixture()]);
    api.getUtenzeSubjectNasCandidates.mockRejectedValueOnce(error);
    search();
    await screen.findByText(message);
    expect(pathInput()).toHaveValue("/archive/R/first");
    expect(screen.getByRole("radio")).toBeChecked();
    expect(screen.getByRole("button", { name: "Trova cartelle candidate" })).toBeEnabled();
  });

  test.each([
    ["", "/typed/during-search", "/archive/R/first"], ["/captured/path", "", ""],
  ])("candidate result uses initiating selection %s rather than current edit %s", async (captured, current, expected) => {
    await ready(); edit(); setPath(captured);
    const pending = deferred<AnagraficaNasFolderCandidate[]>();
    api.getUtenzeSubjectNasCandidates.mockReturnValueOnce(pending.promise);
    search(); setPath(current);
    await resolveRequest(pending, [candidateFixture()]);
    expect(pathInput()).toHaveValue(expected);
  });
});

describe("R22 mounted path payload and completion", () => {
  test("empty save validates without API or busy", async () => {
    await ready(); edit(); savePath();
    expect(screen.getByText("Seleziona una cartella NAS da salvare.")).toBeInTheDocument();
    expect(api.updateUtenzeSubject).not.toHaveBeenCalled();
    expect(api.getUtenzeSubjectNasImportStatus).toHaveBeenCalledTimes(1);
    expect(screen.getByRole("button", { name: "Salva percorso NAS" })).toBeEnabled();
  });

  test.each([
    ["R", "S", "R"], ["", "S", ""], [null, "S", "S"], [null, null, null],
  ])("candidate letter %s with subject letter %s yields exact payload %s", async (candidateLetter, subjectLetter, expectedLetter) => {
    api.getUtenzeSubject.mockResolvedValue(subjectFixture({ nas_folder_letter: subjectLetter }));
    await ready(); edit();
    await candidates([candidateFixture({ letter: candidateLetter })]);
    savePath(); await screen.findByText(pathMessage);
    expect(api.updateUtenzeSubject.mock.calls).toEqual([["campaign-token", "subject-1", {
      nas_folder_path: "/archive/R/first", nas_folder_letter: expectedLetter,
    }]]);
    expect(await screen.findByText("Sola lettura")).toBeInTheDocument();
    expect(api.getUtenzeSubject).toHaveBeenCalledTimes(1);
    expect(api.getUtenzeSubjectNasImportStatus).toHaveBeenCalledTimes(3);
  });

  test("selected second candidate, not first candidate, supplies its letter", async () => {
    await ready(); edit();
    await candidates([candidateFixture(), candidateFixture({ nas_folder_path: "/archive/S/second", letter: "S", folder_name: "Seconda cartella" })]);
    fireEvent.click(screen.getAllByRole("radio")[1]); savePath();
    await screen.findByText(pathMessage);
    expect(api.updateUtenzeSubject.mock.calls).toEqual([["campaign-token", "subject-1", {
      nas_folder_path: "/archive/S/second", nas_folder_letter: "S",
    }]]);
  });

  test.each(["S", null])("unmatched custom path preserves subject letter %s", async (letter) => {
    api.getUtenzeSubject.mockResolvedValue(subjectFixture({ nas_folder_letter: letter }));
    await ready(); edit();
    await candidates([candidateFixture()]); setPath("/custom/path"); savePath();
    await screen.findByText(pathMessage);
    expect(api.updateUtenzeSubject.mock.calls).toEqual([["campaign-token", "subject-1", {
      nas_folder_path: "/custom/path", nas_folder_letter: letter,
    }]]);
  });

  test("boundary whitespace path is sent verbatim with no client trimming", async () => {
    await ready(); edit(); setPath("   "); savePath();
    await screen.findByText(pathMessage);
    expect(api.updateUtenzeSubject.mock.calls).toEqual([["campaign-token", "subject-1", {
      nas_folder_path: "   ", nas_folder_letter: null,
    }]]);
  });

  test("deferred save preserves independent controls then response hydration wins edited input", async () => {
    await ready(); edit();
    await candidates([candidateFixture()]);
    const update = deferred<AnagraficaSubjectDetail>();
    api.updateUtenzeSubject.mockReturnValueOnce(update.promise);
    savePath();
    expect(screen.getByRole("button", { name: "Salvataggio..." })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Trova cartelle candidate" })).toBeEnabled();
    expect(screen.getByRole("radio")).toBeEnabled();
    expect(headerImport()).toBeEnabled();
    setPath("/edited/while-saving");
    await resolveRequest(update, subjectFixture({ nas_folder_path: "/canonical/returned", nas_folder_letter: "C" }));
    await screen.findByText(pathMessage);
    expect(pathInput()).toHaveValue("/canonical/returned");
    expect(pathInput()).toHaveAttribute("readonly");
    expect(screen.getByRole("radio")).toBeDisabled();
    expect(screen.getByRole("radio")).not.toBeChecked();
    expect(api.getUtenzeSubject).toHaveBeenCalledTimes(1);
  });

  test.each([
    [new Error("Path denied"), "Path denied"], ["bad path", "Errore salvataggio percorso NAS"],
  ])("update failure retains edit/input/options and releases busy: %s", async (error, message) => {
    await ready(); edit(); await candidates([candidateFixture()]);
    api.updateUtenzeSubject.mockRejectedValueOnce(error);
    savePath(); await screen.findByText(message);
    expect(pathInput()).toHaveValue("/archive/R/first");
    expect(screen.getByRole("radio")).toBeChecked();
    expect(screen.getByText("Modalità modifica attiva")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Salva percorso NAS" })).toBeEnabled();
    expect(api.getUtenzeSubjectNasImportStatus).toHaveBeenCalledTimes(1);
    expect(screen.queryByText(pathMessage)).not.toBeInTheDocument();
  });

  test("persisted path still reports success when both subsequent statuses fail", async () => {
    await ready(); edit(); setPath("/persisted/path");
    api.getUtenzeSubjectNasImportStatus.mockRejectedValue("bad status after save");
    savePath(); await screen.findByText(pathMessage);
    expect(screen.getByText("Verifica NAS non disponibile")).toBeInTheDocument();
    expect(pathInput()).toHaveValue("/persisted/path");
    expect(await screen.findByText("Sola lettura")).toBeInTheDocument();
    expect(api.getUtenzeSubjectNasImportStatus).toHaveBeenCalledTimes(3);
  });

  test("save→explicit status→effect status order; busy boolean clears while effect still pending", async () => {
    await ready(); edit(); setPath("/requested/path");
    const trace: string[] = [];
    const update = deferred<AnagraficaSubjectDetail>();
    const first = deferred<AnagraficaSubjectNasImportStatus>();
    const second = deferred<AnagraficaSubjectNasImportStatus>();
    api.updateUtenzeSubject.mockImplementationOnce(() => { trace.push("update"); return update.promise; });
    api.getUtenzeSubjectNasImportStatus
      .mockImplementationOnce(() => { trace.push("status-1"); return first.promise; })
      .mockImplementationOnce(() => { trace.push("status-2"); return second.promise; });
    savePath(); expect(trace).toEqual(["update"]);
    await resolveRequest(update, subjectFixture({ nas_folder_path: "/returned/path" }));
    expect(trace).toEqual(["update", "status-1", "status-2"]);
    expect(headerImport()).toBeDisabled();
    expect(screen.getByText("NAS pronto")).toBeInTheDocument();
    await resolveRequest(first, statusFixture({ message: "Explicit save status" }));
    expect(screen.getByText(pathMessage)).toBeInTheDocument();
    expect(headerImport()).toBeEnabled();
    expect(api.getUtenzeSubject).toHaveBeenCalledTimes(1);
    await resolveRequest(second, statusFixture({ message: "Late effect save status", pending_files_in_nas: 6 }));
    expect(screen.queryByText("Explicit save status")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Aggiorna documenti (6)" })).toBeEnabled();
  });
});

describe("R22 shared messages, cross-command and route races", () => {
  test("candidate command and empty guard preserve success; next nonempty save clears messages", async () => {
    await ready(); edit(); setPath("/initial/path"); savePath();
    await screen.findByText(pathMessage);
    expect(await screen.findByText("Sola lettura")).toBeInTheDocument();
    edit();
    api.getUtenzeSubjectNasCandidates.mockRejectedValueOnce(new Error("Candidate failure after success"));
    search(); await screen.findByText("Candidate failure after success");
    expect(screen.getByText(pathMessage)).toBeInTheDocument();
    setPath(""); savePath();
    expect(screen.getByText(pathMessage)).toBeInTheDocument();
    expect(screen.getByText("Seleziona una cartella NAS da salvare.")).toBeInTheDocument();
    setPath("/next/path");
    const pending = deferred<AnagraficaSubjectDetail>();
    api.updateUtenzeSubject.mockReturnValueOnce(pending.promise);
    savePath();
    expect(screen.queryByText(pathMessage)).not.toBeInTheDocument();
    expect(screen.queryByText("Seleziona una cartella NAS da salvare.")).not.toBeInTheDocument();
    await resolveRequest(pending, subjectFixture({ nas_folder_path: "/next/path" }));
    expect(screen.getByText(pathMessage)).toBeInTheDocument();
  });

  test("next import clears prior save success/error immediately", async () => {
    await ready(); edit(); setPath("/initial/path"); savePath();
    await screen.findByText(pathMessage);
    expect(await screen.findByText("Sola lettura")).toBeInTheDocument();
    edit(); setPath(""); savePath();
    const pending = deferred<AnagraficaSubjectImportResult>();
    api.importUtenzeSubjectFromNas.mockReturnValueOnce(pending.promise);
    fireEvent.click(headerImport());
    expect(screen.queryByText(pathMessage)).not.toBeInTheDocument();
    expect(screen.queryByText("Seleziona una cartella NAS da salvare.")).not.toBeInTheDocument();
    await rejectRequest(pending, new Error("Later import failure"));
    expect(screen.getByText("Later import failure")).toBeInTheDocument();
  });

  test("candidate response can finish during save; later hydration overwrites selection but keeps options", async () => {
    await ready(); edit(); setPath("/captured/path");
    const searching = deferred<AnagraficaNasFolderCandidate[]>();
    const saving = deferred<AnagraficaSubjectDetail>();
    api.getUtenzeSubjectNasCandidates.mockReturnValueOnce(searching.promise);
    api.updateUtenzeSubject.mockReturnValueOnce(saving.promise);
    search(); savePath();
    expect(screen.getByRole("button", { name: "Ricerca cartelle..." })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Salvataggio..." })).toBeDisabled();
    await resolveRequest(searching, [candidateFixture()]);
    expect(screen.getByRole("radio")).toBeEnabled();
    fireEvent.click(screen.getByRole("radio"));
    expect(pathInput()).toHaveValue("/archive/R/first");
    await resolveRequest(saving, subjectFixture({ nas_folder_path: "/saved/old-path" }));
    expect(pathInput()).toHaveValue("/saved/old-path");
    expect(screen.getByRole("radio")).toBeDisabled();
    expect(screen.getByText(pathMessage)).toBeInTheDocument();
  });

  test("same mounted route instance accepts an old status after id change", async () => {
    const initialStatus = deferred<AnagraficaSubjectNasImportStatus>();
    api.getUtenzeSubjectNasImportStatus.mockReturnValueOnce(initialStatus.promise);
    const view = render(<UtenzeSubjectDetailPage />);
    await screen.findByText("Rossi Mario");
    await waitFor(() => expect(api.getUtenzeSubjectNasImportStatus).toHaveBeenCalledTimes(1));
    const nextSubject = deferred<AnagraficaSubjectDetail>();
    api.getUtenzeSubject.mockReturnValueOnce(nextSubject.promise);
    api.subjectId = "subject-2";
    view.rerender(<UtenzeSubjectDetailPage />);
    await waitFor(() => expect(api.getUtenzeSubjectNasImportStatus).toHaveBeenCalledWith("campaign-token", "subject-2"));
    expect(api.getUtenzeSubject.mock.calls).toEqual([["campaign-token", "subject-1"], ["campaign-token", "subject-2"]]);
    expect(screen.getByText("Rossi Mario")).toBeInTheDocument();
    await resolveRequest(nextSubject, subjectFixture({ id: "subject-2", nas_folder_path: "/subject-2/path" }));
    expect(pathInput()).toHaveValue("/subject-2/path");
    await resolveRequest(initialStatus, statusFixture({ message: "Stale subject-1 status", pending_files_in_nas: 8 }));
    expect(screen.getByText("Stale subject-1 status")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Aggiorna documenti (8)" })).toBeEnabled();
    fireEvent.click(headerImport());
    await screen.findByText(importMessage);
    expect(api.importUtenzeSubjectFromNas).toHaveBeenCalledWith("campaign-token", "subject-2");
  });
});
