import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import UtenzeSubjectDetailPage from "@/app/utenze/[id]/page";
import type {
  AnagraficaCatastoDocument,
  AnagraficaCompany,
  AnagraficaPerson,
  AnagraficaSubjectDetail,
  AnprSubjectStatus,
  CurrentUser,
  ElaborazioneBatchDetail,
} from "@/types/api";

const api = vi.hoisted(() => ({
  router: { push: vi.fn(), replace: vi.fn() },
  getStoredAccessToken: vi.fn(), clearStoredAccessToken: vi.fn(),
  getCurrentUser: vi.fn<typeof import("@/lib/api").getCurrentUser>(),
  getMyPermissions: vi.fn<typeof import("@/lib/api").getMyPermissions>(),
  getUtenzeSubject: vi.fn<typeof import("@/lib/api").getUtenzeSubject>(),
  getUtenzeSubjectPaymentNotices: vi.fn<typeof import("@/lib/api").getUtenzeSubjectPaymentNotices>(),
  getUtenzeSubjectNasImportStatus: vi.fn<typeof import("@/lib/api").getUtenzeSubjectNasImportStatus>(),
  getUtenzeAnprStatus: vi.fn<typeof import("@/lib/api").getUtenzeAnprStatus>(),
  createElaborazioneRichiesta: vi.fn<typeof import("@/lib/api").createElaborazioneRichiesta>(),
  sendPresenceHeartbeat: vi.fn<typeof import("@/lib/api").sendPresenceHeartbeat>(),
}));

vi.mock("next/navigation", () => ({
  useParams: () => ({ id: "subject-r102" }), useRouter: () => api.router,
  useSearchParams: () => new URLSearchParams(window.location.search),
  usePathname: () => window.location.pathname,
}));
vi.mock("@/lib/auth", () => ({
  getStoredAccessToken: api.getStoredAccessToken, clearStoredAccessToken: api.clearStoredAccessToken,
}));
vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  getCurrentUser: api.getCurrentUser, getMyPermissions: api.getMyPermissions,
  getUtenzeSubject: api.getUtenzeSubject,
  getUtenzeSubjectPaymentNotices: api.getUtenzeSubjectPaymentNotices,
  getUtenzeSubjectNasImportStatus: api.getUtenzeSubjectNasImportStatus,
  getUtenzeAnprStatus: api.getUtenzeAnprStatus,
  createElaborazioneRichiesta: api.createElaborazioneRichiesta,
  sendPresenceHeartbeat: api.sendPresenceHeartbeat,
}));

const token = "r102-visura-token";
const timestamp = "2026-10-15T09:00:00Z";
const dayMs = 24 * 60 * 60 * 1000;

