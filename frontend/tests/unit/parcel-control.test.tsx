import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";

import { ParcelControlDetail } from "@/components/ruolo/parcel-control-detail";
import { ParcelControlForms } from "@/components/ruolo/parcel-control-forms";
import { ParcelControlTable } from "@/components/ruolo/parcel-control-table";
import { ParcelControlWorkspace } from "@/components/ruolo/parcel-control-workspace";
import type { ControlCase, ControlRow } from "@/types/parcel-control";

const mocks = vi.hoisted(() => ({ params: new URLSearchParams(), push: vi.fn(), request: vi.fn(),
  token: "token" as string | null, user: { role: "super_admin" } as { role: string } | null, keys: [] as string[] }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: mocks.push }), useSearchParams: () => mocks.params }));
vi.mock("@/components/layout/app-shell-context", () => ({ useAppShellContext: () => ({ currentUser: mocks.user, grantedSectionKeys: mocks.keys }) }));
vi.mock("@/components/ruolo/module-page", () => ({ RuoloModulePage: ({ children }: { children: React.ReactNode }) => <div>{children}</div> }));
vi.mock("@/lib/auth", () => ({ getStoredAccessToken: () => mocks.token }));
vi.mock("@/lib/parcel-control-api", () => ({ parcelControlRequest: mocks.request,
  controlCommand: (reason: string, data: object, version: number) => ({ reason, data, expected_version: version }) }));

function row(overrides: Partial<ControlRow> = {}): ControlRow {
  return { id: "parcel-1", label: "ORISTANO · 1/100", reference: { comune_nome: "ORISTANO", comune_codice: "G113",
    foglio: "1", particella: "100", subalterno: "", sezione: null, catasto: null },
    years: { 2020: "present", 2021: "absent", 2022: "not_verifiable", 2023: "present", 2024: "present", 2025: "not_verifiable" },
    first_year: 2020, last_year: 2024, current_presence: "not_verifiable", cf_anomaly: true,
    identity_incomplete: true, territorial_status: "verification_required", occurrences: [], case_id: null, case_status: null, ...overrides };
}

function practice(): ControlCase {
  return { id: "case-1", parcel_id: "parcel-1", status: "open", version: 2, responsible_id: 1, current: row(),
    original: { occurrences: [{ row_id: "source-1", year: 2020, avviso_id: "notice-1", codice_cnc: "CNC", subject_id: null,
      name: "Mario Rossi", tax_code: { original: null, normalized: "", anomaly: "missing" }, cat_particella_id: null, catasto_status: "suppressed" },
      { row_id: "source-2", year: 2021, avviso_id: "notice-2", codice_cnc: "CNC2", subject_id: null, name: null,
        tax_code: { original: "RSSMRA80A01H501U", normalized: "RSSMRA80A01H501U", anomaly: null }, cat_particella_id: "cat-1", catasto_status: null }] },
    evidence: [{ id: "e1", kind: "document", source: "AdE", reference: "Doc 1" }, { id: "e2", kind: "visura", request_id: "v1", scope: "Oristano" },
      { id: "e3", kind: "visura", request_id: "v2" }],
    matches: [{ id: "m1", status: "confirmed", name: "Mario Rossi", tax_code: "RSSMRA80A01H501U", subject_kind: "PF", right: "Proprietà", share: "1/1", period: "2025" },
      { id: "m2", status: "proposed", name: "Altro", tax_code: "01114601006", subject_kind: "PNF", right: "Proprietà", share: "1/2", period: "2020" }],
    parcels: [{ id: "recovered-1", reference: row().reference, status: "investigating" }],
    visure: [{ id: "v1", status: "completed", error: null, search_mode: "soggetto", batch_id: "batch-1",
      extraction: { owners: [{ denominazione: "Mario Rossi", codice_fiscale: "RSSMRA80A01H501U", diritto: "Proprietà", quota: "1/1" }] } },
      { id: "v2", status: "failed", error: "Errore tecnico", search_mode: "immobile", batch_id: "batch-2", extraction: null }],
    proposals: [{ id: "proposal-1", label: "ORISTANO · 1/100", year: 2025, kind: "insertion", status: "review_required", verified_tax_code: "RSSMRA80A01H501U", eligibility_rule: "Delibera", residual_doubts: "Titolo storico" }],
    audit: [{ action: "open", reason: "Verifica", actor_id: 1, created_at: "2025-01-01" }] };
}

