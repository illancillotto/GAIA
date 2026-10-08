import type { ReactNode } from "react";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import * as XLSX from "xlsx";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { ElaborazioniCapacitasWorkspace } from "@/components/elaborazioni/capacitas-workspace";

const mocks = vi.hoisted(() => ({
  token: vi.fn(),
  credentials: vi.fn(),
  terreniJobs: vi.fn(),
  particelleJobs: vi.fn(),
  historyJobs: vi.fn(),
  incassJobs: vi.fn(),
  createObjectURL: vi.fn<(blob: Blob) => string>(),
  revokeObjectURL: vi.fn<(url: string) => void>(),
}));

vi.mock("@/lib/auth", () => ({ getStoredAccessToken: mocks.token }));
vi.mock("@/lib/api", () => ({
  listCapacitasCredentials: mocks.credentials,
  listCapacitasTerreniJobs: mocks.terreniJobs,
  listCapacitasParticelleSyncJobs: mocks.particelleJobs,
  listCapacitasAnagraficaHistoryJobs: mocks.historyJobs,
  listCapacitasInCassSyncJobs: mocks.incassJobs,
  isAuthError: () => false,
}));
vi.mock("@/components/app/protected-page", () => ({
  ProtectedPage: ({ children }: { children: ReactNode }) => <>{children}</>,
}));
vi.mock("@/components/elaborazioni/workspace-modal", () => ({
  ElaborazioneWorkspaceModal: () => null,
}));

const originalCreateDescriptor = Object.getOwnPropertyDescriptor(window.URL, "createObjectURL");
const originalRevokeDescriptor = Object.getOwnPropertyDescriptor(window.URL, "revokeObjectURL");
const downloads: Array<{ href: string; filename: string }> = [];
const spreadsheetMime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";
const templates = [
  {
    section: "terreni" as const,
    basename: "capacitas-terreni-template",
    sheet: "terreni",
    rows: [
      ["comune", "sezione", "foglio", "particella", "sub"],
      ["Uras", "", "1", "680", ""],
      ["Uras", "", "14", "1695", ""],
    ],
    csv: "comune,sezione,foglio,particella,sub\nUras,,1,680,\nUras,,14,1695,",
  },
  {
    section: "storico" as const,
    basename: "capacitas-anagrafica-storico-template",
    sheet: "storico",
    rows: [
      ["subject_id", "idxana"],
      ["550e8400-e29b-41d4-a716-446655440000", ""],
      ["", "48A9749E-96BF-4617-A019-046BF4CECA2B"],
    ],
    csv: "subject_id,idxana\n550e8400-e29b-41d4-a716-446655440000,\n,48A9749E-96BF-4617-A019-046BF4CECA2B",
  },
];

beforeEach(() => {
  vi.resetAllMocks();
  downloads.length = 0;
  mocks.token.mockReturnValue("session-token");
  for (const list of [mocks.credentials, mocks.terreniJobs, mocks.particelleJobs, mocks.historyJobs, mocks.incassJobs]) {
    list.mockResolvedValue([]);
  }
  mocks.createObjectURL.mockImplementation(() => `blob:capacitas-template-${mocks.createObjectURL.mock.calls.length}`);
  Object.defineProperty(window.URL, "createObjectURL", {
    configurable: true, writable: true, value: mocks.createObjectURL,
  });
  Object.defineProperty(window.URL, "revokeObjectURL", {
    configurable: true, writable: true, value: mocks.revokeObjectURL,
  });
  vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function (this: HTMLAnchorElement) {
    downloads.push({ href: this.href, filename: this.download });
  });
});

afterEach(() => {
  cleanup();
  vi.useRealTimers();
  vi.restoreAllMocks();
  if (originalCreateDescriptor) Object.defineProperty(window.URL, "createObjectURL", originalCreateDescriptor);
  else Reflect.deleteProperty(window.URL, "createObjectURL");
  if (originalRevokeDescriptor) Object.defineProperty(window.URL, "revokeObjectURL", originalRevokeDescriptor);
  else Reflect.deleteProperty(window.URL, "revokeObjectURL");
});

async function mountTemplates(section: "terreni" | "storico") {
  const view = render(<ElaborazioniCapacitasWorkspace embedded initialSection={section} />);
  await waitFor(() => expect(screen.getByText(
    section === "terreni" ? "Nessun job registrato" : "Nessun job storico registrato",
  )).toBeInTheDocument());
  if (section === "storico") fireEvent.click(screen.getByRole("button", { name: "Batch da file" }));
  return view;
}

function clickTemplate(format: "csv" | "xlsx", basename: string) {
  fireEvent.click(screen.getByRole("button", { name: format === "csv" ? "Template CSV" : "Template Excel" }));
  const index = downloads.length - 1;
  const blob = mocks.createObjectURL.mock.calls[index][0];
  expect(blob).toBeInstanceOf(Blob);
  expect(blob.size).toBeGreaterThan(0);
  expect(blob.type).toBe(format === "csv" ? "text/csv;charset=utf-8" : spreadsheetMime);
  expect(downloads[index]).toEqual({
    href: `blob:capacitas-template-${index + 1}`,
    filename: `${basename}.${format}`,
  });
  expect(mocks.createObjectURL).toHaveBeenCalledTimes(index + 1);
  return blob;
}

function assertDelayedRevocation(url: string) {
  expect(mocks.revokeObjectURL).not.toHaveBeenCalled();
  act(() => { vi.advanceTimersByTime(999); });
  expect(mocks.revokeObjectURL).not.toHaveBeenCalled();
  act(() => { vi.advanceTimersByTime(1); });
  expect(mocks.revokeObjectURL).toHaveBeenCalledExactlyOnceWith(url);
  act(() => { vi.advanceTimersByTime(10000); });
  expect(mocks.revokeObjectURL).toHaveBeenCalledTimes(1);
}

