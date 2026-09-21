import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import NoticeRegisterPage from "@/app/ruolo/tributi/registro-avvisi/page";
import { getModuleSections } from "@/components/layout/navigation";
import { DocumentDetail } from "@/components/ruolo/notice-register/document-detail";
import { RegisterTimeline } from "@/components/ruolo/notice-register/timeline";
import type { RegisterDetail } from "@/types/notice-register";
import { candidateFixture, evidenceFixture, jsonResponse, noticeFixture, positionFixture } from "./notice-register-fixtures";

const auth = vi.hoisted(() => ({ useSession: vi.fn() }));
vi.mock("@/lib/use-session-bootstrap", () => ({ useSessionBootstrap: auth.useSession }));
vi.mock("@/components/ruolo/module-page", () => ({ RuoloModulePage: ({ children, requiredSection }: { children: ReactNode; requiredSection: string }) => <main data-section={requiredSection}>{children}</main> }));

let document: RegisterDetail;
let total: number;
let writeStatus: number;
let writes: { url: string; method: string; body: { data: Record<string, unknown>; reason: string; expected_version: number } }[];
let fetchMock: ReturnType<typeof vi.fn>;
let candidateTotal: number;
let evidenceTotal: number;
let candidates: typeof candidateFixture[];

function session(overrides: Record<string, unknown> = {}) {
  return { status: "ready", token: "token", currentUser: { role: "admin", enabled_modules: ["ruolo"] },
    grantedSectionKeys: ["ruolo.tributi.view", "ruolo.tributi.manage_status"], ...overrides };
}

function fakeGet(url: URL) {
  const page = Number(url.searchParams.get("page") ?? 1);
  const pack = (items: unknown[], count: number) => ({ items: page === 1 ? items : [], total: count, page, page_size: 10 });
  if (url.pathname.endsWith("/importazioni")) return pack([], 0);
  if (url.pathname.endsWith("/candidati")) return pack(candidates, candidateTotal);
  if (url.pathname.endsWith("/evidenze")) return pack([evidenceFixture], evidenceTotal);
  if (url.pathname.endsWith("/invii")) return pack([{ id: "attempt-1", channel: "Posta", tracking_code: null, sent_at: null, source_system: "poste" }], 1);
  if (url.pathname.endsWith("/storico")) return pack([{ id: "audit-1", version: 1, actor_id: 7, action: "create_document", reason: "Verifica archivio", created_at: "2026-09-17", before_json: {}, after_json: { number: "original" } }], 11);
  if (url.pathname.endsWith(`/${document.id}`)) return document;
  return pack([document], total);
}

beforeEach(() => {
  document = noticeFixture(); total = 1; writeStatus = 200; candidateTotal = 1; evidenceTotal = 1;
  candidates = [{ ...candidateFixture }]; writes = [];
  auth.useSession.mockReturnValue(session());
  fetchMock = vi.fn(async (input: string, init: RequestInit) => {
    const url = new URL(input, "http://localhost");
    if (init.method) {
      const body = JSON.parse(String(init.body));
      writes.push({ url: url.pathname, method: init.method, body });
      if (writeStatus !== 200) return jsonResponse({ detail: "Verifica dati inseriti" }, writeStatus);
      document.version += 1;
      return jsonResponse({ document_id: document.id, resource_id: "resource-1", version: document.version });
    }
    return jsonResponse(fakeGet(url));
  });
  vi.stubGlobal("fetch", fetchMock);
});

afterEach(() => { cleanup(); vi.unstubAllGlobals(); vi.restoreAllMocks(); });

async function openDocument() {
  render(<NoticeRegisterPage />);
  fireEvent.click(await screen.findByRole("button", { name: "Apri CUM-2022-2023" }));
  await screen.findByRole("heading", { name: "CUM-2022-2023" });
}

function openForm(summary: string, name: string) {
  fireEvent.click(screen.getByText(summary, { selector: "summary" }));
  return screen.getByRole("form", { name });
}

function input(form: HTMLElement, label: string, value: string) {
  fireEvent.change(within(form).getByLabelText(label), { target: { value } });
}

async function save(form: HTMLElement) {
  input(form, "Motivo della registrazione o correzione", "Controllo fascicolo");
  fireEvent.submit(form);
  await screen.findByText("Registrazione salvata. Verifica lo stato aggiornato.");
  await screen.findByRole("heading", { name: "CUM-2022-2023" });
}

