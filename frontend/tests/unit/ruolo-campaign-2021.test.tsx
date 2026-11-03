import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import Page from "@/app/ruolo/tributi/2021/page";
import { CampaignContent, CampaignTable, CampaignWorkspace, matches } from "@/components/ruolo/campaign-2021/workspace";
import { CampaignReview } from "@/components/ruolo/campaign-2021/review";
import type { CampaignReport, CampaignRow } from "@/components/ruolo/campaign-2021/client";

const api = vi.hoisted(() => ({ request: vi.fn(), requestBlob: vi.fn() }));
vi.mock("@/lib/api/core", () => api);
const session = vi.hoisted(() => ({ current: {} as Record<string, unknown> }));
vi.mock("@/lib/use-session-bootstrap", () => ({ useSessionBootstrap: () => session.current }));
vi.mock("@/components/ruolo/module-page", () => ({ RuoloModulePage: ({ title, children }: { title: string; children: React.ReactNode }) => <div><h1>{title}</h1>{children}</div> }));

const BASE = "/ruolo/tributi/campagna-2021";
const first: CampaignRow = { row: 2, number: "020210000000010", name: "CONTRIBUENTE ESEMPIO", tax_code: "RSSMRA80A01H501U", digital: true, amounts: { residual: "100.00", total: "125.68" }, current: { accounting: { importo_residuo: "100,00" }, engine: { saldo_amount: "106.00" } }, reconciliation: { kind: "prima_emissione_non_documentata_come_notificata", blockers: [], reviews: ["base_360_365"], deltas: { interest: "19.68", zero: "0.00" } } };
const second: CampaignRow = { ...first, row: 3, number: "020210000000020", name: "SECONDO ESEMPIO", digital: false, current: {}, reconciliation: { kind: "stato_incerto", blockers: ["storico_non_verificato"], reviews: [], deltas: {} } };
const report: CampaignReport = { report_sha256: "a".repeat(64), file_sha256: "b".repeat(64), acquired_at: "2026-11-02T00:00:00Z", summary: { rows: 2, ordinary: 1, digital: 1, total: "251.36", warnings: ["F-J non è un pagamento verificato"], parameters: { end: "2026-10-31" } }, rows: [first, second] };
const saved = { ...report, id: "campaign" };
const approved = { id: "approval", state: "snapshot_contabile_approvato", actor_id: 1, approved_at: "2026-11-02", sent: false, notified: false };