describe("Capacitas real template downloads", () => {
  test.each(templates)("exports exact $section CSV headers/examples and releases its URL after 1000ms", async (template) => {
    await mountTemplates(template.section);
    vi.useFakeTimers();
    const blob = clickTemplate("csv", template.basename);
    expect(await blob.text()).toBe(template.csv);
    const workbook = XLSX.read(await blob.text(), { type: "string", raw: true });
    expect(XLSX.utils.sheet_to_json(workbook.Sheets[workbook.SheetNames[0]], {
      header: 1, raw: false, defval: "",
    })).toEqual(template.rows);
    assertDelayedRevocation("blob:capacitas-template-1");
    for (const list of [mocks.credentials, mocks.terreniJobs, mocks.particelleJobs, mocks.historyJobs, mocks.incassJobs]) {
      expect(list).toHaveBeenCalledTimes(1);
    }
  });

  test.each(templates)("exports a readable $section XLSX workbook with complete sheets and examples", async (template) => {
    await mountTemplates(template.section);
    vi.useFakeTimers();
    const blob = clickTemplate("xlsx", template.basename);
    const bytes = await blob.arrayBuffer();
    expect(Array.from(new Uint8Array(bytes).slice(0, 4))).toEqual([80, 75, 3, 4]);
    const workbook = XLSX.read(new Uint8Array(bytes), { type: "array" });
    expect(workbook.SheetNames).toEqual(template.section === "terreni" ? ["terreni", "istruzioni"] : ["storico"]);
    expect(XLSX.utils.sheet_to_json(workbook.Sheets[template.sheet], {
      header: 1, raw: false, defval: "",
    })).toEqual(template.rows);
    if (template.section === "terreni") {
      expect(XLSX.utils.sheet_to_json(workbook.Sheets.istruzioni)).toEqual([
        { campo: "comune", obbligatorio: "si", descrizione: "Comune o frazione da risolvere su Capacitas, meglio se specifico." },
        { campo: "foglio", obbligatorio: "si", descrizione: "Foglio catastale usato in ricercaTerreni." },
        { campo: "particella", obbligatorio: "si", descrizione: "Particella catastale." },
        { campo: "sezione", obbligatorio: "no", descrizione: "Sezione Capacitas se presente." },
        { campo: "sub", obbligatorio: "no", descrizione: "Subalterno o sub particella." },
        { campo: "note", obbligatorio: "no", descrizione: "Colonna libera ignorata dal sistema se presente." },
      ]);
    }
    assertDelayedRevocation("blob:capacitas-template-1");
  });

  test("offers history templates only in file mode and preserves a generated download when returning to manual mode", async () => {
    render(<ElaborazioniCapacitasWorkspace embedded initialSection="storico" />);
    await waitFor(() => expect(screen.getByText("Nessun job storico registrato")).toBeInTheDocument());
    expect(screen.queryByRole("button", { name: "Template Excel" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Template CSV" })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Batch da file" }));
    vi.useFakeTimers();
    const blob = clickTemplate("csv", templates[1].basename);
    expect(await blob.text()).toBe(templates[1].csv);
    fireEvent.click(screen.getByRole("button", { name: "Manuale" }));
    expect(screen.queryByRole("button", { name: "Template CSV" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Template Excel" })).not.toBeInTheDocument();
    assertDelayedRevocation("blob:capacitas-template-1");
  });

  test("keeps staggered Terreni and history downloads independent across section navigation", async () => {
    await mountTemplates("terreni");
    vi.useFakeTimers();
    const terreni = clickTemplate("csv", templates[0].basename);
    expect(await terreni.text()).toBe(templates[0].csv);
    act(() => { vi.advanceTimersByTime(250); });
    fireEvent.click(screen.getByRole("button", { name: /^Storico anagrafico/ }));
    fireEvent.click(screen.getByRole("button", { name: "Batch da file" }));
    const history = clickTemplate("xlsx", templates[1].basename);
    const workbook = XLSX.read(new Uint8Array(await history.arrayBuffer()), { type: "array" });
    expect(workbook.SheetNames).toEqual(["storico"]);
    expect(XLSX.utils.sheet_to_json(workbook.Sheets.storico, { header: 1, raw: false, defval: "" })).toEqual(templates[1].rows);
    act(() => { vi.advanceTimersByTime(749); });
    expect(mocks.revokeObjectURL).not.toHaveBeenCalled();
    act(() => { vi.advanceTimersByTime(1); });
    expect(mocks.revokeObjectURL.mock.calls).toEqual([["blob:capacitas-template-1"]]);
    act(() => { vi.advanceTimersByTime(249); });
    expect(mocks.revokeObjectURL.mock.calls).toEqual([["blob:capacitas-template-1"]]);
    act(() => { vi.advanceTimersByTime(1); });
    expect(mocks.revokeObjectURL.mock.calls).toEqual([["blob:capacitas-template-1"], ["blob:capacitas-template-2"]]);
    expect(downloads.map((download) => download.filename)).toEqual([
      "capacitas-terreni-template.csv", "capacitas-anagrafica-storico-template.xlsx",
    ]);
  });

  test("still releases the generated URL on schedule after the workspace is unmounted", async () => {
    const view = await mountTemplates("terreni");
    vi.useFakeTimers();
    const blob = clickTemplate("xlsx", templates[0].basename);
    expect(XLSX.read(new Uint8Array(await blob.arrayBuffer()), { type: "array" }).SheetNames).toEqual(["terreni", "istruzioni"]);
    view.unmount();
    assertDelayedRevocation("blob:capacitas-template-1");
  });
});
