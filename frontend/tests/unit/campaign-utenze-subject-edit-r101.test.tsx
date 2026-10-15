import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import UtenzeSubjectDetailPage from "@/app/utenze/[id]/page";
import type {
  AnagraficaCompany,
  AnagraficaPerson,
  AnagraficaPersonInput,
  AnagraficaSubjectDetail,
  AnagraficaSubjectNasImportStatus,
  AnagraficaSubjectUpdateInput,
  AnprSubjectStatus,
  CurrentUser,
} from "@/types/api";

const api = vi.hoisted(() => ({
  router: { push: vi.fn(), replace: vi.fn() },
  getStoredAccessToken: vi.fn(),
  clearStoredAccessToken: vi.fn(),
  getCurrentUser: vi.fn<typeof import("@/lib/api").getCurrentUser>(),
  getMyPermissions: vi.fn<typeof import("@/lib/api").getMyPermissions>(),
  getUtenzeSubject: vi.fn<typeof import("@/lib/api").getUtenzeSubject>(),
  getUtenzeSubjectPaymentNotices: vi.fn<typeof import("@/lib/api").getUtenzeSubjectPaymentNotices>(),
  getUtenzeSubjectNasImportStatus: vi.fn<typeof import("@/lib/api").getUtenzeSubjectNasImportStatus>(),
  getUtenzeAnprStatus: vi.fn<typeof import("@/lib/api").getUtenzeAnprStatus>(),
  updateUtenzeSubject: vi.fn<typeof import("@/lib/api").updateUtenzeSubject>(),
}));

vi.mock("next/navigation", () => ({
  useParams: () => ({ id: "subject-r101" }),
  useRouter: () => api.router,
  useSearchParams: () => new URLSearchParams(window.location.search),
  usePathname: () => window.location.pathname,
}));
vi.mock("@/lib/auth", () => ({
  getStoredAccessToken: api.getStoredAccessToken,
  clearStoredAccessToken: api.clearStoredAccessToken,
}));
vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  getCurrentUser: api.getCurrentUser,
  getMyPermissions: api.getMyPermissions,
  getUtenzeSubject: api.getUtenzeSubject,
  getUtenzeSubjectPaymentNotices: api.getUtenzeSubjectPaymentNotices,
  getUtenzeSubjectNasImportStatus: api.getUtenzeSubjectNasImportStatus,
  getUtenzeAnprStatus: api.getUtenzeAnprStatus,
  updateUtenzeSubject: api.updateUtenzeSubject,
}));

const token = "r101-subject-edit-token";
const timestamp = "2026-10-15T09:00:00Z";
const emptyPersonPayload: AnagraficaPersonInput = {
  cognome: "Rossi", nome: "Mario", codice_fiscale: "RSSMRA80A01H501U",
  data_nascita: null, comune_nascita: null, indirizzo: null,
  comune_residenza: null, cap: null, email: null, telefono: null, note: null,
  stato_anpr: null, data_decesso: null, luogo_decesso_comune: null,
};
const emptyCompanyPayload: NonNullable<AnagraficaSubjectUpdateInput["company"]> = {
  ragione_sociale: "Società R101", forma_giuridica: null, partita_iva: "12345678901",
  codice_fiscale: null, sede_legale: null, comune_sede: null, cap: null,
  email_pec: null, telefono: null, note: null,
};
const personChanges = [
  ["Cognome / ragione sociale", "Bianchi"], ["Nome", "Anna"],
  ["Codice fiscale", "BNCNNA85B41H501X"], ["Data nascita", "1985-02-01"],
  ["Comune nascita", "Roma"], ["Indirizzo", "Via Nuova 7"],
  ["Comune residenza", "Latina"], ["CAP", "04100"],
  ["Email", "anna@example.invalid"], ["Telefono", "0612345678"],
  ["Note", "Nota persona R101"],
] as const;
const companyChanges = [
  ["Ragione sociale", "Azienda Agricola R101"], ["Forma giuridica", "SRL"],
  ["Partita IVA", "10987654321"], ["Codice fiscale", "99887766554"],
  ["Sede legale", "Via Azienda 9"], ["Comune sede", "Viterbo"],
  ["CAP", "01100"], ["PEC / Email", "azienda@pec.example.invalid"],
  ["Telefono", "0761123456"], ["Note", "Nota azienda R101"],
] as const;

