import { Buffer } from "node:buffer";
import type { ReactNode } from "react";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import * as XLSX from "xlsx";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { ElaborazioniCapacitasWorkspace } from "@/components/elaborazioni/capacitas-workspace";

const mocks = vi.hoisted(() => ({ token: vi.fn(), credentials: vi.fn(), terreni: vi.fn(), particelle: vi.fn(), history: vi.fn(), incass: vi.fn(), createTerreni: vi.fn(), createHistory: vi.fn(), authError: vi.fn() }));
vi.mock("@/lib/auth", () => ({ getStoredAccessToken: mocks.token }));
vi.mock("@/lib/api", () => ({
  listCapacitasCredentials: mocks.credentials,
  listCapacitasTerreniJobs: mocks.terreni,
  listCapacitasParticelleSyncJobs: mocks.particelle,
  listCapacitasAnagraficaHistoryJobs: mocks.history,
  listCapacitasInCassSyncJobs: mocks.incass,
  createCapacitasTerreniJob: mocks.createTerreni,
  createCapacitasAnagraficaHistoryJob: mocks.createHistory,
  isAuthError: mocks.authError,
}));
vi.mock("@/components/app/protected-page", () => ({ ProtectedPage: ({ children }: { children: ReactNode }) => <>{children}</> }));
vi.mock("@/components/elaborazioni/workspace-modal", () => ({ ElaborazioneWorkspaceModal: () => null }));

function workbookWithoutSheets(): File {
  const workbook = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(workbook, XLSX.utils.aoa_to_sheet([["subject_id"], ["A"]]), "first");
  const archive = XLSX.CFB.read(XLSX.write(workbook, { bookType: "xlsx", type: "buffer" }), { type: "buffer" });
  const entry = XLSX.CFB.find(archive, "Root Entry/xl/workbook.xml");
  if (!entry) throw new Error("Serialized workbook XML missing");
  const originalXml = Buffer.from(entry.content).toString("utf8");
  const modifiedXml = originalXml.replace(/<sheets>[\s\S]*?<\/sheets>/, "<sheets/>");
  expect(modifiedXml).not.toEqual(originalXml);
  XLSX.CFB.utils.cfb_add(archive, "Root Entry/xl/workbook.xml", Buffer.from(modifiedXml));
  const bytes: Buffer = XLSX.CFB.write(archive, { fileType: "zip", type: "buffer" });
  expect(XLSX.read(bytes, { type: "buffer" }).SheetNames).toEqual([]);
  const contents = new Uint8Array(bytes).buffer;
  const file = new File([contents], "no-sheets.xlsx", { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" });
  Object.defineProperty(file, "arrayBuffer", { value: async () => contents });
  return file;
}

beforeEach(() => {
  vi.resetAllMocks();
  mocks.token.mockReturnValue("session-token");
  for (const list of [mocks.credentials, mocks.terreni, mocks.particelle, mocks.history, mocks.incass]) list.mockResolvedValue([]);
  mocks.authError.mockReturnValue(false);
});
afterEach(() => { cleanup(); });

describe("Capacitas actual OOXML workbook without sheets", () => {
  test("Terreni upload rejects parsed empty workbook, retains filename and prevents submission", async () => {
    render(<ElaborazioniCapacitasWorkspace embedded initialSection="terreni" />);
    await screen.findByText("Nessun job registrato");
    fireEvent.change(screen.getByLabelText("File batch"), { target: { files: [workbookWithoutSheets()] } });
    const notices = await screen.findAllByText("File vuoto o senza righe valide per il batch Terreni.");
    for (const notice of notices) expect(notice).toBeVisible();
    expect(screen.getByRole("button", { name: "Avvia job batch" })).toBeDisabled();
    expect(screen.getByText("Nessun file batch caricato")).toBeVisible();
    expect(screen.getByText("no-sheets.xlsx")).toBeVisible();
    expect(mocks.createTerreni).not.toHaveBeenCalled();
    expect(screen.getByLabelText("File batch")).toBeEnabled();
  });

  test("Storico upload rejects parsed empty workbook and disables import without API dispatch", async () => {
    render(<ElaborazioniCapacitasWorkspace embedded initialSection="storico" />);
    await screen.findByText("Nessun job storico registrato");
    fireEvent.click(screen.getByRole("button", { name: "Batch da file" }));
    fireEvent.change(screen.getByLabelText("File batch"), { target: { files: [workbookWithoutSheets()] } });
    const notices = await screen.findAllByText("File vuoto o senza righe valide per lo storico anagrafico.");
    for (const notice of notices) expect(notice).toBeVisible();
    expect(screen.getByRole("button", { name: "Avvia import storico" })).toBeDisabled();
    expect(screen.getByText("0 righe pronte")).toBeVisible();
    expect(mocks.createHistory).not.toHaveBeenCalled();
    expect(screen.getByLabelText("File batch")).toBeEnabled();
  });
});
