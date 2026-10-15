import { act, cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import UtenzeSubjectDetailPage from "@/app/utenze/[id]/page";
import type { AnagraficaSubjectDetail, CurrentUser } from "@/types/api";

const api = vi.hoisted(() => ({
  router: { push: vi.fn(), replace: vi.fn() },
  getStoredAccessToken: vi.fn(), clearStoredAccessToken: vi.fn(),
  getCurrentUser: vi.fn<typeof import("@/lib/api").getCurrentUser>(),
  getMyPermissions: vi.fn<typeof import("@/lib/api").getMyPermissions>(),
  getUtenzeSubject: vi.fn<typeof import("@/lib/api").getUtenzeSubject>(),
  getUtenzeSubjectPaymentNotices: vi.fn<typeof import("@/lib/api").getUtenzeSubjectPaymentNotices>(),
  getUtenzeSubjectNasImportStatus: vi.fn<typeof import("@/lib/api").getUtenzeSubjectNasImportStatus>(),
  getUtenzeSubjectNasCandidates: vi.fn<typeof import("@/lib/api").getUtenzeSubjectNasCandidates>(),
  updateUtenzeSubject: vi.fn<typeof import("@/lib/api").updateUtenzeSubject>(),
  updateUtenzeDocument: vi.fn<typeof import("@/lib/api").updateUtenzeDocument>(),
  classifyUtenzeDocumentContent: vi.fn<typeof import("@/lib/api").classifyUtenzeDocumentContent>(),
  deleteUtenzeDocument: vi.fn<typeof import("@/lib/api").deleteUtenzeDocument>(),
  uploadUtenzeSubjectDocument: vi.fn<typeof import("@/lib/api").uploadUtenzeSubjectDocument>(),
  importUtenzeSubjectFromNas: vi.fn<typeof import("@/lib/api").importUtenzeSubjectFromNas>(),
  createElaborazioneRichiesta: vi.fn<typeof import("@/lib/api").createElaborazioneRichiesta>(),
  downloadUtenzeDocumentBlob: vi.fn<typeof import("@/lib/api").downloadUtenzeDocumentBlob>(),
  downloadCatastoDocumentBlob: vi.fn<typeof import("@/lib/api").downloadCatastoDocumentBlob>(),
  sendPresenceHeartbeat: vi.fn<typeof import("@/lib/api").sendPresenceHeartbeat>(),
}));

vi.mock("next/navigation", () => ({
  useParams: () => ({ id: "subject-r105" }), useRouter: () => api.router,
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
  updateUtenzeSubject: api.updateUtenzeSubject, updateUtenzeDocument: api.updateUtenzeDocument,
  classifyUtenzeDocumentContent: api.classifyUtenzeDocumentContent,
  deleteUtenzeDocument: api.deleteUtenzeDocument,
  uploadUtenzeSubjectDocument: api.uploadUtenzeSubjectDocument,
  importUtenzeSubjectFromNas: api.importUtenzeSubjectFromNas,
  createElaborazioneRichiesta: api.createElaborazioneRichiesta,
  downloadUtenzeDocumentBlob: api.downloadUtenzeDocumentBlob,
  downloadCatastoDocumentBlob: api.downloadCatastoDocumentBlob,
  sendPresenceHeartbeat: api.sendPresenceHeartbeat,
}));

const token = "r105-metadata-token";
const createdAt = "2025-07-19T06:10:00Z";
const importedAt = "2026-02-03T10:25:00Z";
const updatedAt = "2026-10-15T14:35:00Z";

type MetadataInput = Pick<AnagraficaSubjectDetail,
  "nas_folder_letter" | "nas_folder_path" | "source_external_id" | "imported_at" | "requires_review"
>;

function userFixture(): CurrentUser {
  return {
    id: 105, username: "r105", email: "r105@example.invalid", role: "viewer", is_active: true,
    module_accessi: false, module_rete: false, module_inventario: false, module_catasto: false,
    module_utenze: true, module_operazioni: false, module_riordino: false,
    module_ruolo: false, module_presenze: false, enabled_modules: ["utenze"],
  };
}

function subjectFixture(overrides: Partial<MetadataInput> = {}): AnagraficaSubjectDetail {
  return {
    id: "subject-r105", subject_type: "company", status: "active", source_system: "metadata-import-r105",
    source_external_id: "EXT-R105-509", source_name_raw: "Azienda R105",
    nas_folder_path: "/archive/R/Azienda-105", nas_folder_letter: "R",
    requires_review: false, imported_at: importedAt,
    created_at: createdAt, updated_at: updatedAt, person: null,
    company: {
      subject_id: "subject-r105", ragione_sociale: "Azienda R105", partita_iva: "12345678901",
      codice_fiscale: null, forma_giuridica: null, sede_legale: null, comune_sede: null,
      cap: null, email_pec: null, telefono: null, note: null, created_at: createdAt, updated_at: updatedAt,
    },
    documents: [], catasto_documents: [], audit_log: [], ...overrides,
  };
}

function metadataArticle(): HTMLElement {
  const article = screen.getByText("Metadati archivio", { exact: true }).closest("article");
  if (!(article instanceof HTMLElement)) throw new Error("Missing actual archive metadata article");
  return article;
}

function metadata() { return within(metadataArticle()); }

function audit() {
  const article = screen.getByText("Audit log", { exact: true }).closest("article");
  if (!(article instanceof HTMLElement)) throw new Error("Missing actual Audit log article");
  return within(article);
}

async function ready(subject: AnagraficaSubjectDetail) {
  api.getUtenzeSubject.mockResolvedValue(subject);
  render(<UtenzeSubjectDetailPage />);
  await screen.findByText("R105 NAS pronto");
  await act(async () => {});
  expect(metadata().getByText("Informazioni tecniche sul collegamento NAS e sullo stato archivistico del soggetto.")).toBeVisible();
}

function expectMetadataValues(expected: Record<string, string>) {
  expect(metadata().getAllByRole("term")).toHaveLength(9);
  expect(metadata().getAllByRole("definition")).toHaveLength(9);
  for (const [label, value] of Object.entries(expected)) {
    const group = metadata().getByText(label, { exact: true }).parentElement;
    if (!(group instanceof HTMLElement)) throw new Error(`Missing actual metadata group for ${label}`);
    const definition = within(group).getByRole("definition");
    expect(definition).toBeVisible();
    expect(definition.textContent).toBe(value);
  }
}

function presentMetadata(review: boolean): Record<string, string> {
  const formatter = new Intl.DateTimeFormat("it-IT", { dateStyle: "short", timeStyle: "short" });
  return {
    "Tipo soggetto": "company", "Lettera archivio": "R", "Percorso NAS": "/archive/R/Azienda-105",
    "Importato il": formatter.format(new Date(importedAt)), "Sorgente": "metadata-import-r105",
    "ID esterno sorgente": "EXT-R105-509", "Aggiornato il": formatter.format(new Date(updatedAt)),
    "Creato il": formatter.format(new Date(createdAt)), "Richiede revisione": review ? "Si" : "No",
  };
}

function expectOnlyInitialReads() {
  expect(api.getUtenzeSubject).toHaveBeenCalledExactlyOnceWith(token, "subject-r105");
  expect(api.getUtenzeSubjectPaymentNotices).toHaveBeenCalledExactlyOnceWith(token, "subject-r105");
  expect(api.getUtenzeSubjectNasImportStatus).toHaveBeenCalledExactlyOnceWith(token, "subject-r105");
  for (const request of [
    api.getUtenzeSubjectNasCandidates, api.updateUtenzeSubject, api.updateUtenzeDocument,
    api.classifyUtenzeDocumentContent, api.deleteUtenzeDocument, api.uploadUtenzeSubjectDocument,
    api.importUtenzeSubjectFromNas, api.createElaborazioneRichiesta,
    api.downloadUtenzeDocumentBlob, api.downloadCatastoDocumentBlob,
  ]) {
    expect(request).not.toHaveBeenCalled();
  }
  expect(api.router.push).not.toHaveBeenCalled();
  expect(api.router.replace).not.toHaveBeenCalled();
}

beforeEach(() => {
  vi.resetAllMocks();
  window.history.replaceState(null, "", "/utenze/subject-r105?embedded=1");
  api.getStoredAccessToken.mockReturnValue(token);
  api.getCurrentUser.mockResolvedValue(userFixture());
  api.getMyPermissions.mockResolvedValue({ sections: [], granted_keys: [] });
  api.getUtenzeSubjectPaymentNotices.mockResolvedValue([]);
  api.getUtenzeSubjectNasImportStatus.mockResolvedValue({
    can_import_from_nas: false, missing_in_nas: true, matched_folder_path: null,
    matched_folder_name: null, total_files_in_nas: 0, pending_files_in_nas: 0, message: "R105 NAS pronto",
  });
  api.sendPresenceHeartbeat.mockResolvedValue({ ok: true, last_seen_at: updatedAt });
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("R105 real archive metadata disclosure", () => {
  test.each([
    { label: "null path", path: null, summary: "Nessun percorso NAS collegato." },
    { label: "empty path", path: "", summary: "Nessun percorso NAS collegato." },
    { label: "present path", path: "/archive/R/Azienda-105", summary: "Percorso NAS collegato disponibile." },
  ])("$label starts collapsed with only the correct metadata summary", async ({ path, summary }) => {
    await ready(subjectFixture({ nas_folder_path: path }));
    expect(metadata().getByText(`Metadati ridotti di default. ${summary}`)).toBeVisible();
    expect(metadata().getByRole("button", { name: "Espandi" })).toBeEnabled();
    expect(metadata().queryByRole("button", { name: "Riduci" })).not.toBeInTheDocument();
    expect(metadata().queryByRole("term")).not.toBeInTheDocument();
    expect(metadata().queryByRole("definition")).not.toBeInTheDocument();
    expectOnlyInitialReads();
  });

  test.each([false, true])("expanded present values keep all nine associations with requires_review %s", async (review) => {
    await ready(subjectFixture({ requires_review: review }));
    fireEvent.click(metadata().getByRole("button", { name: "Espandi" }));
    expect(metadata().getByRole("button", { name: "Riduci" })).toBeEnabled();
    expect(metadata().queryByText(/Metadati ridotti di default/)).not.toBeInTheDocument();
    expectMetadataValues(presentMetadata(review));
    expectOnlyInitialReads();
  });

  test.each([null, ""])("nullable text fields %j and absent imported date use em dashes in their own groups", async (absent) => {
    await ready(subjectFixture({
      nas_folder_letter: absent, nas_folder_path: absent, source_external_id: absent, imported_at: null,
    }));
    fireEvent.click(metadata().getByRole("button", { name: "Espandi" }));
    expectMetadataValues({
      ...presentMetadata(false), "Lettera archivio": "—", "Percorso NAS": "—",
      "ID esterno sorgente": "—", "Importato il": "—",
    });
    expectOnlyInitialReads();
  });

  test("collapse and reexpand preserve metadata and subject while Audit log stays independent", async () => {
    const subject = subjectFixture({ requires_review: true });
    const originalSubject = JSON.stringify(subject);
    const originalCompany = subject.company;
    const originalDocuments = subject.documents;
    await ready(subject);
    expect(audit().getByText("Audit log ridotto di default. Nessun evento registrato.")).toBeVisible();
    fireEvent.click(metadata().getByRole("button", { name: "Espandi" }));
    expectMetadataValues(presentMetadata(true));
    expect(audit().getByRole("button", { name: "Espandi" })).toBeEnabled();
    expect(audit().getByText("Audit log ridotto di default. Nessun evento registrato.")).toBeVisible();
    fireEvent.click(audit().getByRole("button", { name: "Espandi" }));
    expect(audit().getByText("Nessun evento registrato.", { exact: true })).toBeVisible();
    expectMetadataValues(presentMetadata(true));
    fireEvent.click(metadata().getByRole("button", { name: "Riduci" }));
    expect(metadata().getByText("Metadati ridotti di default. Percorso NAS collegato disponibile.")).toBeVisible();
    expect(metadata().queryByRole("definition")).not.toBeInTheDocument();
    expect(audit().getByRole("button", { name: "Riduci" })).toBeEnabled();
    expect(audit().getByText("Nessun evento registrato.", { exact: true })).toBeVisible();
    expectOnlyInitialReads();
    fireEvent.click(metadata().getByRole("button", { name: "Espandi" }));
    expectMetadataValues(presentMetadata(true));
    fireEvent.click(audit().getByRole("button", { name: "Riduci" }));
    expect(audit().getByText("Audit log ridotto di default. Nessun evento registrato.")).toBeVisible();
    expectMetadataValues(presentMetadata(true));
    expect(JSON.stringify(subject)).toBe(originalSubject);
    expect(subject.company).toBe(originalCompany);
    expect(subject.documents).toBe(originalDocuments);
    expectOnlyInitialReads();
  });
});
