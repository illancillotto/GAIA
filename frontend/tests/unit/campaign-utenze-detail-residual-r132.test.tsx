import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import UtenzeSubjectDetailPage from "@/app/utenze/[id]/page";
import type {
  AnagraficaCatastoDocument,
  AnagraficaCompany,
  AnagraficaDocument,
  AnagraficaNasFolderCandidate,
  AnagraficaPaymentNotice,
  AnagraficaPerson,
  AnagraficaSubjectDetail,
  CurrentUser,
} from "@/types/api";

const api = vi.hoisted(() => ({
  router: { push: vi.fn(), replace: vi.fn() },
  getStoredAccessToken: vi.fn(), clearStoredAccessToken: vi.fn(),
  getCurrentUser: vi.fn<typeof import("@/lib/api").getCurrentUser>(),
  getMyPermissions: vi.fn<typeof import("@/lib/api").getMyPermissions>(),
  getUtenzeSubject: vi.fn<typeof import("@/lib/api").getUtenzeSubject>(),
  getUtenzeSubjectPaymentNotices: vi.fn<typeof import("@/lib/api").getUtenzeSubjectPaymentNotices>(),
  getUtenzeSubjectNasImportStatus: vi.fn<typeof import("@/lib/api").getUtenzeSubjectNasImportStatus>(),
  getUtenzeSubjectNasCandidates: vi.fn<typeof import("@/lib/api").getUtenzeSubjectNasCandidates>(),
  getUtenzeAnprStatus: vi.fn<typeof import("@/lib/api").getUtenzeAnprStatus>(),
  updateUtenzeSubject: vi.fn<typeof import("@/lib/api").updateUtenzeSubject>(),
  classifyUtenzeDocumentContent: vi.fn<typeof import("@/lib/api").classifyUtenzeDocumentContent>(),
  createElaborazioneRichiesta: vi.fn<typeof import("@/lib/api").createElaborazioneRichiesta>(),
  downloadCatastoDocumentBlob: vi.fn<typeof import("@/lib/api").downloadCatastoDocumentBlob>(),
  downloadUtenzeDocumentBlob: vi.fn<typeof import("@/lib/api").downloadUtenzeDocumentBlob>(),
  sendPresenceHeartbeat: vi.fn<typeof import("@/lib/api").sendPresenceHeartbeat>(),
}));

vi.mock("next/navigation", () => ({
  useParams: () => ({ id: "subject-r132" }), useRouter: () => api.router,
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
  getUtenzeSubjectNasCandidates: api.getUtenzeSubjectNasCandidates,
  getUtenzeAnprStatus: api.getUtenzeAnprStatus,
  updateUtenzeSubject: api.updateUtenzeSubject,
  classifyUtenzeDocumentContent: api.classifyUtenzeDocumentContent,
  createElaborazioneRichiesta: api.createElaborazioneRichiesta,
  downloadCatastoDocumentBlob: api.downloadCatastoDocumentBlob,
  downloadUtenzeDocumentBlob: api.downloadUtenzeDocumentBlob,
  sendPresenceHeartbeat: api.sendPresenceHeartbeat,
}));

const token = "r132-residual-token";
const timestamp = "2026-10-16T08:00:00Z";
const dayMs = 24 * 60 * 60 * 1000;