beforeEach(() => {
  mocks.params = new URLSearchParams(); mocks.push.mockReset(); mocks.request.mockReset();
  mocks.token = "token"; mocks.user = { role: "super_admin" }; mocks.keys = [];
  mocks.request.mockResolvedValue({ items: [row()], total: 51, current_year: 2025, coverage: {}, refreshed_at: "2025-01-01" });
});

test("workspace defaults to all parcels and preserves annual links", async () => {
  const component = render(<ParcelControlWorkspace annualView={<p>Archivio annuale</p>} />);
  expect(await screen.findByText("ORISTANO · 1/100")).toBeInTheDocument();
  expect(mocks.request).toHaveBeenCalledWith("token", "?view=all&page=1&search=");
  expect(screen.getByRole("link", { name: "Successiva" })).toHaveAttribute("href", expect.stringContaining("pagina=2"));
  fireEvent.change(screen.getByLabelText("Cerca particella"), { target: { value: "1/100" } });
  fireEvent.submit(screen.getByLabelText("Cerca particella").closest("form")!);
  expect(mocks.push).toHaveBeenCalledWith("/ruolo/particelle?vista=all&ricerca=1%2F100");
  mocks.params = new URLSearchParams("anno=2025");
  component.rerender(<ParcelControlWorkspace annualView={<p>Archivio annuale</p>} />);
  expect(screen.getByText("Archivio annuale")).toBeInTheDocument();
  mocks.params = new URLSearchParams("vista=annuale");
  component.rerender(<ParcelControlWorkspace annualView={<p>Archivio annuale</p>} />);
  expect(screen.getByText("Archivio annuale")).toBeInTheDocument();
});

test("analysis, opening a practice and saving retain stable URLs", async () => {
  render(<ParcelControlWorkspace annualView={null} />);
  await screen.findByText("ORISTANO · 1/100");
  mocks.request.mockResolvedValueOnce({ items: [row()], total: 1 }).mockResolvedValue({ items: [row()], total: 1 });
  fireEvent.click(screen.getByText("Aggiorna analisi dello storico"));
  await waitFor(() => expect(mocks.request).toHaveBeenCalledWith("token", "/analisi", expect.objectContaining({ reason: expect.any(String) })));
  await waitFor(() => expect(screen.queryByRole("status")).not.toBeInTheDocument());
  mocks.request.mockResolvedValue(practice());
  fireEvent.click(screen.getByText("Apri pratica"));
  await waitFor(() => expect(mocks.push).toHaveBeenCalledWith("/ruolo/particelle?vista=cases&pratica=case-1"));
  await screen.findByText("Storico delle decisioni");
  fireEvent.change(screen.getByLabelText("Azione"), { target: { value: "status" } });
  fireEvent.change(screen.getAllByLabelText("Motivazione")[1], { target: { value: "Approfondimento necessario" } });
  fireEvent.submit(screen.getByText("Salva nella pratica").closest("form")!);
  await waitFor(() => expect(mocks.request).toHaveBeenCalledWith("token", "/pratiche/case-1/status", expect.objectContaining({ expected_version: 2 })));
});

test("practice details can be resumed and refreshed", async () => {
  mocks.params = new URLSearchParams("vista=cases&pratica=case-1");
  mocks.request.mockResolvedValue(practice());
  render(<ParcelControlWorkspace annualView={null} />);
  await screen.findByText("Storico delle decisioni");
  expect(mocks.request).toHaveBeenCalledWith("token", "/pratiche/case-1");
  fireEvent.click(screen.getByText("Aggiorna esiti"));
  await waitFor(() => expect(mocks.request).toHaveBeenCalledTimes(2));
});