beforeEach(() => {
  vi.resetAllMocks();
  session.current = { status: "ready", token: "t", currentUser: { role: "admin", enabled_modules: ["ruolo"] }, grantedSectionKeys: ["ruolo.tributi.view", "ruolo.tributi.manage_status"] };
  api.request.mockImplementation((url: string) => Promise.resolve(url === BASE ? [{ id: "old", filename: "precedente.xlsx", created_at: "2026-11-01" }] : url.endsWith("/analisi") ? report : url.endsWith("/importazioni") ? saved : url.endsWith("/approvazioni") ? approved : saved));
  api.requestBlob.mockResolvedValue(new Blob(["marked-pdf"], { type: "application/pdf" }));
  URL.createObjectURL = vi.fn(() => "blob:preview"); URL.revokeObjectURL = vi.fn();
  vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

function fillApproval() {
  fireEvent.change(screen.getByLabelText("Importi da approvare"), { target: { value: "excel" } });
  fireEvent.change(screen.getByLabelText("Spese da aggiungere"), { target: { value: "0.00" } });
  fireEvent.change(screen.getByLabelText("Canale valutato"), { target: { value: "nessuno" } });
  fireEvent.change(screen.getByLabelText("Riferimento verifica spese"), { target: { value: "Verifica spese sintetica" } });
  fireEvent.change(screen.getByLabelText("Riferimento verifica: base_360_365"), { target: { value: "Verifica base giorni" } });
  fireEvent.change(screen.getByLabelText("Motivazione contabile e amministrativa"), { target: { value: "Verifica sintetica" } });
  fireEvent.click(screen.getByRole("checkbox"));
}

it("analyzes before retaining, blocks unsafe rows, approves a snapshot and downloads only a draft", async () => {
  render(<Page />);
  expect(screen.getByRole("heading", { name: "Avvisi e solleciti 2021" })).toBeVisible();
  expect(screen.getByRole("button", { name: "Analizza senza importare" })).toBeDisabled();
  const file = new File(["synthetic"], "scope.xlsx");
  fireEvent.change(screen.getByLabelText("File Excel 2021"), { target: { files: [file] } });
  fireEvent.click(screen.getByRole("button", { name: "Analizza senza importare" }));
  expect(await screen.findByText(/2 avvisi: 1 ordinari, 1 digitali/)).toBeVisible();
  expect(screen.queryByRole("button", { name: `Verifica e approva ${first.number}` })).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Conserva lo snapshot verificato" }));
  expect(await screen.findByRole("button", { name: `Verifica e approva ${second.number}` })).toBeDisabled();
  fireEvent.click(screen.getByRole("button", { name: `Verifica e approva ${first.number}` }));
  fillApproval(); fireEvent.click(screen.getByRole("button", { name: "Approva snapshot contabile" }));
  expect(await screen.findByText(/Snapshot contabile approvato da operatore 1/)).toBeVisible();
  fireEvent.click(screen.getByRole("button", { name: "Crea anteprima PDF" }));
  await waitFor(() => expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:preview"));
  expect(api.requestBlob).toHaveBeenCalledWith(`${BASE}/approvazioni/approval/anteprima`, expect.objectContaining({ method: "POST" }));
  const call = api.request.mock.calls.find(([url]) => url === `${BASE}/campaign/approvazioni`)!;
  expect(JSON.parse(call[1].body)).toMatchObject({ row_number: 2, amount_source: "excel", notification_fee: "0.00", confirmed: true, resolutions: { base_360_365: "Verifica base giorni" } });
  const retained = api.request.mock.calls.find(([url]) => url === `${BASE}/importazioni`)!;
  expect(retained[1].body.get("report_sha256")).toBe(report.report_sha256);
});

it("filters exact positions and reopens retained snapshots without an upload", async () => {
  render(<CampaignContent token="t" canEdit />);
  fireEvent.click(await screen.findByRole("button", { name: /precedente.xlsx/ }));
  expect(await screen.findByText(/2 di 2 posizioni/)).toBeVisible();
  fireEvent.change(screen.getByLabelText("Digitale"), { target: { value: "false" } });
  expect(screen.getByText(/1 di 2 posizioni/)).toBeVisible();
  fireEvent.change(screen.getByLabelText("Tipo"), { target: { value: "stato_incerto" } });
  fireEvent.change(screen.getByLabelText("Esito"), { target: { value: "blocked" } });
  fireEvent.change(screen.getByLabelText("Totale minimo"), { target: { value: "125" } });
  fireEvent.change(screen.getByLabelText("Totale massimo"), { target: { value: "126" } });
  fireEvent.change(screen.getByLabelText("Cerca numero o destinatario"), { target: { value: second.number } });
  expect(screen.getByText(second.name)).toBeVisible();
  expect(screen.queryByText(first.name)).not.toBeInTheDocument();
  expect(api.request).toHaveBeenCalledWith(`${BASE}/old`, expect.anything());
  const empty = { query: "", digital: "", kind: "", state: "", min: "", max: "" };
  expect(matches(first, { ...empty, state: "review" })).toBe(true);
  expect(matches(first, { ...empty, min: "999" })).toBe(false);
  expect(matches(first, { ...empty, max: "1" })).toBe(false);
});

it.each([new Error("Dati cambiati"), "offline"])("explains failed approval and preview requests (%s)", async (failure) => {
  render(<CampaignReview token="t" report={saved} row={first} />);
  api.request.mockRejectedValueOnce(failure);
  fillApproval(); fireEvent.click(screen.getByRole("button", { name: "Approva snapshot contabile" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(failure instanceof Error ? failure.message : "Approvazione non riuscita");
  fireEvent.click(screen.getByRole("button", { name: "Approva snapshot contabile" }));
  expect(await screen.findByRole("button", { name: "Crea anteprima PDF" })).toBeEnabled();
  api.requestBlob.mockRejectedValueOnce(failure);
  fireEvent.click(screen.getByRole("button", { name: "Crea anteprima PDF" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(failure instanceof Error ? failure.message : "Anteprima non riuscita");
});

it("handles unavailable history, failed analysis and clearing a file", async () => {
  api.request.mockRejectedValueOnce(new Error("unavailable"));
  render(<CampaignContent token="t" canEdit={false} />);
  expect(await screen.findByRole("alert")).toHaveTextContent("Storico non disponibile");
  const upload = screen.getByLabelText("File Excel 2021");
  fireEvent.change(upload, { target: { files: [new File(["x"], "scope.xlsx")] } });
  api.request.mockRejectedValueOnce(new Error("File non valido"));
  fireEvent.click(screen.getByRole("button", { name: "Analizza senza importare" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("File non valido");
  api.request.mockRejectedValueOnce("offline");
  fireEvent.click(screen.getByRole("button", { name: "Analizza senza importare" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Operazione non riuscita");
  fireEvent.change(upload, { target: { files: [] } });
  expect(screen.getByRole("button", { name: "Analizza senza importare" })).toBeDisabled();
});

it.each([true, false])("ignores history that completes after the workspace is unmounted (%s)", async (success) => {
  let resolve!: (value: unknown) => void;
  api.request.mockReturnValueOnce(new Promise((yes, no) => { resolve = success ? yes : no; }));
  const view = render(<CampaignContent token="t" canEdit={false} />); view.unmount();
  await act(async () => resolve([]));
});

it("shows F-J separately and compares approved sources and notification fees before approval", () => {
  render(<CampaignReview token="t" report={saved} row={{ ...first, amounts: { ...first.amounts, difference: "20.00" } }} />);
  expect(screen.getByText(/Differenza contabile F-J: € 20.00/)).toBeVisible();
  expect(screen.queryByText(/Totale PDF:/)).not.toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("Importi da approvare"), { target: { value: "excel" } });
  fireEvent.change(screen.getByLabelText("Spese da aggiungere"), { target: { value: "11.55" } });
  expect(screen.getByText(/Totale PDF: € 137.23/)).toBeVisible();
  fireEvent.change(screen.getByLabelText("Importi da approvare"), { target: { value: "gaia" } });
  expect(screen.getByText(/Totale PDF: € 117.55/)).toBeVisible();
});

it("requires the module and section and supports read-only users", async () => {
  session.current = { status: "loading" };
  const view = render(<CampaignWorkspace />); expect(screen.getByRole("status")).toBeVisible();
  session.current = { status: "ready", token: "t", currentUser: { role: "viewer", enabled_modules: [] }, grantedSectionKeys: [] };
  view.rerender(<CampaignWorkspace />); expect(screen.getByRole("alert")).toHaveTextContent("Accesso non autorizzato");
  session.current = { status: "ready", token: "t", currentUser: { role: "super_admin", enabled_modules: [] }, grantedSectionKeys: ["ruolo.tributi.view"] };
  view.rerender(<CampaignWorkspace />); await screen.findByRole("button", { name: /precedente.xlsx/ });
  cleanup(); render(<CampaignTable report={saved} token="t" canEdit={false} />);
  expect(screen.queryByRole("button", { name: /Verifica e approva/ })).not.toBeInTheDocument();
});