function userFixture(): CurrentUser {
  return {
    id: 132, username: "r132", email: "r132@example.invalid", role: "viewer", is_active: true,
    module_accessi: false, module_rete: false, module_inventario: false, module_catasto: false,
    module_utenze: true, module_operazioni: false, module_riordino: false,
    module_ruolo: false, module_presenze: false, enabled_modules: ["utenze"],
  };
}
function companyFixture(): AnagraficaCompany {
  return {
    subject_id: "subject-r132", ragione_sociale: "Azienda R132", partita_iva: "12345678901",
    codice_fiscale: null, forma_giuridica: null, sede_legale: null, comune_sede: null,
    cap: null, email_pec: null, telefono: null, note: null, created_at: timestamp, updated_at: timestamp,
  };
}
function personFixture(overrides: Partial<AnagraficaPerson> = {}): AnagraficaPerson {
  return {
    subject_id: "subject-r132", cognome: "Rossi", nome: "Mario", codice_fiscale: "RSSMRA80A01H501U",
    anpr_id: null, stato_anpr: null, data_decesso: null, luogo_decesso_comune: null,
    last_anpr_check_at: null, last_c030_check_at: null, data_nascita: null,
    comune_nascita: null, indirizzo: null, comune_residenza: null, cap: null,
    email: null, telefono: null, note: null, created_at: timestamp, updated_at: timestamp,
    ...overrides,
  };
}
function subjectFixture(overrides: Partial<AnagraficaSubjectDetail> = {}): AnagraficaSubjectDetail {
  return {
    id: "subject-r132", subject_type: "company", status: "active", source_system: "campaign-r132",
    source_external_id: null, source_name_raw: "Azienda R132", nas_folder_path: null,
    nas_folder_letter: null, requires_review: false, imported_at: null,
    created_at: timestamp, updated_at: timestamp, person: null, company: companyFixture(),
    documents: [], catasto_documents: [], audit_log: [], ...overrides,
  };
}
function documentFixture(overrides: Partial<AnagraficaDocument> = {}): AnagraficaDocument {
  return {
    id: "document-r132", filename: "residual-r132.pdf", relative_path: "residual-r132.pdf",
    nas_path: "/archive/R/residual-r132.pdf", extension: ".pdf", is_pdf: true,
    doc_type: "altro", classification_source: "manual", smart_category: "other",
    smart_category_label: "Altro da classificare", smart_priority: 10, smart_confidence: 0.2, smart_reason: null,
    content_classification_status: "not_started", content_category: null,
    content_category_label: null, content_confidence: null, content_reason: null,
    content_excerpt: null, content_classification_source: null, content_classified_at: null,
    content_classification_error: null, warnings: [], ...overrides,
  };
}
function catastoFixture(overrides: Partial<AnagraficaCatastoDocument> = {}): AnagraficaCatastoDocument {
  return {
    id: "catasto-r132", request_id: null, comune: "ORISTANO", foglio: "12", particella: "345",
    subalterno: null, catasto: "Fabbricati", tipo_visura: "Sintetica", filename: "catasto-r132.pdf",
    codice_fiscale: "RSSMRA80A01H501U", created_at: new Date(Date.now() - 30 * dayMs).toISOString(), ...overrides,
  };
}
function noticeFixture(id: string, overrides: Partial<AnagraficaPaymentNotice> = {}): AnagraficaPaymentNotice {
  return {
    id, subject_id: "subject-r132", source_system: "incass", source_notice_id: `notice-${id}`,
    source_internal_id: null, codice_fiscale: null, partita_iva: "12345678901", display_name: "Azienda R132",
    anno: "2026", stato_code: null, stato_label: null, data_scadenza: null, data_pagamento: null,
    tipo_anagrafica: null, ultimo_invio: null, lista_id: null, lista_descrizione: null, indirizzo: null,
    cap: null, citta: null, provincia: null, importo_carico: "100,00", importo_sgravio: null,
    importo_riscosso: null, importo_residuo: "100,00", importo_riporto: null, importo_rateizzato: null,
    importo_annullato: null, payment_status: "unpaid", detail_url: null, detail_info_text: null,
    pdf_links: [], synced_at: null, created_at: null, updated_at: null, ...overrides,
  };
}
function candidateFixture(overrides: Partial<AnagraficaNasFolderCandidate> = {}): AnagraficaNasFolderCandidate {
  return {
    folder_name: "Cartella R132", letter: "R", nas_folder_path: "/archive/R/r132", score: 80,
    subject_type: "company", confidence: 0.75, requires_review: false, codice_fiscale: null,
    partita_iva: null, ragione_sociale: "Azienda R132", cognome: null, nome: null, ...overrides,
  };
}
function deferred<Result>() {
  let resolve!: (value: Result) => void;
  const promise = new Promise<Result>((yes) => { resolve = yes; });
  return { promise, resolve };
}
async function ready(subject = subjectFixture()) {
  api.getUtenzeSubject.mockResolvedValue(subject);
  render(<UtenzeSubjectDetailPage />);
  await screen.findByText("R132 NAS pronto");
  await act(async () => {});
}
function enableEditing() {
  fireEvent.click(screen.getByRole("button", { name: "Modifica" }));
  fireEvent.click(screen.getByRole("button", { name: "Abilita modifica" }));
  expect(screen.getByText("Modalità modifica attiva")).toBeVisible();
}
function article(title: string) {
  const node = screen.getByText(title, { exact: true }).closest("article");
  if (!(node instanceof HTMLElement)) throw new Error(`Missing real article ${title}`);
  return within(node);
}
function paymentCard() {
  const card = screen.getByText("Stato pagamenti").parentElement;
  if (!(card instanceof HTMLElement)) throw new Error("Missing real payment summary card");
  return card;
}