test("coverage is an explicit documented action", async () => {
  render(<ParcelControlWorkspace annualView={null} />);
  await screen.findByText("ORISTANO · 1/100");
  fireEvent.change(screen.getByLabelText("Fonte e versione verificata"), { target: { value: "inCASS integrale" } });
  fireEvent.change(screen.getByLabelText("Motivazione"), { target: { value: "Dettagli verificati" } });
  fireEvent.submit(screen.getByText("Registra attestazione").closest("form")!);
  await waitFor(() => expect(mocks.request).toHaveBeenCalledWith("token", "/annualita/2025/certificazione", expect.objectContaining({ data: { source: "inCASS integrale" } })));
});

test("proposal queue and viewer permissions", async () => {
  mocks.params = new URLSearchParams("vista=proposals&pagina=2&ricerca=Oristano");
  mocks.user = { role: "viewer" };
  mocks.request.mockResolvedValue({ items: [{ ...practice().proposals[0], case_id: "case-1" }], total: 1 });
  render(<ParcelControlWorkspace annualView={null} />);
  expect(await screen.findByText("ORISTANO · 1/100 · 2025 · Da verificare")).toHaveAttribute("href", expect.stringContaining("pratica=case-1"));
  expect(screen.queryByText("Aggiorna analisi dello storico")).not.toBeInTheDocument();
  expect(screen.queryByText("Successiva")).not.toBeInTheDocument();
});

test("errors, anonymous sessions and cancellation", async () => {
  mocks.request.mockRejectedValue(new Error("Servizio indisponibile"));
  const component = render(<ParcelControlWorkspace annualView={null} />);
  expect(await screen.findByRole("alert")).toHaveTextContent("Servizio indisponibile");
  component.unmount();
  mocks.token = null; mocks.user = null;
  render(<ParcelControlWorkspace annualView={null} />);
  expect(screen.getByText("non ancora eseguita", { exact: false })).toBeInTheDocument();
});

test("mutation errors and expired tokens remain visible", async () => {
  mocks.keys = ["ruolo.tributi.manage_status"]; mocks.user = { role: "admin" };
  render(<ParcelControlWorkspace annualView={null} />);
  await screen.findByText("ORISTANO · 1/100");
  mocks.request.mockRejectedValueOnce(new Error("Pratica modificata"));
  fireEvent.click(screen.getByText("Aggiorna analisi dello storico"));
  expect(await screen.findByRole("alert")).toHaveTextContent("Pratica modificata");
  mocks.request.mockRejectedValueOnce("failure");
  fireEvent.click(screen.getByText("Aggiorna analisi dello storico"));
  await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("Operazione non riuscita"));
  mocks.token = null;
  fireEvent.click(screen.getByText("Aggiorna analisi dello storico"));
  expect(screen.getByRole("alert")).toHaveTextContent("Accesso richiesto");
});

test("table distinguishes unknown years, cases and empty results", () => {
  const open = vi.fn();
  const component = render(<ParcelControlTable items={[row(), row({ id: "p2", case_id: "case-1", case_status: "open", cf_anomaly: false, identity_incomplete: false })]} open={open} busy={false} />);
  fireEvent.click(screen.getByText("Apri pratica"));
  expect(open).toHaveBeenCalledWith(expect.objectContaining({ id: "parcel-1" }));
  expect(screen.getByText("Aperta")).toHaveAttribute("href", expect.stringContaining("pratica=case-1"));
  component.rerender(<ParcelControlTable items={[]} open={open} busy />);
  expect(screen.getByText("Nessuna particella in questa vista.", { exact: false })).toBeInTheDocument();
});