function personFixture(overrides: Partial<AnagraficaPerson> = {}): AnagraficaPerson {
  return {
    subject_id: "subject-r101", cognome: "Rossi", nome: "Mario", codice_fiscale: "RSSMRA80A01H501U",
    anpr_id: null, stato_anpr: null, data_decesso: null, luogo_decesso_comune: null,
    last_anpr_check_at: null, last_c030_check_at: null, data_nascita: null,
    comune_nascita: null, indirizzo: null, comune_residenza: null, cap: null,
    email: null, telefono: null, note: null, created_at: timestamp, updated_at: timestamp,
    ...overrides,
  };
}
function companyFixture(overrides: Partial<AnagraficaCompany> = {}): AnagraficaCompany {
  return {
    subject_id: "subject-r101", ...emptyCompanyPayload,
    created_at: timestamp, updated_at: timestamp, ...overrides,
  };
}
function subjectFixture(overrides: Partial<AnagraficaSubjectDetail> = {}): AnagraficaSubjectDetail {
  return {
    id: "subject-r101", subject_type: "person", status: "active", source_system: "campaign-r101",
    source_external_id: null, source_name_raw: "Rossi Mario", nas_folder_path: null,
    nas_folder_letter: null, requires_review: false, imported_at: null,
    created_at: timestamp, updated_at: timestamp, person: personFixture(), company: null,
    documents: [], catasto_documents: [], audit_log: [], ...overrides,
  };
}
function userFixture(): CurrentUser {
  return {
    id: 101, username: "r101", email: "r101@example.invalid", role: "viewer", is_active: true,
    module_accessi: false, module_rete: false, module_inventario: false, module_catasto: false,
    module_utenze: true, module_operazioni: false, module_riordino: false,
    module_ruolo: false, module_presenze: false, enabled_modules: ["utenze"],
  };
}
function nasFixture(): AnagraficaSubjectNasImportStatus {
  return {
    can_import_from_nas: false, missing_in_nas: true, matched_folder_path: null,
    matched_folder_name: null, total_files_in_nas: 0, pending_files_in_nas: 0,
    message: "R101 NAS pronto",
  };
}
function deferred<Result>() {
  let resolve!: (value: Result) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<Result>((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}
async function ready(subject = subjectFixture()) {
  api.getUtenzeSubject.mockResolvedValue(subject);
  const person = subject.person;
  const anpr: AnprSubjectStatus = {
    subject_id: subject.id, anpr_id: person?.anpr_id ?? null,
    stato_anpr: person?.stato_anpr ?? null, data_decesso: person?.data_decesso ?? null,
    luogo_decesso_comune: person?.luogo_decesso_comune ?? null,
    last_anpr_check_at: person?.last_anpr_check_at ?? null,
    last_c030_check_at: person?.last_c030_check_at ?? null,
  };
  api.getUtenzeAnprStatus.mockResolvedValue(anpr);
  render(<UtenzeSubjectDetailPage />);
  await screen.findByText("R101 NAS pronto");
  await act(async () => {});
  expect(api.getUtenzeSubject).toHaveBeenCalledExactlyOnceWith(token, "subject-r101");
  expect(screen.getByText("Sola lettura")).toBeVisible();
  expect(screen.getByRole("button", { name: "Salva scheda" })).toBeDisabled();
}
function enableEditing() {
  fireEvent.click(screen.getByRole("button", { name: "Modifica" }));
  expect(screen.getByText("Abilita modalità modifica")).toBeVisible();
  expect(screen.getByRole("button", { name: "Salva scheda" })).toBeDisabled();
  fireEvent.click(screen.getByRole("button", { name: "Abilita modifica" }));
  expect(screen.getByText("Modalità modifica attiva")).toBeVisible();
}
function change(name: string, value: string) {
  const field = screen.getByLabelText(name, { exact: true });
  expect(field).toBeVisible();
  expect(field).toBeEnabled();
  expect(field).not.toHaveAttribute("readonly");
  expect(field).not.toHaveValue(value);
  fireEvent.change(field, { target: { value } });
  expect(field).toHaveValue(value);
}
function save() {
  const button = screen.getByRole("button", { name: "Salva scheda" });
  expect(button).toBeEnabled();
  fireEvent.click(button);
}
function expectBusy() {
  expect(screen.getByRole("button", { name: "Salvataggio..." })).toBeDisabled();
  expect(screen.queryByRole("button", { name: "Salva scheda" })).not.toBeInTheDocument();
  expect(api.updateUtenzeSubject).toHaveBeenCalledTimes(1);
}
async function expectSuccess() {
  expect(await screen.findByText("Scheda soggetto aggiornata.")).toBeVisible();
  await waitFor(() => expect(screen.getByRole("button", { name: "Salva scheda" })).toBeDisabled());
  expect(screen.getByText("Sola lettura")).toBeVisible();
  expect(screen.queryByText("Modalità modifica attiva")).not.toBeInTheDocument();
  expect(screen.getByLabelText("Source name raw")).toHaveAttribute("readonly");
  expect(screen.getByLabelText("Stato", { exact: true })).toBeDisabled();
  expect(screen.getByLabelText("Richiede revisione")).toBeDisabled();
}

beforeEach(() => {
  vi.resetAllMocks();
  window.history.replaceState(null, "", "/utenze/subject-r101?embedded=1");
  api.getStoredAccessToken.mockReturnValue(token);
  api.getCurrentUser.mockResolvedValue(userFixture());
  api.getMyPermissions.mockResolvedValue({ sections: [], granted_keys: [] });
  api.getUtenzeSubjectPaymentNotices.mockResolvedValue([]);
  api.getUtenzeSubjectNasImportStatus.mockResolvedValue(nasFixture());
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

describe("R101 real subject hydration and public save transitions", () => {
  test("person edits every field, submits exact payload and uses server hydration after pending edits", async () => {
    const request = deferred<AnagraficaSubjectDetail>();
    api.updateUtenzeSubject.mockReturnValue(request.promise);
    await ready();
    for (const label of personChanges.map(([label]) => label)) {
      expect(screen.getByLabelText(label, { exact: true })).toHaveAttribute("readonly");
    }
    enableEditing();
    change("Source name raw", "Bianchi Anna raw");
    change("Stato", "inactive");
    fireEvent.click(screen.getByLabelText("Richiede revisione"));
    for (const [label, value] of personChanges) change(label, value);
    expect(screen.getByLabelText("Data decesso")).toBeDisabled();
    expect(screen.getByLabelText("Luogo decesso")).toBeDisabled();
    fireEvent.click(screen.getByLabelText("Soggetto deceduto"));
    change("Data decesso", "2026-10-01");
    change("Luogo decesso", "Roma");
    save();
    expectBusy();
    expect(api.updateUtenzeSubject).toHaveBeenCalledExactlyOnceWith(token, "subject-r101", {
      source_name_raw: "Bianchi Anna raw", requires_review: true, status: "inactive",
      person: {
        cognome: "Bianchi", nome: "Anna", codice_fiscale: "BNCNNA85B41H501X",
        data_nascita: "1985-02-01", comune_nascita: "Roma", indirizzo: "Via Nuova 7",
        comune_residenza: "Latina", cap: "04100", email: "anna@example.invalid",
        telefono: "0612345678", note: "Nota persona R101", stato_anpr: "deceased",
        data_decesso: "2026-10-01", luogo_decesso_comune: "Roma",
      },
    });
    change("Nome", "Modifica durante richiesta");
    expect(api.updateUtenzeSubject).toHaveBeenCalledTimes(1);
    await act(async () => request.resolve(subjectFixture({
      source_name_raw: "Risposta server persona", status: "duplicate", requires_review: false,
      person: personFixture({ cognome: "Server", nome: "Confermato", indirizzo: "Via Server 1" }),
    })));
    await expectSuccess();
    expect(screen.getByLabelText("Source name raw")).toHaveValue("Risposta server persona");
    expect(screen.getByLabelText("Cognome / ragione sociale")).toHaveValue("Server");
    expect(screen.getByLabelText("Nome", { exact: true })).toHaveValue("Confermato");
    expect(screen.getByLabelText("Indirizzo")).toHaveValue("Via Server 1");
    expect(screen.getByLabelText("Stato", { exact: true })).toHaveValue("duplicate");
    expect(screen.getByLabelText("Richiede revisione")).not.toBeChecked();
    expect(screen.getByLabelText("Soggetto deceduto")).not.toBeChecked();
    expect(screen.getByLabelText("Data decesso")).toHaveValue("");
  });

  test("populated deceased person hydrates every field and clearing sends nulls without death values", async () => {
    const populated = personFixture({
      data_nascita: "1980-01-01", comune_nascita: "Roma", indirizzo: "Via Vecchia 1",
      comune_residenza: "Roma", cap: "00100", email: "mario@example.invalid",
      telefono: "061111111", note: "Nota preesistente", stato_anpr: "deceased",
      data_decesso: "2026-09-01", luogo_decesso_comune: "Roma",
    });
    api.updateUtenzeSubject.mockResolvedValue(subjectFixture());
    await ready(subjectFixture({ person: populated }));
    const values = [
      ["Data nascita", "1980-01-01"], ["Comune nascita", "Roma"], ["Indirizzo", "Via Vecchia 1"],
      ["Comune residenza", "Roma"], ["CAP", "00100"], ["Email", "mario@example.invalid"],
      ["Telefono", "061111111"], ["Note", "Nota preesistente"],
    ] as const;
    for (const [label, value] of values) expect(screen.getByLabelText(label, { exact: true })).toHaveValue(value);
    expect(screen.getByLabelText("Soggetto deceduto")).toBeChecked();
    expect(screen.getByLabelText("Data decesso")).toHaveValue("2026-09-01");
    expect(screen.getByLabelText("Luogo decesso")).toHaveValue("Roma");
    enableEditing();
    for (const [label] of values) change(label, "");
    fireEvent.click(screen.getByLabelText("Soggetto deceduto"));
    expect(screen.getByLabelText("Soggetto deceduto")).not.toBeChecked();
    for (const label of ["Data decesso", "Luogo decesso"]) {
      expect(screen.getByLabelText(label)).toBeDisabled();
      expect(screen.getByLabelText(label)).toHaveValue("");
    }
    save();
    expect(api.updateUtenzeSubject).toHaveBeenCalledExactlyOnceWith(token, "subject-r101", {
      source_name_raw: "Rossi Mario", requires_review: false, status: "active", person: emptyPersonPayload,
    });
    await expectSuccess();
  });

  test("deceased person with empty death details saves null details and retains the manual flag", async () => {
    api.updateUtenzeSubject.mockResolvedValue(subjectFixture({ person: personFixture({ stato_anpr: "deceased" }) }));
    await ready();
    enableEditing();
    fireEvent.click(screen.getByLabelText("Soggetto deceduto"));
    expect(screen.getByLabelText("Data decesso")).toBeEnabled();
    expect(screen.getByLabelText("Luogo decesso")).toBeEnabled();
    save();
    expect(api.updateUtenzeSubject).toHaveBeenCalledExactlyOnceWith(token, "subject-r101", {
      source_name_raw: "Rossi Mario", requires_review: false, status: "active",
      person: { ...emptyPersonPayload, stato_anpr: "deceased" },
    });
    await expectSuccess();
    expect(screen.getByLabelText("Soggetto deceduto")).toBeChecked();
  });

  test("unchecking and rechecking death cannot restore discarded details", async () => {
    api.updateUtenzeSubject.mockResolvedValue(subjectFixture());
    await ready(subjectFixture({ person: personFixture({
      stato_anpr: "deceased", data_decesso: "2026-09-01", luogo_decesso_comune: "Roma",
    }) }));
    enableEditing();
    expect(screen.getByLabelText("Data decesso")).toHaveValue("2026-09-01");
    fireEvent.click(screen.getByLabelText("Soggetto deceduto"));
    fireEvent.click(screen.getByLabelText("Soggetto deceduto"));
    expect(screen.getByLabelText("Data decesso")).toHaveValue("");
    expect(screen.getByLabelText("Luogo decesso")).toHaveValue("");
    change("Data decesso", "2026-10-02");
    change("Luogo decesso", "Latina");
    save();
    expect(api.updateUtenzeSubject).toHaveBeenCalledExactlyOnceWith(token, "subject-r101", {
      source_name_raw: "Rossi Mario", requires_review: false, status: "active",
      person: { ...emptyPersonPayload, stato_anpr: "deceased", data_decesso: "2026-10-02", luogo_decesso_comune: "Latina" },
    });
    await expectSuccess();
  });

  test("company null hydration, all public fields, exact payload and server read-only replacement", async () => {
    const request = deferred<AnagraficaSubjectDetail>();
    api.updateUtenzeSubject.mockReturnValue(request.promise);
    await ready(subjectFixture({ subject_type: "company", person: null, company: companyFixture() }));
    for (const label of ["Forma giuridica", "Codice fiscale", "Sede legale", "Comune sede", "CAP", "PEC / Email", "Telefono", "Note"]) {
      expect(screen.getByLabelText(label, { exact: true })).toHaveValue("");
    }
    expect(api.getUtenzeAnprStatus).not.toHaveBeenCalled();
    enableEditing();
    change("Source name raw", "Società da verificare");
    change("Stato", "duplicate");
    fireEvent.click(screen.getByLabelText("Richiede revisione"));
    for (const [label, value] of companyChanges) change(label, value);
    save();
    expectBusy();
    expect(api.updateUtenzeSubject).toHaveBeenCalledExactlyOnceWith(token, "subject-r101", {
      source_name_raw: "Società da verificare", requires_review: true, status: "duplicate",
      company: {
        ragione_sociale: "Azienda Agricola R101", forma_giuridica: "SRL", partita_iva: "10987654321",
        codice_fiscale: "99887766554", sede_legale: "Via Azienda 9", comune_sede: "Viterbo",
        cap: "01100", email_pec: "azienda@pec.example.invalid", telefono: "0761123456", note: "Nota azienda R101",
      },
    });
    await act(async () => request.resolve(subjectFixture({
      subject_type: "company", person: null, source_name_raw: "Società approvata", requires_review: false,
      company: companyFixture({ ragione_sociale: "Denominazione dal server", forma_giuridica: "SPA", note: "Nota server" }),
    })));
    await expectSuccess();
    expect(screen.getByLabelText("Ragione sociale")).toHaveValue("Denominazione dal server");
    expect(screen.getByLabelText("Forma giuridica")).toHaveValue("SPA");
    expect(screen.getByLabelText("Note")).toHaveValue("Nota server");
    expect(screen.getByLabelText("Source name raw")).toHaveValue("Società approvata");
  });

  test("populated company hydration and clearing optional fields produce an exact nullable company payload", async () => {
    const company = companyFixture({
      forma_giuridica: "SRL", codice_fiscale: "99887766554", sede_legale: "Via Vecchia 2",
      comune_sede: "Roma", cap: "00100", email_pec: "societa@pec.example.invalid",
      telefono: "062222222", note: "Nota precedente",
    });
    const subject = subjectFixture({ subject_type: "company", person: null, company });
    api.updateUtenzeSubject.mockResolvedValue(subjectFixture({ subject_type: "company", person: null, company: companyFixture() }));
    await ready(subject);
    const values = [
      ["Forma giuridica", "SRL"], ["Codice fiscale", "99887766554"], ["Sede legale", "Via Vecchia 2"],
      ["Comune sede", "Roma"], ["CAP", "00100"], ["PEC / Email", "societa@pec.example.invalid"],
      ["Telefono", "062222222"], ["Note", "Nota precedente"],
    ] as const;
    for (const [label, value] of values) expect(screen.getByLabelText(label, { exact: true })).toHaveValue(value);
    enableEditing();
    for (const [label] of values) change(label, "");
    save();
    expect(api.updateUtenzeSubject).toHaveBeenCalledExactlyOnceWith(token, "subject-r101", {
      source_name_raw: "Rossi Mario", requires_review: false, status: "active", company: emptyCompanyPayload,
    });
    await expectSuccess();
  });

  test.each([
    [new Error("R101 salvataggio rifiutato"), "R101 salvataggio rifiutato"],
    [null, "Errore salvataggio soggetto"],
  ])("failed save retains draft and next request clears feedback before server recovery: %s", async (failure, message) => {
    const rejected = deferred<AnagraficaSubjectDetail>();
    const retry = deferred<AnagraficaSubjectDetail>();
    api.updateUtenzeSubject.mockReturnValueOnce(rejected.promise).mockReturnValueOnce(retry.promise);
    await ready();
    enableEditing();
    change("Email", "bozza@example.invalid");
    save();
    expectBusy();
    await act(async () => rejected.reject(failure));
    expect(await screen.findByText(message)).toBeVisible();
    expect(screen.queryByText("Scheda soggetto aggiornata.")).not.toBeInTheDocument();
    expect(screen.getByText("Modalità modifica attiva")).toBeVisible();
    expect(screen.getByLabelText("Email")).toHaveValue("bozza@example.invalid");
    expect(screen.getByRole("button", { name: "Salva scheda" })).toBeEnabled();
    change("Email", "retry@example.invalid");
    save();
    expect(screen.getByRole("button", { name: "Salvataggio..." })).toBeDisabled();
    expect(screen.queryByText(message)).not.toBeInTheDocument();
    expect(api.updateUtenzeSubject).toHaveBeenCalledTimes(2);
    expect(api.updateUtenzeSubject).toHaveBeenNthCalledWith(1, token, "subject-r101", {
      source_name_raw: "Rossi Mario", requires_review: false, status: "active",
      person: { ...emptyPersonPayload, email: "bozza@example.invalid" },
    });
    expect(api.updateUtenzeSubject).toHaveBeenNthCalledWith(2, token, "subject-r101", {
      source_name_raw: "Rossi Mario", requires_review: false, status: "active",
      person: { ...emptyPersonPayload, email: "retry@example.invalid" },
    });
    await act(async () => retry.resolve(subjectFixture({ person: personFixture({ email: "confermato@example.invalid" }) })));
    await expectSuccess();
    expect(screen.getByLabelText("Email")).toHaveValue("confermato@example.invalid");
  });

  test("canceling confirmation and terminating edits do not save or silently discard the public draft", async () => {
    await ready();
    fireEvent.click(screen.getByRole("button", { name: "Modifica" }));
    fireEvent.click(screen.getByRole("button", { name: "Annulla" }));
    expect(screen.queryByText("Abilita modalità modifica")).not.toBeInTheDocument();
    expect(screen.getByLabelText("Nome", { exact: true })).toHaveAttribute("readonly");
    enableEditing();
    change("Nome", "Bozza conservata");
    fireEvent.click(screen.getByRole("button", { name: "Termina modifica" }));
    expect(screen.getByLabelText("Nome", { exact: true })).toHaveValue("Bozza conservata");
    expect(screen.getByLabelText("Nome", { exact: true })).toHaveAttribute("readonly");
    expect(screen.getByRole("button", { name: "Salva scheda" })).toBeDisabled();
    expect(api.updateUtenzeSubject).not.toHaveBeenCalled();
    enableEditing();
    expect(screen.getByLabelText("Nome", { exact: true })).toHaveValue("Bozza conservata");
    expect(screen.getByLabelText("Nome", { exact: true })).not.toHaveAttribute("readonly");
    expect(api.updateUtenzeSubject).not.toHaveBeenCalled();
  });

  test("valid unknown subject saves common fields without inventing a person or company", async () => {
    const unknown = subjectFixture({
      subject_type: "unknown", person: null, company: null, source_name_raw: "Soggetto da identificare",
    });
    api.updateUtenzeSubject.mockResolvedValue({ ...unknown, source_name_raw: "Risposta server unknown", requires_review: true });
    await ready(unknown);
    expect(screen.getByLabelText("Ragione sociale")).toHaveValue("");
    expect(screen.getByLabelText("Forma giuridica")).toHaveValue("");
    expect(screen.getByLabelText("Partita IVA")).toHaveValue("");
    expect(screen.queryByLabelText("Soggetto deceduto")).not.toBeInTheDocument();
    expect(api.getUtenzeAnprStatus).not.toHaveBeenCalled();
    enableEditing();
    change("Source name raw", "Origine da verificare");
    change("Stato", "inactive");
    fireEvent.click(screen.getByLabelText("Richiede revisione"));
    save();
    expect(api.updateUtenzeSubject).toHaveBeenCalledExactlyOnceWith(token, "subject-r101", {
      source_name_raw: "Origine da verificare", status: "inactive", requires_review: true,
    });
    await expectSuccess();
    expect(screen.getByLabelText("Source name raw")).toHaveValue("Risposta server unknown");
    expect(screen.getByLabelText("Richiede revisione")).toBeChecked();
  });
});