beforeEach(() => {
  vi.resetAllMocks();
  window.history.replaceState(null, "", "/utenze/subject-r132?embedded=1");
  api.getStoredAccessToken.mockReturnValue(token);
  api.getCurrentUser.mockResolvedValue(userFixture());
  api.getMyPermissions.mockResolvedValue({ sections: [], granted_keys: [] });
  api.getUtenzeSubjectPaymentNotices.mockResolvedValue([]);
  api.getUtenzeSubjectNasImportStatus.mockResolvedValue({
    can_import_from_nas: false, missing_in_nas: true, matched_folder_path: null,
    matched_folder_name: null, total_files_in_nas: 0, pending_files_in_nas: 0, message: "R132 NAS pronto",
  });
  api.sendPresenceHeartbeat.mockResolvedValue({ ok: true, last_seen_at: timestamp });
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

describe("R132 residual public paths of the subject detail page", () => {
  test.each([
    {
      name: "all notices paid",
      notices: [noticeFixture("a", { payment_status: "paid", importo_residuo: "0,00" })],
      label: "Pagatore regolare", className: "border-emerald-100", summary: /^1 avvisi · residuo 0,00\s€$/,
    },
    {
      name: "paid and unpaid notices with open debt",
      notices: [
        noticeFixture("a", { payment_status: "paid", importo_residuo: "0,00" }),
        noticeFixture("b", { payment_status: "unpaid", importo_residuo: "12.500,50" }),
      ],
      label: "Pagamenti parziali", className: "border-amber-100", summary: /^2 avvisi · residuo 12\.500,50\s€$/,
    },
  ])("payment summary for $name uses its own status style and formatted residual", async ({ notices, label, className, summary }) => {
    api.getUtenzeSubjectPaymentNotices.mockResolvedValue(notices);
    await ready();
    const card = paymentCard();
    expect(within(card).getByText(label)).toBeVisible();
    expect(card).toHaveClass(className);
    expect(within(card).getByText(summary)).toBeVisible();
    expect(api.getUtenzeSubjectPaymentNotices).toHaveBeenCalledExactlyOnceWith(token, "subject-r132");
  });

  test("a non-Error payment notices rejection is reported as unavailable notices", async () => {
    api.getUtenzeSubjectPaymentNotices.mockRejectedValue("inCASS R132 non raggiungibile");
    await ready();
    expect(within(paymentCard()).getByText("Avvisi non disponibili")).toBeVisible();
  });

  test("manual upload modal lists an associated NAS-only document without persisted id", async () => {
    await ready(subjectFixture({
      documents: [documentFixture({ id: null, filename: "solo-nas-r132.pdf", nas_path: "/archive/R/solo-nas-r132.pdf" })],
    }));
    enableEditing();
    fireEvent.click(screen.getByRole("button", { name: "Nessun dato rilevato nel NAS, importa manualmente" }));
    const list = screen.getByText("Documenti gia associati").parentElement;
    if (!(list instanceof HTMLElement)) throw new Error("Missing real associated documents list");
    expect(within(list).getByText("solo-nas-r132.pdf")).toBeVisible();
    expect(within(list).getByText("/archive/R/solo-nas-r132.pdf")).toBeVisible();
    expect(within(list).getByText("altro")).toBeVisible();
  });

  test("an unlabeled document shows its raw content classification status", async () => {
    await ready(subjectFixture({ documents: [documentFixture({ content_classification_status: "unsupported" })] }));
    expect(article("Documenti associati").getByText("contenuto: unsupported")).toBeVisible();
    expect(article("Documenti associati").queryByText("contenuto: non analizzato")).not.toBeInTheDocument();
  });

  test("Catasto correlation shows subalterno and missing CF, and ignores non-activation keys", async () => {
    await ready(subjectFixture({
      catasto_documents: [catastoFixture({ subalterno: "7", codice_fiscale: null })],
    }));
    const catasto = article("Correlazioni Catasto");
    expect(catasto.getByText("ORISTANO · Fg. 12 · Part. 345 · Sub. 7")).toBeVisible();
    expect(catasto.getByText("Fabbricati · Sintetica · CF non disponibile")).toBeVisible();
    const row = catasto.getByText("catasto-r132.pdf").closest<HTMLElement>('[role="button"]');
    if (!row) throw new Error("Missing real Catasto row");
    fireEvent.keyDown(row, { key: "a" });
    fireEvent.keyDown(row, { key: "Tab" });
    expect(api.downloadCatastoDocumentBlob).not.toHaveBeenCalled();
    expect(screen.queryByText("Anteprima documento")).not.toBeInTheDocument();
  });

  test("NAS candidates fall back to PIVA and then to the missing identifier label", async () => {
    api.getUtenzeSubjectNasCandidates.mockResolvedValue([
      candidateFixture({ partita_iva: "98765432109" }),
      candidateFixture({ folder_name: "Cartella anonima", nas_folder_path: "/archive/R/anonima", confidence: 0.4, requires_review: true }),
    ]);
    await ready();
    enableEditing();
    fireEvent.click(screen.getByRole("button", { name: "Trova cartelle candidate" }));
    await waitFor(() => expect(screen.getByRole("button", { name: "Trova cartelle candidate" })).toBeEnabled());
    const nas = article("Override cartella NAS");
    expect(nas.getByText("confidenza 75% · 98765432109 · review no")).toBeVisible();
    expect(nas.getByText("confidenza 40% · identificativo non disponibile · review si")).toBeVisible();
    expect(api.getUtenzeSubjectNasCandidates).toHaveBeenCalledExactlyOnceWith(token, "subject-r132");
  });

  test("confirming a recent-Visura request after a pending save clears the CF reports the missing identifier", async () => {
    const recent = catastoFixture({ id: "recent-r132", filename: "recent-r132.pdf", created_at: new Date(Date.now() - dayMs).toISOString() });
    const person = personFixture();
    const subject = subjectFixture({ subject_type: "person", source_name_raw: "Rossi Mario", person, company: null, catasto_documents: [recent] });
    api.getUtenzeAnprStatus.mockResolvedValue({
      subject_id: subject.id, anpr_id: null, stato_anpr: null, data_decesso: null,
      luogo_decesso_comune: null, last_anpr_check_at: null, last_c030_check_at: null,
    });
    const save = deferred<AnagraficaSubjectDetail>();
    api.updateUtenzeSubject.mockReturnValue(save.promise);
    await ready(subject);

    enableEditing();
    fireEvent.change(screen.getByLabelText("Codice fiscale"), { target: { value: "" } });
    fireEvent.click(screen.getByRole("button", { name: "Salva scheda" }));
    expect(screen.getByRole("button", { name: "Salvataggio..." })).toBeDisabled();
    expect(api.updateUtenzeSubject).toHaveBeenCalledTimes(1);
    expect(api.updateUtenzeSubject.mock.calls[0]?.[2].person?.codice_fiscale).toBe("");

    const requestButton = screen.getByRole("button", { name: "Richiedi visura" });
    expect(requestButton).toBeEnabled();
    fireEvent.click(requestButton);
    const dialog = screen.getByRole("dialog", { name: "Conferma nuova visura" });
    expect(dialog).toBeVisible();

    await act(async () => save.resolve({ ...subject, person: { ...person, codice_fiscale: "" } }));
    expect(await screen.findByText("Scheda soggetto aggiornata.")).toBeVisible();
    expect(screen.getByText("Codice fiscale o partita IVA mancanti")).toBeVisible();
    expect(screen.getByRole("button", { name: "Richiedi visura" })).toBeDisabled();

    const confirm = within(screen.getByRole("dialog", { name: "Conferma nuova visura" })).getByRole("button", { name: "Conferma richiesta" });
    expect(confirm).toBeEnabled();
    fireEvent.click(confirm);
    expect(await screen.findByText("Identificativo soggetto assente: serve un codice fiscale o una partita IVA per inviare la visura.")).toBeVisible();
    expect(screen.queryByRole("dialog", { name: "Conferma nuova visura" })).not.toBeInTheDocument();
    expect(api.createElaborazioneRichiesta).not.toHaveBeenCalled();
    expect(api.router.push).not.toHaveBeenCalled();
  });
});

describe("R132 races around the remaining defensive guards", () => {
  test("an in-flight ANPR status arriving after a concurrent reload reclassified the subject as company leaves it untouched", async () => {
    const person = personFixture();
    const document = documentFixture({ id: "document-anpr-r132", filename: "anpr-r132.pdf" });
    const pfSubject = subjectFixture({ subject_type: "person", source_name_raw: "Rossi Mario", person, company: null, documents: [document] });
    const companySubject = subjectFixture({ documents: [document] });
    const anprStatus = deferred<Awaited<ReturnType<typeof import("@/lib/api").getUtenzeAnprStatus>>>();
    api.getUtenzeAnprStatus.mockReturnValue(anprStatus.promise);
    api.classifyUtenzeDocumentContent.mockResolvedValue(document);
    api.getUtenzeSubject.mockResolvedValueOnce(pfSubject).mockResolvedValueOnce(companySubject);
    render(<UtenzeSubjectDetailPage />);
    await screen.findByText("R132 NAS pronto");
    await act(async () => {});
    expect(screen.getByText("Rossi Mario")).toBeVisible();
    await waitFor(() => expect(api.getUtenzeAnprStatus).toHaveBeenCalledWith(token, "subject-r132"));

    fireEvent.click(screen.getByRole("button", { name: "Analizza contenuto" }));
    expect(await screen.findByText("Classificazione contenutistica documento aggiornata.")).toBeVisible();
    expect(api.getUtenzeSubject).toHaveBeenCalledTimes(2);
    expect(screen.getAllByText("Partita IVA: 12345678901")[0]).toBeVisible();
    expect(screen.queryByText("Rossi Mario")).not.toBeInTheDocument();

    await act(async () => anprStatus.resolve({
      subject_id: "subject-r132", anpr_id: "ANPR-LATE", stato_anpr: "deceased", data_decesso: "2026-10-01",
      luogo_decesso_comune: "ORISTANO", last_anpr_check_at: timestamp, last_c030_check_at: null,
    }));
    expect(screen.getAllByText("Partita IVA: 12345678901")[0]).toBeVisible();
    expect(screen.getByLabelText("Partita IVA")).toHaveValue("12345678901");
    expect(screen.queryByText("Rossi Mario")).not.toBeInTheDocument();
    expect(api.getUtenzeSubject).toHaveBeenCalledTimes(2);
  });

  test("an empty reload response unmounts every subject action instead of running them without a subject", async () => {
    const document = documentFixture({ id: "document-empty-r132", filename: "empty-r132.pdf" });
    api.classifyUtenzeDocumentContent.mockResolvedValue(document);
    api.getUtenzeSubject
      .mockResolvedValueOnce(subjectFixture({ documents: [document] }))
      .mockResolvedValueOnce(undefined as unknown as AnagraficaSubjectDetail);
    render(<UtenzeSubjectDetailPage />);
    await screen.findByText("R132 NAS pronto");
    await act(async () => {});
    enableEditing();
    expect(screen.getByRole("button", { name: "Salva scheda" })).toBeEnabled();

    fireEvent.click(screen.getByRole("button", { name: "Analizza contenuto" }));
    expect(await screen.findByText("Caricamento scheda soggetto.")).toBeVisible();
    for (const name of ["Salva scheda", "Richiedi visura", "Rimuovi", "Elimina", "Analizza contenuto"]) {
      expect(screen.queryByRole("button", { name })).not.toBeInTheDocument();
    }
    expect(api.updateUtenzeSubject).not.toHaveBeenCalled();
    expect(api.createElaborazioneRichiesta).not.toHaveBeenCalled();
  });
});