test("operator forms preserve separate evidence, proposed matches and decisions", async () => {
  const save = vi.fn().mockResolvedValue(undefined);
  render(<ParcelControlForms practice={practice()} busy={false} save={save} />);
  fireEvent.change(screen.getByLabelText("Fonte"), { target: { value: "AdE" } });
  fireEvent.change(screen.getByLabelText("Riferimento documentale"), { target: { value: "Doc 1" } });
  fireEvent.change(screen.getByLabelText("Data evidenza"), { target: { value: "2025-01-01" } });
  fireEvent.change(screen.getByLabelText("Motivazione"), { target: { value: "Verifica" } });
  fireEvent.submit(screen.getByText("Salva nella pratica").closest("form")!);
  await waitFor(() => expect(save).toHaveBeenCalledWith("evidence", expect.objectContaining({ years: [2025], source: "AdE" }), "Verifica"));
  fireEvent.change(screen.getByLabelText("Azione"), { target: { value: "match" } });
  fireEvent.change(screen.getByLabelText("Evidenza"), { target: { value: "e1" } });
  fireEvent.change(screen.getByLabelText("Motivazione"), { target: { value: "Matching" } });
  fireEvent.submit(screen.getByText("Salva nella pratica").closest("form")!);
  await waitFor(() => expect(save).toHaveBeenCalledWith("match", expect.objectContaining({ evidence_ids: ["e1"], status: "proposed" }), "Matching"));
  fireEvent.change(screen.getByLabelText("Azione"), { target: { value: "proposal" } });
  fireEvent.change(screen.getByLabelText("Intestatario verificato"), { target: { value: "m1" } });
  fireEvent.change(screen.getByLabelText("Motivazione"), { target: { value: "Proposta" } });
  fireEvent.submit(screen.getByText("Salva nella pratica").closest("form")!);
  await waitFor(() => expect(save).toHaveBeenCalledWith("proposal", expect.objectContaining({ year: 2025, match_id: "m1" }), "Proposta"));
  fireEvent.change(screen.getByLabelText("Azione"), { target: { value: "status" } });
  fireEvent.change(screen.getByLabelText("Motivazione"), { target: { value: "Conclusione" } });
  fireEvent.submit(screen.getByText("Salva nella pratica").closest("form")!);
  await waitFor(() => expect(save).toHaveBeenCalledWith("status", { status: "open" }, "Conclusione"));
});

test("SISTER requests, recovery and proposal decisions use saved practice", async () => {
  const save = vi.fn().mockResolvedValue(undefined);
  const component = render(<ParcelControlDetail practice={practice()} editable busy={false} save={save} />);
  fireEvent.click(screen.getByText("Acquisisci immobile estratto"));
  expect(save).toHaveBeenCalledWith("recover", { evidence_id: "e2" }, expect.any(String));
  fireEvent.change(screen.getByLabelText("Ambito effettivo della ricerca"), { target: { value: "Oristano" } });
  fireEvent.change(screen.getAllByLabelText("Motivazione")[0], { target: { value: "Visura" } });
  fireEvent.submit(screen.getByText("Prepara richiesta SISTER").closest("form")!);
  await waitFor(() => expect(save).toHaveBeenCalledWith("visura/richiesta", expect.objectContaining({ scope: "Oristano", request: expect.objectContaining({ search_mode: "immobile" }) }), "Visura"));
  fireEvent.change(screen.getByLabelText("Motivazione decisione"), { target: { value: "Approfondire" } });
  fireEvent.submit(screen.getByText("Registra decisione").closest("form")!);
  await waitFor(() => expect(save).toHaveBeenCalledWith("decision", { proposal_id: "proposal-1", status: "investigating" }, "Approfondire"));
  component.rerender(<ParcelControlDetail practice={{ ...practice(), current: { ...row(), reference: { ...row().reference, sezione: "B" } } }} editable={false} busy save={save} />);
  expect(screen.queryByText("Salva nella pratica")).not.toBeInTheDocument();
  expect(screen.queryByText("Prepara richiesta SISTER")).not.toBeInTheDocument();
});

test("stale network responses cannot replace current view", async () => {
  let resolveRequest: (value: unknown) => void = () => undefined;
  mocks.request.mockReturnValueOnce(new Promise(resolve => { resolveRequest = resolve; }));
  const component = render(<ParcelControlWorkspace annualView={null} />);
  component.unmount();
  await act(async () => { resolveRequest({ items: [], total: 0 }); });
  let rejectRequest: (reason: unknown) => void = () => undefined;
  mocks.request.mockReturnValueOnce(new Promise((_resolve, reject) => { rejectRequest = reject; }));
  const next = render(<ParcelControlWorkspace annualView={null} />);
  next.unmount();
  await act(async () => { rejectRequest(new Error("Cancelled")); });
});