describe("registro avvisi workspace", () => {
  it("exposes navigation and read-only views without import/send controls", async () => {
    auth.useSession.mockReturnValue(session({ grantedSectionKeys: ["ruolo.tributi.view"] }));
    render(<NoticeRegisterPage />);
    expect(screen.getByRole("main")).toHaveAttribute("data-section", "ruolo.tributi.view");
    expect(await screen.findByText("Accesso in sola lettura.")).toBeVisible();
    expect(screen.queryByRole("button", { name: "Registra avviso storico" })).toBeNull();
    const sections = getModuleSections({ currentModuleKey: "ruolo" }).flatMap((s) => s.items);
    expect(sections).toContainEqual(expect.objectContaining({ href: "/ruolo/tributi/registro-avvisi", label: "Registro avvisi" }));
    fireEvent.click(screen.getByRole("button", { name: "Anomalie" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("view=anomalie"), expect.anything()));
    fireEvent.click(screen.getByRole("button", { name: "Affidamenti" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("view=affidamenti"), expect.anything()));
    fireEvent.click(screen.getByRole("button", { name: "Importazioni" }));
    expect(screen.getByRole("heading", { name: "Importazioni Excel e Poste" })).toBeVisible();
    expect(screen.queryByRole("button", { name: "Prepara anteprima Excel" })).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Tutti gli avvisi" }));
    fireEvent.click(await screen.findByRole("button", { name: "Apri CUM-2022-2023" }));
    await screen.findByText("Documento senza posizioni. Aggiungi i riferimenti annuali prima del collegamento.");
    expect(screen.queryByLabelText("Operazioni documento")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Torna al registro" }));
    expect(await screen.findByRole("button", { name: "Apri CUM-2022-2023" })).toBeVisible();
  });

  it.each([
    { status: "checking" }, { token: null }, { currentUser: null },
  ])("does not request data before session is ready: %j", async (override) => {
    auth.useSession.mockReturnValue(session(override));
    render(<NoticeRegisterPage />);
    expect(screen.getByRole("status")).toHaveTextContent("Verifica accesso");
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it.each([
    { currentUser: { role: "admin", enabled_modules: [] } }, { grantedSectionKeys: [] },
  ])("fails closed for missing module or section: %j", (override) => {
    auth.useSession.mockReturnValue(session(override));
    render(<NoticeRegisterPage />);
    expect(screen.getByRole("alert")).toHaveTextContent("non autorizzato");
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("allows super-admin module exemption but still checks sections", async () => {
    auth.useSession.mockReturnValue(session({ currentUser: { role: "super_admin", enabled_modules: [] } }));
    render(<NoticeRegisterPage />);
    expect(await screen.findByRole("button", { name: "Apri CUM-2022-2023" })).toBeVisible();
  });

  it("applies all filters, resets page and supports refresh", async () => {
    total = 21;
    render(<NoticeRegisterPage />);
    await screen.findByRole("button", { name: "Apri CUM-2022-2023" });
    fireEvent.click(screen.getByRole("button", { name: "Successiva" }));
    await screen.findByText("Nessun documento per i filtri selezionati.");
    fireEvent.click(screen.getByRole("button", { name: "Precedente" }));
    await screen.findByRole("button", { name: "Apri CUM-2022-2023" });
    const form = screen.getByRole("form", { name: "Filtri registro" });
    input(form, "Numero, CF, riferimento o tracking", "  RIF%_  "); input(form, "Annualita", "2022");
    input(form, "Notifica", "perfezionata"); input(form, "STEP", "affidato");
    fireEvent.submit(form);
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("q=RIF%25_&tax_year=2022&notification_state=perfezionata&recovery_state=affidato"), expect.anything()));
    fireEvent.click(screen.getByRole("button", { name: "Ricarica elenco" }));
    await screen.findByRole("button", { name: "Apri CUM-2022-2023" });
  });

  it("handles load failure and retry without displaying stale records", async () => {
    fetchMock.mockRejectedValueOnce(new Error("Backend indisponibile"));
    render(<NoticeRegisterPage />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Backend indisponibile");
    expect(screen.queryByRole("button", { name: "Apri CUM-2022-2023" })).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Ricarica elenco" }));
    await screen.findByRole("button", { name: "Apri CUM-2022-2023" });
  });

  it("creates a historical document and opens its returned identity", async () => {
    render(<NoticeRegisterPage />);
    fireEvent.click(screen.getByRole("button", { name: "Registra avviso storico" }));
    const form = screen.getByRole("form", { name: "Nuovo avviso storico" });
    input(form, "Numero documento", "LEGACY-001"); input(form, "Codice fiscale destinatario", "TESTCF");
    input(form, "Data emissione", "2024-06-01"); input(form, "Motivo della registrazione o correzione", "Inserimento storico");
    fireEvent.submit(form);
    await screen.findByRole("heading", { name: "CUM-2022-2023" });
    expect(writes[0]).toMatchObject({ method: "POST", body: { expected_version: 1, reason: "Inserimento storico", data: { document_number: "LEGACY-001", tax_code: "TESTCF", issued_on: "2024-06-01" } } });
  });

  it("can leave the new document form without registering data", async () => {
    render(<NoticeRegisterPage />);
    fireEvent.click(screen.getByRole("button", { name: "Registra avviso storico" }));
    fireEvent.click(screen.getByRole("button", { name: "Torna al registro" }));
    await screen.findByRole("button", { name: "Apri CUM-2022-2023" });
    expect(writes).toHaveLength(0);
  });

  it("renders missing metadata and unknown anomalies without claiming notification", async () => {
    document = noticeFixture({ tax_code: null, issued_on: null, notification: null, anomalies: ["future_anomaly"] });
    await openDocument();
    expect(screen.getByText(/CF non disponibile.*Data assente/)).toBeVisible();
    expect(screen.getByText("future_anomaly")).toBeVisible();
    fireEvent.click(screen.getByText("Documento originale (sola lettura)"));
    expect(screen.getByText(/"archivio"/)).toBeVisible();
  });

  it("revises metadata with original version and reloads after save", async () => {
    await openDocument();
    const form = openForm("Correggi documento storico", "Correggi documento");
    input(form, "Numero documento", "CORRETTO");
    await save(form);
    expect(writes[0].body.expected_version).toBe(1);
    expect(writes[0].body.data.document_number).toBe("CORRETTO");
    expect(screen.getByText("Origine: manual | Versione: 2")).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "Ricarica documento" }));
    await screen.findByRole("heading", { name: "CUM-2022-2023" });
  });

  it("adds a position preserving leading zeros and registers an evidence", async () => {
    await openDocument();
    let form = openForm("Aggiungi posizione annuale", "Nuova posizione");
    input(form, "Riferimento annuale originale", "020220001834880"); input(form, "Annualita", "2022");
    await save(form);
    expect(writes[0].body.data).toEqual({ source_namespace: "incass", source_reference: "020220001834880", tax_year: 2022 });
    form = openForm("Registra evidenza", "Nuova evidenza");
    input(form, "Tipo evidenza", "ricevuta"); input(form, "Riferimento ricevuta o documento", "Fascicolo 42");
    await save(form);
    expect(writes[1].body.data).toEqual({ kind: "ricevuta", reference: "Fascicolo 42", occurred_on: null });
  });

  it("selects evidence from this document and registers notification", async () => {
    evidenceTotal = 21;
    await openDocument();
    const form = openForm("Valuta notifica", "Valutazione notifica");
    input(form, "Valutazione notifica", "perfezionata"); input(form, "Data perfezionamento", "2024-06-29");
    await screen.findByRole("option", { name: "Ricevuta: Fascicolo 42" });
    input(form, "Evidenza del documento", "evidence-1");
    fireEvent.click(within(form).getByRole("button", { name: "Altre evidenze" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("evidenze?page=2&page_size=20"), expect.anything()));
    fireEvent.click(within(form).getByRole("button", { name: "Evidenze precedenti" }));
    await save(form);
    expect(writes[0].body.data).toEqual({ state: "perfezionata", notified_on: "2024-06-29", evidence_id: "evidence-1" });
  });

  it("clears the notification date for a non-perfected assessment", async () => {
    document.notification = { state: "perfezionata", notified_on: "2024-06-29", evidence_id: "evidence-1" };
    await openDocument();
    const form = openForm("Valuta notifica", "Valutazione notifica");
    input(form, "Valutazione notifica", "da_verificare");
    await save(form);
    expect(writes[0].body.data.notified_on).toBeNull();
  });

  it("shows a conflict and does not silently replace the submitted version", async () => {
    writeStatus = 409;
    await openDocument();
    const form = openForm("Correggi documento storico", "Correggi documento");
    input(form, "Motivo della registrazione o correzione", "Correzione");
    fireEvent.submit(form);
    expect(await screen.findByRole("alert")).toHaveTextContent("Conflitto");
    expect(writes[0].body.expected_version).toBe(1);
    expect(screen.getByText("Origine: manual | Versione: 1")).toBeVisible();
    writeStatus = 200;
    await save(form);
  });

  it("shows errors on document reads and supports retry", async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse({ detail: "Documento non trovato" }, 404));
    render(<DocumentDetail token="token" documentId="doc-1" canEdit={false} onSelect={vi.fn()} />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Documento non trovato");
    fireEvent.click(screen.getByRole("button", { name: "Ricarica documento" }));
    await act(async () => {});
  });
});

describe("posizioni e timeline", () => {
  it("searches, compares and explicitly confirms a candidate", async () => {
    document.positions = [positionFixture()];
    candidateTotal = 11;
    await openDocument();
    fireEvent.click(screen.getByText("Cerca e collega avviso"));
    const search = screen.getByRole("form", { name: "Cerca avviso da collegare" });
    input(search, "CNC, CF, nominativo o UUID", "TESTCF"); fireEvent.submit(search);
    fireEvent.click(await screen.findByRole("button", { name: "Seleziona CNC-2022-001" }));
    const form = screen.getByRole("form", { name: "Conferma collegamento" });
    expect(within(form).getByRole("checkbox")).toBeRequired();
    fireEvent.click(within(form).getByRole("checkbox"));
    await save(form);
    expect(writes[0].body.data).toEqual({ avviso_id: "avviso-1", confirmed: true });
    expect(writes[0].url).toContain("/posizioni/pos-1/collegamento");
  });

  it("paginates candidates, clears selection, handles absent candidate metadata and linked results", async () => {
    document.positions = [positionFixture({ recovery: null })]; candidateTotal = 11;
    candidates = [{ ...candidateFixture, nominativo_raw: null, codice_fiscale_raw: null, importo_totale_euro: null } as unknown as typeof candidateFixture,
      { ...candidateFixture, id: "avviso-2", already_linked: true }];
    await openDocument();
    fireEvent.click(screen.getByText("Cerca e collega avviso"));
    const form = screen.getByRole("form", { name: "Cerca avviso da collegare" });
    input(form, "CNC, CF, nominativo o UUID", "CNC"); fireEvent.submit(form);
    expect(await screen.findByText("Nominativo assente | CF assente")).toBeVisible();
    expect(screen.getByRole("button", { name: "Gia collegato" })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "Seleziona CNC-2022-001" }));
    expect(screen.getByText(/Collega CNC.*Nominativo assente/)).toBeVisible();
    const position = screen.getByLabelText("Posizioni annuali");
    fireEvent.click(within(position).getByRole("button", { name: "Successiva" }));
    await screen.findByText("Nessun candidato. Il riferimento Incass non e un codice CNC.");
    expect(screen.queryByRole("form", { name: "Conferma collegamento" })).toBeNull();
    fireEvent.click(within(position).getByRole("button", { name: "Precedente" }));
    await screen.findByRole("button", { name: "Gia collegato" });
  });

  it("unlinks with confirmation and revises the annual reference", async () => {
    document.positions = [positionFixture({ avviso_id: "avviso-1", avviso: candidateFixture,
      recovery: { state: "affidato", case_reference: "STEP-42", verified_on: "2026-09-01", evidence_reference: "Report verificato", amount: "123.45" } })];
    await openDocument();
    expect(screen.getByRole("link", { name: "CNC-2022-001" })).toHaveAttribute("href", "/ruolo/tributi/avviso-1");
    let form = openForm("Scollega avviso", "Conferma scollegamento");
    fireEvent.click(within(form).getByRole("checkbox")); await save(form);
    expect(writes[0].body.data).toEqual({ avviso_id: null, confirmed: true });
    form = openForm("Correggi riferimento annuale", "Correggi posizione");
    input(form, "Annualita", "2023"); await save(form);
    expect(writes[1].body.data.tax_year).toBe(2023);
    form = openForm("Registra verifica STEP", "Verifica STEP");
    input(form, "Valutazione STEP", "chiuso"); await save(form);
    expect(writes[2].body.data).toMatchObject({ state: "chiuso", case_reference: "STEP-42", amount: "123.45" });
  });

  it("keeps position operations hidden for viewers", async () => {
    document.positions = [positionFixture()];
    auth.useSession.mockReturnValue(session({ grantedSectionKeys: ["ruolo.tributi.view"] }));
    await openDocument();
    expect(screen.queryByText("Registra verifica STEP")).toBeNull();
  });

  it("presents evidence, attempts, audit and empty event pages", async () => {
    render(<RegisterTimeline token="token" documentId="doc-1" />);
    expect(await screen.findByText("Fascicolo 42")).toBeVisible();
    fireEvent.click(screen.getByText("Evidenza originale"));
    expect(screen.getByText(/29\/06\/204/)).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "invii" }));
    expect(await screen.findByText("Posta | Tracking assente")).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "storico" }));
    expect(await screen.findByText("Verifica archivio")).toBeVisible();
    fireEvent.click(screen.getByText("Valori precedenti")); fireEvent.click(screen.getByText("Valori successivi"));
    fireEvent.click(screen.getByRole("button", { name: "Successiva" }));
    await screen.findByText("Nessun evento registrato.");
    fireEvent.click(screen.getByRole("button", { name: "Precedente" }));
    await screen.findByText("Verifica archivio");
    fireEvent.click(screen.getByRole("button", { name: "Ricarica eventi" }));
    await screen.findByText("Verifica archivio");
  });
});