function personFixture(overrides: Partial<AnagraficaPerson> = {}): AnagraficaPerson {
  return {
    subject_id: "subject-r102", cognome: "Rossi", nome: "Mario", codice_fiscale: "  rssmra80a01h501u  ",
    anpr_id: null, stato_anpr: null, data_decesso: null, luogo_decesso_comune: null,
    last_anpr_check_at: null, last_c030_check_at: null, data_nascita: null,
    comune_nascita: null, indirizzo: null, comune_residenza: null, cap: null,
    email: null, telefono: null, note: null, created_at: timestamp, updated_at: timestamp,
    ...overrides,
  };
}
function companyFixture(overrides: Partial<AnagraficaCompany> = {}): AnagraficaCompany {
  return {
    subject_id: "subject-r102", ragione_sociale: "  Azienda R102  ", partita_iva: "  12345678901  ",
    codice_fiscale: "  cf-azienda-r102  ", forma_giuridica: null, sede_legale: null,
    comune_sede: null, cap: null, email_pec: null, telefono: null, note: null,
    created_at: timestamp, updated_at: timestamp, ...overrides,
  };
}
function subjectFixture(overrides: Partial<AnagraficaSubjectDetail> = {}): AnagraficaSubjectDetail {
  return {
    id: "subject-r102", subject_type: "person", status: "active", source_system: "campaign-r102",
    source_external_id: null, source_name_raw: "Intestazione originale R102", nas_folder_path: null,
    nas_folder_letter: null, requires_review: false, imported_at: null,
    created_at: timestamp, updated_at: timestamp, person: personFixture(), company: null,
    documents: [], catasto_documents: [], audit_log: [], ...overrides,
  };
}
function userFixture(): CurrentUser {
  return {
    id: 102, username: "r102", email: "r102@example.invalid", role: "viewer", is_active: true,
    module_accessi: false, module_rete: false, module_inventario: false, module_catasto: false,
    module_utenze: true, module_operazioni: false, module_riordino: false,
    module_ruolo: false, module_presenze: false, enabled_modules: ["utenze"],
  };
}
function batchFixture(id = "batch-r102"): ElaborazioneBatchDetail {
  return {
    id, user_id: 102, name: `Visura ${id}`, status: "pending", total_items: 1,
    completed_items: 0, failed_items: 0, skipped_items: 0, not_found_items: 0,
    source_filename: null, current_operation: null, report_json_path: null, report_md_path: null,
    created_at: timestamp, started_at: null, completed_at: null, requests: [],
  };
}
function visuraFixture(id: string, createdAt: string): AnagraficaCatastoDocument {
  return {
    id, request_id: null, comune: "ORISTANO", foglio: "1", particella: "2",
    subalterno: null, catasto: "Terreni", tipo_visura: "Sintetica", filename: `${id}.pdf`,
    codice_fiscale: "RSSMRA80A01H501U", created_at: createdAt,
  };
}
function deferred<Result>() {
  let resolve!: (value: Result) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<Result>((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}
async function ready(subject = subjectFixture(), embedded = true) {
  window.history.replaceState(null, "", `/utenze/subject-r102${embedded ? "?embedded=1" : ""}`);
  api.getUtenzeSubject.mockResolvedValue(subject);
  const person = subject.person;
  const status: AnprSubjectStatus = {
    subject_id: subject.id, anpr_id: person?.anpr_id ?? null, stato_anpr: person?.stato_anpr ?? null,
    data_decesso: person?.data_decesso ?? null, luogo_decesso_comune: person?.luogo_decesso_comune ?? null,
    last_anpr_check_at: person?.last_anpr_check_at ?? null,
    last_c030_check_at: person?.last_c030_check_at ?? null,
  };
  api.getUtenzeAnprStatus.mockResolvedValue(status);
  render(<UtenzeSubjectDetailPage />);
  await screen.findByText("R102 NAS pronto");
  await act(async () => {});
  expect(api.getUtenzeSubject).toHaveBeenCalledExactlyOnceWith(token, "subject-r102");
  expect(api.createElaborazioneRichiesta).not.toHaveBeenCalled();
  expect(screen.getByText("Visura per soggetto")).toBeVisible();
}
function visuraCard() {
  const card = screen.getByText("Visura per soggetto").closest(".rounded-2xl");
  if (!(card instanceof HTMLElement)) throw new Error("Missing real Visura card");
  return within(card);
}
function requestVisura() {
  const button = screen.getByRole("button", { name: "Richiedi visura" });
  expect(button).toBeEnabled();
  fireEvent.click(button);
}
function expectPayload(subjectKind: "PF" | "PNF", identifier: string, intestazione: string) {
  expect(api.createElaborazioneRichiesta).toHaveBeenCalledExactlyOnceWith(token, {
    search_mode: "soggetto", tipo_visura: "Sintetica", subject_kind: subjectKind,
    subject_id: identifier, request_type: "ATTUALITA", intestazione,
  });
}
async function expectCompleted(id = "batch-r102") {
  expect(await screen.findByText(`Richiesta visura avviata sul batch Visura ${id}.`)).toBeVisible();
  await waitFor(() => expect(screen.getByRole("button", { name: "Richiedi visura" })).toBeEnabled());
  expect(screen.queryByRole("button", { name: "Richiesta in corso..." })).not.toBeInTheDocument();
}

beforeEach(() => {
  vi.resetAllMocks();
  api.getStoredAccessToken.mockReturnValue(token);
  api.getCurrentUser.mockResolvedValue(userFixture());
  api.getMyPermissions.mockResolvedValue({ sections: [], granted_keys: [] });
  api.getUtenzeSubjectPaymentNotices.mockResolvedValue([]);
  api.getUtenzeSubjectNasImportStatus.mockResolvedValue({
    can_import_from_nas: false, missing_in_nas: true, matched_folder_path: null,
    matched_folder_name: null, total_files_in_nas: 0, pending_files_in_nas: 0, message: "R102 NAS pronto",
  });
  api.createElaborazioneRichiesta.mockResolvedValue(batchFixture());
  api.sendPresenceHeartbeat.mockResolvedValue({ ok: true, last_seen_at: timestamp });
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

describe("R102 real mounted subject Visura lifecycle", () => {
  test("PF normalizes CF and outer name whitespace, then navigates outside embedded mode", async () => {
    await ready(subjectFixture({ person: personFixture({ cognome: " Rossi", nome: "Mario " }) }), false);
    expect(visuraCard().getByText("Codice fiscale: RSSMRA80A01H501U")).toBeVisible();
    expect(screen.getByText("PF")).toBeVisible();
    requestVisura();
    await expectCompleted();
    expectPayload("PF", "RSSMRA80A01H501U", "Rossi Mario");
    expect(api.router.push).toHaveBeenCalledExactlyOnceWith("/elaborazioni/batches/batch-r102");
    expect(api.router.replace).not.toHaveBeenCalled();
    expect(screen.queryByRole("button", { name: "Apri batch" })).not.toBeInTheDocument();
    expect(api.sendPresenceHeartbeat).toHaveBeenCalled();
  });

  test("PF falls back to the raw source name only when both person names are blank", async () => {
    await ready(subjectFixture({ person: personFixture({ cognome: " ", nome: " " }) }));
    requestVisura();
    await expectCompleted();
    expectPayload("PF", "RSSMRA80A01H501U", "Intestazione originale R102");
    expect(api.router.push).not.toHaveBeenCalled();
  });

  test("PNF prefers trimmed PIVA over a different CF and trims company name", async () => {
    await ready(subjectFixture({ subject_type: "company", person: null, company: companyFixture() }));
    expect(screen.getByText("Partita IVA: 12345678901")).toBeVisible();
    expect(screen.getByText("PNF")).toBeVisible();
    requestVisura();
    await expectCompleted();
    expectPayload("PNF", "12345678901", "Azienda R102");
    expect(api.router.push).not.toHaveBeenCalled();
  });

  test.each(["", "   "])("PNF with PIVA %j falls back to normalized CF and raw company name", async (partitaIva) => {
    await ready(subjectFixture({
      subject_type: "company", person: null,
      company: companyFixture({ partita_iva: partitaIva, ragione_sociale: "  " }),
    }));
    expect(visuraCard().getByText("Codice fiscale: CF-AZIENDA-R102")).toBeVisible();
    requestVisura();
    await expectCompleted();
    expectPayload("PNF", "CF-AZIENDA-R102", "Intestazione originale R102");
  });

  test.each([
    { name: "PF blank CF", subject: subjectFixture({ person: personFixture({ codice_fiscale: "   " }) }) },
    { name: "PNF blank identifiers", subject: subjectFixture({ subject_type: "company", person: null, company: companyFixture({ partita_iva: "  ", codice_fiscale: " " }) }) },
    { name: "PNF absent CF", subject: subjectFixture({ subject_type: "company", person: null, company: companyFixture({ partita_iva: "", codice_fiscale: null }) }) },
    { name: "unknown subject", subject: subjectFixture({ subject_type: "unknown", person: null, company: null }) },
  ])("$name keeps the real request button disabled without calling the API", async ({ subject }) => {
    await ready(subject);
    expect(screen.getByRole("button", { name: "Richiedi visura" })).toBeDisabled();
    expect(screen.getByText("Codice fiscale o partita IVA mancanti")).toBeVisible();
    expect(visuraCard().getByText("Non disponibile")).toBeVisible();
    expect(api.createElaborazioneRichiesta).not.toHaveBeenCalled();
    expect(api.router.push).not.toHaveBeenCalled();
  });

  test("embedded deferred request disables duplicates, opens returned batch and clears old success on a new request", async () => {
    const first = deferred<ElaborazioneBatchDetail>();
    const second = deferred<ElaborazioneBatchDetail>();
    api.createElaborazioneRichiesta.mockReturnValueOnce(first.promise).mockReturnValueOnce(second.promise);
    const open = vi.spyOn(window, "open").mockReturnValue(null);
    await ready();
    requestVisura();
    expect(screen.getByRole("button", { name: "Richiesta in corso..." })).toBeDisabled();
    expect(screen.queryByRole("button", { name: "Richiedi visura" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Apri batch" })).not.toBeInTheDocument();
    expectPayload("PF", "RSSMRA80A01H501U", "Rossi Mario");
    expect(api.router.push).not.toHaveBeenCalled();
    await act(async () => first.resolve(batchFixture()));
    await expectCompleted();
    fireEvent.click(screen.getByRole("button", { name: "Apri batch" }));
    expect(open).toHaveBeenCalledExactlyOnceWith("/elaborazioni/batches/batch-r102", "_blank", "noopener,noreferrer");
    requestVisura();
    expect(screen.queryByText("Richiesta visura avviata sul batch Visura batch-r102.")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Apri batch" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Richiesta in corso..." })).toBeDisabled();
    expect(api.createElaborazioneRichiesta).toHaveBeenCalledTimes(2);
    expect(api.createElaborazioneRichiesta.mock.calls[1]).toEqual(api.createElaborazioneRichiesta.mock.calls[0]);
    await act(async () => second.resolve(batchFixture("batch-r102-second")));
    await expectCompleted("batch-r102-second");
    expect(api.router.push).not.toHaveBeenCalled();
  });

  test.each([
    { name: "Error message", error: new Error("SISTER R102 non disponibile"), message: "SISTER R102 non disponibile" },
    { name: "opaque rejection", error: { reason: "opaque-r102" }, message: "Errore avvio visura per soggetto" },
  ])("$name displays failure, resets pending and clears error during a genuine retry", async ({ error, message }) => {
    const first = deferred<ElaborazioneBatchDetail>();
    const retry = deferred<ElaborazioneBatchDetail>();
    api.createElaborazioneRichiesta.mockReturnValueOnce(first.promise).mockReturnValueOnce(retry.promise);
    await ready();
    requestVisura();
    expect(screen.getByRole("button", { name: "Richiesta in corso..." })).toBeDisabled();
    await act(async () => first.reject(error));
    expect(await screen.findByText(message)).toBeVisible();
    expect(screen.getByRole("button", { name: "Richiedi visura" })).toBeEnabled();
    expect(screen.queryByRole("button", { name: "Apri batch" })).not.toBeInTheDocument();
    expectPayload("PF", "RSSMRA80A01H501U", "Rossi Mario");
    requestVisura();
    expect(screen.queryByText(message)).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Richiesta in corso..." })).toBeDisabled();
    expect(api.createElaborazioneRichiesta).toHaveBeenCalledTimes(2);
    expect(api.createElaborazioneRichiesta.mock.calls[1]).toEqual(api.createElaborazioneRichiesta.mock.calls[0]);
    await act(async () => retry.resolve(batchFixture("batch-r102-retry")));
    await expectCompleted("batch-r102-retry");
    expect(screen.queryByText(message)).not.toBeInTheDocument();
    expect(api.router.push).not.toHaveBeenCalled();
  });

  test.each(["recent-first", "recent-last"])("latest recent visura (%s) requires real cancellation and confirmation", async (order) => {
    const now = Date.now();
    const recent = visuraFixture("recent-r102", new Date(now - dayMs).toISOString());
    const old = visuraFixture("old-r102", new Date(now - 10 * dayMs).toISOString());
    const request = deferred<ElaborazioneBatchDetail>();
    api.createElaborazioneRichiesta.mockReturnValue(request.promise);
    await ready(subjectFixture({ catasto_documents: order === "recent-first" ? [recent, old] : [old, recent] }));
    const card = screen.getByText("Visura per soggetto").closest(".rounded-2xl");
    if (!(card instanceof HTMLElement)) throw new Error("Missing real Visura card");
    expect(within(card).getByText("recent-r102.pdf")).toBeVisible();
    expect(within(card).queryByText("old-r102.pdf")).not.toBeInTheDocument();
    requestVisura();
    const dialog = screen.getByRole("dialog", { name: "Conferma nuova visura" });
    expect(dialog).toBeVisible();
    expect(within(dialog).getByText(/ha meno di 7 giorni/)).toBeVisible();
    expect(api.createElaborazioneRichiesta).not.toHaveBeenCalled();
    fireEvent.click(within(dialog).getByRole("button", { name: "Annulla" }));
    expect(screen.queryByRole("dialog", { name: "Conferma nuova visura" })).not.toBeInTheDocument();
    expect(api.createElaborazioneRichiesta).not.toHaveBeenCalled();
    requestVisura();
    fireEvent.click(within(screen.getByRole("dialog", { name: "Conferma nuova visura" })).getByRole("button", { name: "Conferma richiesta" }));
    expect(screen.queryByRole("dialog", { name: "Conferma nuova visura" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Richiesta in corso..." })).toBeDisabled();
    expectPayload("PF", "RSSMRA80A01H501U", "Rossi Mario");
    await act(async () => request.resolve(batchFixture()));
    await expectCompleted();
    expect(api.router.push).not.toHaveBeenCalled();
  });

  test.each([7, 10])("visura already %i days old requests directly without a confirmation dialog", async (ageDays) => {
    await ready(subjectFixture({
      catasto_documents: [visuraFixture("old-direct-r102", new Date(Date.now() - ageDays * dayMs).toISOString())],
    }));
    expect(screen.getByRole("button", { name: "Visualizza visura" })).toBeVisible();
    requestVisura();
    expect(screen.queryByRole("dialog", { name: "Conferma nuova visura" })).not.toBeInTheDocument();
    await expectCompleted();
    expectPayload("PF", "RSSMRA80A01H501U", "Rossi Mario");
    expect(api.router.push).not.toHaveBeenCalled();
  });
});