test("all anomalous notices can open cases even without parcel details", async () => {
  mocks.params = new URLSearchParams("vista=cf");
  const notice = { id: "notice-3", year: 2025, codice_cnc: "CNC3", name: "Società", tax_code: { original: "123", anomaly: "incomplete" }, subject_id: null };
  mocks.request.mockResolvedValue({ items: [], notices: [notice, { ...notice, id: "notice-4", codice_cnc: "CNC4", tax_code: { original: null, anomaly: "missing" } }], total: 2 });
  render(<ParcelControlWorkspace annualView={null} />);
  await screen.findByText("CNC3 · 2025");
  expect(mocks.request).toHaveBeenCalledWith("token", "/avvisi?view=cf&page=1&search=");
  mocks.request.mockResolvedValue({ ...practice(), parcel_id: null, original: { occurrences: [], notice } });
  fireEvent.click(screen.getAllByText("Apri pratica dell'avviso")[0]);
  await waitFor(() => expect(mocks.request).toHaveBeenCalledWith("token", "/avvisi/notice-3/pratica", expect.any(Object)));
  await screen.findByText("Società · CF 123");
});

test("empty notice lists and cases with missing tax codes remain readable", async () => {
  mocks.params = new URLSearchParams("vista=cf");
  mocks.request.mockResolvedValue({ items: [], total: 0 });
  const component = render(<ParcelControlWorkspace annualView={null} />);
  await screen.findByText("Sono inclusi anche gli avvisi senza dettaglio delle particelle.");
  expect(screen.queryByText("Apri pratica dell'avviso")).not.toBeInTheDocument();
  component.unmount();
  const missing = { id: "notice-1", year: 2025, codice_cnc: "CNC", name: "Mario", tax_code: { original: null, anomaly: "missing" }, subject_id: null };
  render(<ParcelControlDetail practice={{ ...practice(), parcel_id: null, original: { occurrences: [], notice: missing } }} editable={false} busy={false} save={vi.fn()} />);
  expect(screen.getByText("Mario · CF mancante")).toBeInTheDocument();
});

test("individual parcel outcome is saved independently from practice status", async () => {
  const save = vi.fn().mockResolvedValue(undefined);
  render(<ParcelControlForms practice={{ ...practice(), parcel_id: null }} busy={false} save={save} />);
  fireEvent.change(screen.getByLabelText("Azione"), { target: { value: "parcel_status" } });
  fireEvent.change(screen.getByLabelText("Esito immobile"), { target: { value: "excluded" } });
  fireEvent.change(screen.getByLabelText("Motivazione"), { target: { value: "Immobile escluso" } });
  fireEvent.submit(screen.getByText("Salva nella pratica").closest("form")!);
  await waitFor(() => expect(save).toHaveBeenCalledWith("parcel_status", { parcel_id: "recovered-1", status: "excluded" }, "Immobile escluso"));
  fireEvent.change(screen.getByLabelText("Azione"), { target: { value: "proposal" } });
  expect(screen.getByLabelText("Particella")).toBeInTheDocument();
});

test("recovery retains the link to its originating request", () => {
  const save = vi.fn();
  const value = practice();
  value.evidence = [];
  value.visure[0].extraction = {};
  render(<ParcelControlDetail practice={value} editable busy={false} save={save} />);
  fireEvent.click(screen.getByText("Acquisisci immobile estratto"));
  expect(save).toHaveBeenCalledWith("recover", { evidence_id: undefined }, expect.any(String));
});

test("changed source data require a new analysis before evaluating absences", async () => {
  mocks.request.mockResolvedValue({ items: [row()], total: 1, sources_changed: true });
  render(<ParcelControlWorkspace annualView={null} />);
  expect(await screen.findByText("Le fonti sono cambiate:", { exact: false })).toBeInTheDocument();
});
